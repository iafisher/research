package internal

import (
	"bufio"
	"bytes"
	"crypto/tls"
	"errors"
	"fmt"
	"io"
	"net"
	"os"
	"strconv"
	"strings"
)

type GenericResponse interface {
	GetContent() string
}

type HttpResponse struct {
	Version           string
	Status            int
	StatusExplanation string
	Headers           map[string]string
	Content           string
}

func (response *HttpResponse) GetContent() string {
	return response.Content
}

type FileResponse struct {
	Content string
}

func (response *FileResponse) GetContent() string {
	return response.Content
}

type DataResponse struct {
	Content  string
	MimeType MimeType
}

func (response *DataResponse) GetContent() string {
	return response.Content
}

type UrlFetcher struct {
	connCache map[string]net.Conn
}

func NewUrlFetcher() UrlFetcher {
	return UrlFetcher{connCache: make(map[string]net.Conn)}
}

func (fetcher *UrlFetcher) Fetch(url Url) (GenericResponse, error) {
	if url.Scheme == "http" || url.Scheme == "https" {
		return fetcher.fetchHttpGeneric(url)
	} else if url.Scheme == "file" {
		return fetcher.fetchFile(url)
	} else if url.Scheme == "data" {
		return fetcher.fetchData(url), nil
	} else {
		// should be impossible
		panic("unrecognized scheme in url.Request()")
	}
}

func (fetcher *UrlFetcher) Cleanup() {
	for k, conn := range fetcher.connCache {
		conn.Close()
		delete(fetcher.connCache, k)
	}
}

func (fetcher *UrlFetcher) openConnection(address string, isTls bool) (net.Conn, error) {
	existingConn, ok := fetcher.connCache[address]
	if ok {
		PrintVerbose(fmt.Sprintf("using cached connection to %s", address))
		return existingConn, nil
	}

	var conn net.Conn
	var err error
	if isTls {
		PrintVerbose(fmt.Sprintf("opening TLS connection to %s", address))
		conn, err = tls.Dial("tcp", address, &tls.Config{})
	} else {
		PrintVerbose(fmt.Sprintf("opening TCP connection to %s", address))
		conn, err = net.Dial("tcp", address)
	}

	if err != nil {
		return nil, err
	}

	fetcher.connCache[address] = conn
	return conn, nil
}

func (fetcher *UrlFetcher) uncache(address string) {
	delete(fetcher.connCache, address)
}

func (fetcher *UrlFetcher) fetchHttpGeneric(url Url) (*HttpResponse, error) {
	// TODO: make this configurable
	redirectsRemaining := 5

	for redirectsRemaining > 0 {
		address := fmt.Sprintf("%s:%d", url.Host, url.PortOrDefault())
		isTls := url.Scheme == "https"
		conn, err := fetcher.openConnection(address, isTls)
		if err != nil {
			return nil, err
		}

		err = sendHttpRequest(url, conn)
		if err != nil {
			return nil, err
		}

		r, err := receiveHttpResponse(conn)
		if err != nil {
			return nil, err
		}

		if r.Version == "HTTP/1.0" {
			// in particular, this is necessary because the Python test server only supports HTTP/1.0
			PrintVerbose(fmt.Sprintf("connection using HTTP/1.0; removing from connection cache: %s", address))
			fetcher.uncache(address)
		}

		if r.Status >= 300 && r.Status < 400 {
			location, ok := r.Headers["location"]
			if !ok {
				return nil, fmt.Errorf("got HTTP %d response but no 'Location' header present: %s", r.Status, url.Original)
			}

			PrintVerbose(fmt.Sprintf("following redirect from %s to %s", url.Original, location))
			if strings.HasPrefix(location, "/") {
				url.Original = fmt.Sprintf("%s%s", address, location)
				url.Path = location
			} else {
				url, err = ParseUrl(location)
				if err != nil {
					return nil, fmt.Errorf("could not parse redirect URL (original=%q, redirect=%q): %s", url.Original, location, err.Error())
				}
			}

			redirectsRemaining--
		} else {
			return r, nil
		}
	}

	return nil, fmt.Errorf("max redirects exceeded for %s", url.Original)
}

