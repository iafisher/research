package main

import (
	"bufio"
	"bytes"
	"crypto/tls"
	"errors"
	"flag"
	"fmt"
	"net"
	"os"
	"regexp"
	"strconv"
	"strings"
)

type GenericResponse interface {
	GetTextContent() string
	GetContent() string
}

type HttpResponse struct {
	Version           string
	Status            string
	StatusExplanation string
	Headers           map[string]string
	Content           string
}

func (response *HttpResponse) GetTextContent() string {
	return htmlText(response.Content)
}

func (response *HttpResponse) GetContent() string {
	return response.Content
}

type FileResponse struct {
	Content string
}

func (response *FileResponse) GetTextContent() string {
	return response.Content
}

func (response *FileResponse) GetContent() string {
	return response.Content
}

type DataResponse struct {
	Content  string
	MimeType MimeType
}

func (response *DataResponse) GetTextContent() string {
	if response.MimeType.Type == "text" {
		return htmlText(response.Content)
	} else {
		// TODO: how to handle unknown MIME type?
		return response.Content
	}
}

func (response *DataResponse) GetContent() string {
	return response.Content
}

type Url struct {
	Scheme     string
	Host       string
	Port       int
	Path       string
	MimeType   MimeType // only for 'data:' URLs
	ViewSource bool
}

type MimeType struct {
	Type           string
	Subtype        string
	ParameterName  string
	ParameterValue string
}

func (url Url) Request() (GenericResponse, error) {
	if url.Scheme == "http" {
		return url.requestHttp()
	} else if url.Scheme == "https" {
		return url.requestHttps()
	} else if url.Scheme == "file" {
		return url.requestFile()
	} else if url.Scheme == "data" {
		return url.requestData(), nil
	} else {
		// should be impossible
		panic("unrecognized scheme in url.Request()")
	}
}

func (url Url) requestHttp() (*HttpResponse, error) {
	hostAndPort := fmt.Sprintf("%s:%d", url.Host, url.PortOrDefault())
	conn, err := net.Dial("tcp", hostAndPort)
	if err != nil {
		return nil, err
	}
	return url.requestHttpGeneric(conn)
}

func (url Url) requestHttps() (*HttpResponse, error) {
	hostAndPort := fmt.Sprintf("%s:%d", url.Host, url.PortOrDefault())
	conn, err := tls.Dial("tcp", hostAndPort, &tls.Config{})
	if err != nil {
		return nil, err
	}
	return url.requestHttpGeneric(conn)
}

