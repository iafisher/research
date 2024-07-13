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
		printVerbose(fmt.Sprintf("using cached connection to %s", address))
		return existingConn, nil
	}

	var conn net.Conn
	var err error
	if isTls {
		printVerbose(fmt.Sprintf("opening TLS connection to %s", address))
		conn, err = tls.Dial("tcp", address, &tls.Config{})
	} else {
		printVerbose(fmt.Sprintf("opening TCP connection to %s", address))
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
	address := fmt.Sprintf("%s:%d", url.Host, url.PortOrDefault())
	isTls := url.Scheme == "https"
	conn, err := fetcher.openConnection(address, isTls)
	if err != nil {
		return nil, err
	}

	var requestHeaders = map[string]string{
		"Host":       url.Host,
		"Connection": "keep-alive",
		"User-Agent": "Mozilla/5.0 (desktop; rv:0.1) TinCan/0.1",
	}

	requestLine := fmt.Sprintf("GET %s HTTP/1.1\r\n", url.Path)
	_, err = fmt.Fprint(conn, requestLine)
	if err != nil {
		return nil, err
	}

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

	if version == "HTTP/1.0" {
		// in particular, this is necessary because the Python test server only supports HTTP/1.0
		printVerbose(fmt.Sprintf("connection using HTTP/1.0; removing from connection cache: %s", address))
		fetcher.uncache(address)
	}

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
	_, err = reader.Read(content)
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
	printVerbose(fmt.Sprintf("reading local file: %s", url.Path))
	data, err := os.ReadFile(url.Path)
	if err != nil {
		return nil, err
	}
	return &FileResponse{Content: string(data)}, nil
}

func (fetcher *UrlFetcher) fetchData(url Url) *DataResponse {
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

func checkUrlScheme(scheme string) bool {
	// if you had a new scheme here, you must update url.Request()
	return scheme == "http" || scheme == "https" || scheme == "file" || scheme == "data"
}

func parseUrl(text string) (Url, error) {
	if strings.HasPrefix(text, "data:") {
		return parseDataUrl(text)
	}

	parts := strings.SplitN(text, "://", 2)
	if len(parts) != 2 {
		return Url{}, fmt.Errorf("invalid URL: expected '://'")
	}
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

var CONFIG_VERBOSE bool

func printVerbose(msg string) {
	if CONFIG_VERBOSE {
		fmt.Printf("tincan: %s\n", msg)
	}
}

func main() {
	var noPrint bool
	flag.BoolVar(&CONFIG_VERBOSE, "verbose", false, "turn on verbose output")
	flag.BoolVar(&noPrint, "no-print", false, "do not print responses")
	flag.Parse()

	argCount := len(flag.Args())
	if argCount == 0 {
		fmt.Fprintf(os.Stderr, "error: one command-line argument required\n")
		os.Exit(1)
	}

	fetcher := NewUrlFetcher()
	defer fetcher.Cleanup()

	success := true
	for _, urlString := range flag.Args() {
		if argCount > 1 {
			fmt.Printf("tincan: fetching URL %s\n\n", urlString)
		}
		err := fetchAndPrintOne(&fetcher, urlString, noPrint)
		if err != nil {
			fmt.Fprintf(os.Stderr, "error: could not fetch URL %s: %s\n", urlString, err.Error())
			success = false
		} else {
			if argCount > 1 {
				fmt.Printf("tincan: finished fetching URL %s\n\n", urlString)
			}
		}
	}

	if !success {
		os.Exit(2)
	}
}

func fetchAndPrintOne(fetcher *UrlFetcher, urlString string, noPrint bool) error {
	url, err := parseUrl(urlString)
	if err != nil {
		return err
	}

	response, err := fetcher.Fetch(url)
	if err != nil {
		return err
	}

	if !noPrint {
		if url.ViewSource {
			fmt.Println(response.GetContent())
		} else {
			fmt.Println(response.GetTextContent())
		}
	}

	return nil
}
