package main

import "testing"

func TestParseUrl(t *testing.T) {
	url, err := parseUrl("http://example.com/index.html")
	assertNoErr(t, err)
	assertStrEqual(t, url.Scheme, "http")
	assertStrEqual(t, url.Host, "example.com")
	assertStrEqual(t, url.Path, "/index.html")
	assertIntEqual(t, url.Port, 0)
	assertIntEqual(t, url.PortOrDefault(), 80)

	url, err = parseUrl("http://example.com:8080/index.html")
	assertNoErr(t, err)
	assertStrEqual(t, url.Scheme, "http")
	assertStrEqual(t, url.Host, "example.com")
	assertStrEqual(t, url.Path, "/index.html")
	assertIntEqual(t, url.Port, 8080)

	url, err = parseUrl("https://sub.example.com")
	assertNoErr(t, err)
	assertStrEqual(t, url.Scheme, "https")
	assertStrEqual(t, url.Host, "sub.example.com")
	assertStrEqual(t, url.Path, "/")
	assertIntEqual(t, url.PortOrDefault(), 443)

	url, err = parseUrl("file:///Users/ian/test.txt")
	assertNoErr(t, err)
	assertStrEqual(t, url.Scheme, "file")
	assertStrEqual(t, url.Host, "")
	assertStrEqual(t, url.Path, "/Users/ian/test.txt")

	url, err = parseUrl("data:text/html,Hello world!")
	assertNoErr(t, err)
	assertStrEqual(t, url.Scheme, "data")
	assertStrEqual(t, url.Host, "")
	assertStrEqual(t, url.Path, "Hello world!")
	assertStrEqual(t, url.MimeType.Type, "text")
	assertStrEqual(t, url.MimeType.Subtype, "html")
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

func assertNoErr(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Errorf("unexpected error: %s", err.Error())
	}
}

func assertStrEqual(t *testing.T, actual string, expected string) {
	t.Helper()
	if expected != actual {
		t.Errorf("strings not equal: expected %q, got %q", expected, actual)
	}
}

func assertIntEqual(t *testing.T, actual int, expected int) {
	t.Helper()
	if expected != actual {
		t.Errorf("ints are not equal: expected %d, got %d", expected, actual)
	}
}
