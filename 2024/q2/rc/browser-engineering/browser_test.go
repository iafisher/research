package main

import "testing"

func TestParseUrl(t *testing.T) {
	var url = parseUrl("http://example.com/index.html")
	assertStrEqual(t, url.Scheme, "http")
	assertStrEqual(t, url.Host, "example.com")
	assertStrEqual(t, url.Path, "/index.html")

	url = parseUrl("http://sub.example.com")
	assertStrEqual(t, url.Scheme, "http")
	assertStrEqual(t, url.Host, "sub.example.com")
	assertStrEqual(t, url.Path, "/")
}

func assertStrEqual(t *testing.T, actual string, expected string) {
	t.Helper()
	if expected != actual {
		t.Errorf("strings not equal: expected %q, got %q", expected, actual)
	}
}