func sendHttpRequest(url Url, conn net.Conn) error {
	var requestHeaders = map[string]string{
		"Host":       url.Host,
		"Connection": "keep-alive",
		"User-Agent": "Mozilla/5.0 (desktop; rv:0.1) TinCan/0.1",
	}

	requestLine := fmt.Sprintf("GET %s HTTP/1.1\r\n", url.Path)
	_, err := fmt.Fprint(conn, requestLine)
	if err != nil {
		return err
	}

	for key, value := range requestHeaders {
		fmt.Fprintf(conn, "%s: %s\r\n", key, value)
	}
	fmt.Fprintf(conn, "\r\n")
	return nil
}

func receiveHttpResponse(conn net.Conn) (*HttpResponse, error) {
	reader := bufio.NewReader(conn)

	statusLine, err := readHttpLine(reader)
	if err != nil {
		return nil, err
	}
	statusParts := strings.SplitN(statusLine, " ", 3)
	version := statusParts[0]
	statusStr := statusParts[1]
	status, err := strconv.Atoi(statusStr)
	if err != nil {
		return nil, fmt.Errorf("could not parse HTTP status as integer: %s", err.Error())
	}
	statusExplanation := statusParts[2]

	responseHeaders := make(map[string]string)
	for {
		line, err := readHttpLine(reader)
		if err != nil {
			return nil, err
		}

		if line == "" {
			break
		}

		parts := strings.SplitN(line, ":", 2)
		// TODO: handle error more gracefully
		key := strings.ToLower(parts[0])
		value := strings.TrimSpace(parts[1])
		responseHeaders[key] = value
	}

	// TODO: handle this case
	_, ok := responseHeaders["transfer-encoding"]
	if ok {
		return nil, errors.New("transfer-encoding header not supported")
	}

	// TODO: handle this case
	_, ok = responseHeaders["content-encoding"]
	if ok {
		return nil, errors.New("content-encoding header not supported")
	}

	contentLengthStr, ok := responseHeaders["content-length"]
	if !ok {
		return nil, errors.New("content-length header is missing")
	}

	contentLength, err := strconv.Atoi(contentLengthStr)
	if err != nil {
		return nil, fmt.Errorf("could not parse Content-Length as integer: %s", err.Error())
	}

	content := make([]byte, contentLength)
	_, err = io.ReadFull(reader, content)
	if err != nil {
		return nil, err
	}

	return &HttpResponse{
		Version:           version,
		Status:            status,
		StatusExplanation: statusExplanation,
		Headers:           responseHeaders,
		// TODO: read charset from Content-Type header
		Content: string(content),
	}, nil
}

func (fetcher *UrlFetcher) fetchFile(url Url) (*FileResponse, error) {
	PrintVerbose(fmt.Sprintf("reading local file: %s", url.Path))
	data, err := os.ReadFile(url.Path)
	if err != nil {
		return nil, err
	}
	return &FileResponse{Content: string(data)}, nil
}

func (fetcher *UrlFetcher) fetchData(url Url) *DataResponse {
	return &DataResponse{Content: url.Path, MimeType: url.MimeType}
}

func readHttpLine(reader *bufio.Reader) (string, error) {
	var buffer bytes.Buffer
	for {
		// TODO: safe to convert header from bytes to string?
		bs, err := reader.ReadString('\n')
		if err != nil {
			return "", err
		}

		if strings.HasSuffix(bs, "\r\n") {
			buffer.WriteString(strings.TrimSuffix(bs, "\r\n"))
			break
		} else {
			buffer.WriteString(bs)
		}
	}
	return buffer.String(), nil
}
