package main

import (
	"bufio"
	"bytes"
	"crypto/tls"
	"errors"
	"flag"
	"fmt"
	"net"
	"strconv"
	"strings"
)

type HttpResponse struct {
	Version           string
	Status            string
	StatusExplanation string
	Headers           map[string]string
	Content           string
}

type Url struct {
	Scheme string
	Host   string
	Port   int
	Path   string
}

func (url Url) Request() (HttpResponse, error) {
	var conn net.Conn
	var err error
	hostPort := fmt.Sprintf("%s:%d", url.Host, url.PortOrDefault())
	if url.Scheme == "http" {
		conn, err = net.Dial("tcp", hostPort)
	} else if url.Scheme == "https" {
		conn, err = tls.Dial("tcp", hostPort, &tls.Config{})
	} else {
		return HttpResponse{}, errors.New("unknown URL scheme")
	}
	if err != nil {
		return HttpResponse{}, err
	}
	defer conn.Close()

	fmt.Fprintf(conn, "GET %s HTTP/1.0\r\nHost: %s\r\n\r\n", url.Path, url.Host)
	reader := bufio.NewReader(conn)

	statusLine, err := readHttpLine(reader)
	if err != nil {
		return HttpResponse{}, err
	}
	statusParts := strings.SplitN(statusLine, " ", 3)
	version := statusParts[0]
	status := statusParts[1]
	statusExplanation := statusParts[2]

	responseHeaders := make(map[string]string)
	for {
		line, err := readHttpLine(reader)
		if err != nil {
			return HttpResponse{}, err
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
		return HttpResponse{}, errors.New("transfer-encoding header not supported")
	}

	// TODO: handle this case
	_, ok = responseHeaders["content-encoding"]
	if ok {
		return HttpResponse{}, errors.New("content-encoding header not supported")
	}

	// TODO: use Content-Length header if present
	content, err := readToEnd(reader)
	if err != nil {
		return HttpResponse{}, err
	}

	return HttpResponse{
		Version:           version,
		Status:            status,
		StatusExplanation: statusExplanation,
		Headers:           responseHeaders,
		// TODO: read charset from Content-Type header
		Content: string(content),
	}, nil
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

func parseUrl(text string) (Url, error) {
	parts := strings.SplitN(text, "://", 2)
	scheme := strings.ToLower(parts[0])
	rest := parts[1]

	if scheme != "http" && scheme != "https" {
		panic("only http and https are supported as URL scheme")
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

	return Url{Scheme: scheme, Host: strings.ToLower(host), Port: port, Path: path}, nil
}

func printHtml(content string) {
	inTag := false
	for _, c := range content {
		if c == '<' {
			inTag = true
		} else if c == '>' {
			inTag = false
		} else if !inTag {
			fmt.Printf("%c", c)
		}
	}
	fmt.Println()
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

	// fmt.Printf("%+v\n", response)
	printHtml(response.Content)
	return nil
}
