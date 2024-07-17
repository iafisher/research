package internal

import (
	"unicode/utf8"
)

type DisplayListItem struct {
	X int32
	Y int32
	C string
}

const HSTEP int32 = 15
const VSTEP int32 = 18

// if raw is true then text is rendered as-is, not treated as HTML
func Layout(htmlText string, raw bool, width int32, height int32) []DisplayListItem {
	r := []DisplayListItem{}
	var cursorX int32 = 0
	var cursorY int32 = 0

	inTag := false
	startOfTag := -1
	reader := CharReader{Content: htmlText}

	for !reader.Done() {
		c := reader.Next()
		if !raw {
			if !inTag {
				if c == "<" {
					inTag = true
					startOfTag = reader.Index
					continue
				} else if c == "&" {
					code := readEntityRef(&reader)
					if code == "lt" {
						c = "<"
					} else if code == "gt" {
						c = ">"
					}
				}
			} else {
				if c == ">" {
					inTag = false
					// TODO: doesn't work if element has attributes, e.g. `<p class="whatever'>`

					tagName := reader.Content[startOfTag : reader.Index-1]
					if tagName == "p" {
						cursorY += VSTEP * 2
					}
				}
				continue
			}
		}

		if c == "\n" {
			cursorX = 0
			cursorY += VSTEP
			continue
		}

		r = append(r, DisplayListItem{X: cursorX, Y: cursorY, C: c})

		cursorX += HSTEP
		if cursorX >= width {
			cursorX = 0
			cursorY += VSTEP
		}
	}

	return r
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

	// TODO: probably very inefficient?
	runeValue, width := utf8.DecodeRuneInString(cr.Content[cr.Index:])
	cr.Index += width
	return string(runeValue)
}

func (cr *CharReader) Done() bool {
	return cr.Index >= len(cr.Content)
}