func (url Url) requestHttpGeneric(conn net.Conn) (*HttpResponse, error) {
	var requestHeaders = map[string]string{
		"Host":       url.Host,
		"Connection": "close",
		"User-Agent": "Mozilla/5.0 (desktop; rv:0.1) RCWeb/0.1",
	}

	fmt.Fprintf(conn, "GET %s HTTP/1.1\r\n", url.Path)

	for key, value := range requestHeaders {
		fmt.Fprintf(conn, "%s: %s\r\n", key, value)
	}
	fmt.Fprintf(conn, "\r\n")

	reader := bufio.NewReader(conn)

	statusLine, err := readHttpLine(reader)
	if err != nil {
		return nil, err
	}
	statusParts := strings.SplitN(statusLine, " ", 3)
	version := statusParts[0]
	status := statusParts[1]
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

	// TODO: use Content-Length header if present
	content, err := readToEnd(reader)
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

func (url Url) requestFile() (*FileResponse, error) {
	data, err := os.ReadFile(url.Path)
	if err != nil {
		return nil, err
	}
	return &FileResponse{Content: string(data)}, nil
}

func (url Url) requestData() *DataResponse {
	return &DataResponse{Content: url.Path, MimeType: url.MimeType}
}

func (url Url) PortOrDefault() int {
	if url.Port == 0 {
		if url.Scheme == "https" {
			return 443
		} else {
			return 80
		}
	} else {
		return url.Port
	}
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

func readToEnd(reader *bufio.Reader) ([]byte, error) {
	bufferSize := 4096

	var buffer bytes.Buffer
	for {
		b := make([]byte, bufferSize)
		n, err := reader.Read(b)
		if err != nil {
			return nil, err
		}

		buffer.Write(b[:n])
		if n < bufferSize {
			break
		}
	}

	return buffer.Bytes(), nil
}

func checkUrlScheme(scheme string) bool {
	// if you had a new scheme here, you must update url.Request()
	return scheme == "http" || scheme == "https" || scheme == "file" || scheme == "data"
}

func parseUrl(text string) (Url, error) {
	if strings.HasPrefix(text, "data:") {
		return parseDataUrl(text)
	}

	parts := strings.SplitN(text, "://", 2)
	scheme := strings.ToLower(parts[0])
	rest := parts[1]

	scheme, viewSource := trimPrefix(scheme, "view-source:")
	if !checkUrlScheme(scheme) {
		return Url{}, fmt.Errorf("not a supported URL schema: %q", scheme)
	}

	var host string
	var path string
	if strings.Contains(rest, "/") {
		parts = strings.SplitN(rest, "/", 2)
		host = parts[0]
		path = "/" + parts[1]
	} else {
		host = rest
		path = "/"
	}

	port := 0
	var err error
	if strings.Contains(host, ":") {
		parts = strings.SplitN(host, ":", 2)
		host = parts[0]
		port, err = strconv.Atoi(parts[1])
		if err != nil {
			return Url{}, err
		}
	}

	return Url{Scheme: scheme, Host: strings.ToLower(host), Port: port, Path: path, ViewSource: viewSource}, nil
}

func parseDataUrl(text string) (Url, error) {
	rest := strings.TrimPrefix(text, "data:")

	parts := strings.SplitN(rest, ",", 2)
	if len(parts) != 2 {
		return Url{}, errors.New("missing comma in 'data:' URL")
	}

	var mimeType MimeType
	if parts[0] != "" {
		var err error
		mimeType, err = parseMimeType(parts[0])
		if err != nil {
			return Url{}, err
		}
	} else {
		// MDN: "If omitted, defaults to text/plain;charset=US-ASCII"
		// https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/Data_URLs
		mimeType = MimeType{Type: "text", Subtype: "plain", ParameterName: "charset", ParameterValue: "US-ASCII"}
	}

	// TODO: support full 'data:' URL specification
	// https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/Data_URLs
	return Url{Scheme: "data", Host: "", Port: 0, Path: parts[1], MimeType: mimeType}, nil
}

func parseMimeType(text string) (MimeType, error) {
	// TODO: should only compile this regex once
	chpat := "[A-Za-z0-9-]"
	pat := regexp.MustCompile(fmt.Sprintf("^(%[1]s+)/(%[1]s+)(;(%[1]s+)=(%[1]s+))?$", chpat))
	matches := pat.FindStringSubmatch(text)
	if matches == nil {
		return MimeType{}, fmt.Errorf("invalid MIME type: %q", text)
	}

	return MimeType{Type: matches[1], Subtype: matches[2], ParameterName: matches[4], ParameterValue: matches[5]}, nil
}

func htmlText(content string) string {
	var b strings.Builder

	inTag := false
	reader := CharReader{Content: content}
	for !reader.Done() {
		c := reader.Next()

		if !inTag {
			if c == "<" {
				inTag = true
			} else if c == "&" {
				code := readEntityRef(&reader)
				if code == "lt" {
					b.WriteString("<")
				} else if code == "gt" {
					b.WriteString(">")
				}
			} else {
				b.WriteString(c)
			}
		} else {
			if c == ">" {
				inTag = false
			}
		}
	}
	return b.String()
}

func readEntityRef(reader *CharReader) string {
	start := reader.Index
	for !reader.Done() {
		c := reader.Next()
		if c == ";" {
			return reader.Content[start : reader.Index-1]
		}
	}

	return ""
}

type CharReader struct {
	Content string
	Index   int
}

func (cr *CharReader) Next() string {
	if cr.Done() {
		return ""
	}

	c := cr.Content[cr.Index : cr.Index+1]
	cr.Index++
	return c
}

func (cr *CharReader) Done() bool {
	return cr.Index >= len(cr.Content)
}

func trimPrefix(s string, prefix string) (string, bool) {
	if strings.HasPrefix(s, prefix) {
		return strings.TrimPrefix(s, prefix), true
	} else {
		return s, false
	}
}

func main() {
	flag.Parse()
	urlString := flag.Arg(0)
	if urlString == "" {
		panic("one command-line argument required")
	}

	err := mainOrErr(urlString)
	if err != nil {
		panic(err)
	}
}

func mainOrErr(urlString string) error {
	url, err := parseUrl(urlString)
	if err != nil {
		return err
	}

	response, err := url.Request()
	if err != nil {
		return err
	}

	if url.ViewSource {
		fmt.Println(response.GetContent())
	} else {
		fmt.Println(response.GetTextContent())
	}
	return nil
}
