package internal

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"
)

func TestRequest(t *testing.T) {
	testServer := launchServer(t)
	defer testServer.Cleanup(t)

	url, err := ParseUrl(fmt.Sprintf("http://localhost:%d/example.txt", testServer.Port))
	assertNoErr(t, err)

	fetcher := NewUrlFetcher()

	r, err := fetcher.Fetch(url)
	assertNoErr(t, err)

	assertStrEqual(t, r.GetContent(), EXAMPLE_TXT_CONTENTS)

	url, err = ParseUrl(fmt.Sprintf("http://localhost:%d/example.html", testServer.Port))
	assertNoErr(t, err)

	r, err = fetcher.Fetch(url)
	assertNoErr(t, err)

	assertStrEqual(t, r.GetContent(), EXAMPLE_HTML_CONTENTS)
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
	time.Sleep(500 * time.Millisecond)
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
		t.Fatalf("unexpected error: %s", err.Error())
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
