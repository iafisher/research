package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"
)

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

func TestRequest(t *testing.T) {
	testServer := launchServer(t)
	defer testServer.Cleanup(t)

	url, err := parseUrl(fmt.Sprintf("http://localhost:%d/example.txt", testServer.Port))
	assertNoErr(t, err)

	r, err := url.Request()
	assertNoErr(t, err)

	assertStrEqual(t, r.GetContent(), EXAMPLE_TXT_CONTENTS)

	url, err = parseUrl(fmt.Sprintf("http://localhost:%d/example.html", testServer.Port))
	assertNoErr(t, err)

	r, err = url.Request()
	assertNoErr(t, err)

	assertStrEqual(t, r.GetContent(), EXAMPLE_HTML_CONTENTS)
	assertStrEqual(t, r.GetTextContent(), "Hello, world!")
}

type TestServer struct {
	Tmpdir string
	Port   int
	cmd    *exec.Cmd
}

const TEST_SERVER_PORT = 8383
const EXAMPLE_TXT_CONTENTS = "This is an example file.\n"
const EXAMPLE_HTML_CONTENTS = "<html><body><p>Hello, world!</p></body></html>"

func launchServer(t *testing.T) TestServer {
	tmpdir, err := os.MkdirTemp("", "goserverfiles")
	assertNoErr(t, err)

	fname := filepath.Join(tmpdir, "example.txt")
	err = os.WriteFile(fname, []byte(EXAMPLE_TXT_CONTENTS), 0666)
	assertNoErr(t, err)

	fname = filepath.Join(tmpdir, "example.html")
	err = os.WriteFile(fname, []byte(EXAMPLE_HTML_CONTENTS), 0666)
	assertNoErr(t, err)

	port := TEST_SERVER_PORT
	cmd := exec.Command("python3", "-m", "http.server", fmt.Sprintf("%d", port), "-d", tmpdir)
	err = cmd.Start()
	assertNoErr(t, err)

	// TODO: try to hit server until get a response, instead of sleeping
	time.Sleep(300 * time.Millisecond)
	return TestServer{Tmpdir: tmpdir, Port: port, cmd: cmd}
}

func (ts *TestServer) Cleanup(t *testing.T) {
	err := ts.cmd.Process.Kill()
	assertNoErr(t, err)
	err = os.RemoveAll(ts.Tmpdir)
	assertNoErr(t, err)
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
