package internal

import (
	"testing"
)

func TestParseUrl(t *testing.T) {
	url, err := ParseUrl("http://example.com/index.html")
	assertNoErr(t, err)
	assertStrEqual(t, url.Scheme, "http")
	assertStrEqual(t, url.Host, "example.com")
	assertStrEqual(t, url.Path, "/index.html")
	assertIntEqual(t, url.Port, 0)
	assertIntEqual(t, url.PortOrDefault(), 80)

	url, err = ParseUrl("http://example.com:8080/index.html")
	assertNoErr(t, err)
	assertStrEqual(t, url.Scheme, "http")
	assertStrEqual(t, url.Host, "example.com")
	assertStrEqual(t, url.Path, "/index.html")
	assertIntEqual(t, url.Port, 8080)

	url, err = ParseUrl("https://sub.example.com")
	assertNoErr(t, err)
	assertStrEqual(t, url.Scheme, "https")
	assertStrEqual(t, url.Host, "sub.example.com")
	assertStrEqual(t, url.Path, "/")
	assertIntEqual(t, url.PortOrDefault(), 443)

	url, err = ParseUrl("file:///Users/ian/test.txt")
	assertNoErr(t, err)
	assertStrEqual(t, url.Scheme, "file")
	assertStrEqual(t, url.Host, "")
	assertStrEqual(t, url.Path, "/Users/ian/test.txt")

	url, err = ParseUrl("data:text/html,Hello world!")
	assertNoErr(t, err)
	assertStrEqual(t, url.Scheme, "data")
	assertStrEqual(t, url.Host, "")
	assertStrEqual(t, url.Path, "Hello world!")
	assertStrEqual(t, url.MimeType.Type, "text")
	assertStrEqual(t, url.MimeType.Subtype, "html")

	url, err = ParseUrl("ABOUT:BLANK")
	assertNoErr(t, err)
	assertStrEqual(t, url.Scheme, "about")
	assertStrEqual(t, url.Host, "")
	assertStrEqual(t, url.Path, "blank")
}

func TestParseMimeType(t *testing.T) {
	mtype, err := parseMimeType("application/octet-stream")
	assertNoErr(t, err)
	assertStrEqual(t, mtype.Type, "application")
	assertStrEqual(t, mtype.Subtype, "octet-stream")
	assertStrEqual(t, mtype.ParameterName, "")
	assertStrEqual(t, mtype.ParameterValue, "")

	mtype, err = parseMimeType("text/plain;charset=utf-8")
	assertNoErr(t, err)
	assertStrEqual(t, mtype.Type, "text")
	assertStrEqual(t, mtype.Subtype, "plain")
	assertStrEqual(t, mtype.ParameterName, "charset")
	assertStrEqual(t, mtype.ParameterValue, "utf-8")
}
