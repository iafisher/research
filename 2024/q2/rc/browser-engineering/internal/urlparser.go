package internal

import (
	"errors"
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

type Url struct {
	Original   string
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

func checkUrlScheme(scheme string) bool {
	// if you had a new scheme here, you must update url.Request()
	return scheme == "http" || scheme == "https" || scheme == "file" || scheme == "data"
}

func ParseUrl(text string) (Url, error) {
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

	return Url{Original: text, Scheme: scheme, Host: strings.ToLower(host), Port: port, Path: path, ViewSource: viewSource}, nil
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
	return Url{Original: text, Scheme: "data", Host: "", Port: 0, Path: parts[1], MimeType: mimeType}, nil
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
