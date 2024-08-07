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
	parts := strings.SplitN(text, ":", 2)
	if len(parts) != 2 {
		return Url{}, fmt.Errorf("invalid URL: expected colon")
	}
	scheme := strings.ToLower(parts[0])
	rest := parts[1]

	if scheme == "data" {
		return parseDataUrl(rest)
	} else if scheme == "about" {
		return parseAboutUrl(rest)
	}

	rest = strings.TrimPrefix(rest, "//")

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

func parseDataUrl(rest string) (Url, error) {
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
	return Url{Original: fmt.Sprintf("data:%s", rest), Scheme: "data", Host: "", Port: 0, Path: parts[1], MimeType: mimeType}, nil
}

func parseAboutUrl(rest string) (Url, error) {
	rest = strings.ToLower(rest)
	if rest == "blank" {
		return Url{Original: fmt.Sprintf("about:%s", rest), Scheme: "about", Host: "", Port: 0, Path: rest}, nil
	}
	return Url{}, errors.New("unknown `about:` scheme")
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
