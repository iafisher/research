package internal

import (
	"fmt"
	"os"
	"strings"
)

func trimPrefix(s string, prefix string) (string, bool) {
	if strings.HasPrefix(s, prefix) {
		return strings.TrimPrefix(s, prefix), true
	} else {
		return s, false
	}
}

var CONFIG_VERBOSE bool

func PrintVerbose(msg string) {
	if CONFIG_VERBOSE {
		fmt.Printf("tincan: %s\n", msg)
	}
}

func SetVerbose(v bool) {
	CONFIG_VERBOSE = v
}

func DoesFileExist(filePath string) bool {
	_, err := os.Stat(filePath)
	return err == nil
}
