//go:build testing

package internal

import "testing"

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
