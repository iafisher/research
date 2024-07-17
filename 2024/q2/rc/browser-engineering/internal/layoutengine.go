package internal

import (
	"fmt"
	"unicode/utf8"
)

type DisplayListItem struct {
	X         int32
	Y         int32
	C         string
	EmojiCode string
}

const HSTEP int32 = 15
const VSTEP int32 = 18

// if raw is true then text is rendered as-is, not treated as HTML
func Layout(htmlText string, raw bool, width int32, height int32) DisplayList {
	items := []DisplayListItem{}
	var maxY int32 = 0
	var cursorX int32 = 0
	var cursorY int32 = 0

	inTag := false
	startOfTag := -1
	reader := CharReader{Content: htmlText}

	for !reader.Done() {
		runeValue := reader.Next()
		if !raw {
			if !inTag {
				if runeValue == '<' {
					inTag = true
					startOfTag = reader.Index
					continue
				} else if runeValue == '&' {
					code := readEntityRef(&reader)
					if code == "lt" {
						runeValue = '<'
					} else if code == "gt" {
						runeValue = '>'
					}
				}
			} else {
				if runeValue == '>' {
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

		if runeValue == '\n' {
			cursorX = 0
			cursorY += VSTEP
			continue
		}

		emojiCode := lookUpEmojiCode(runeValue)

		items = append(items, DisplayListItem{X: cursorX, Y: cursorY, C: string(runeValue), EmojiCode: emojiCode})
		if cursorY > maxY {
			maxY = cursorY
		}

		cursorX += HSTEP
		if cursorX >= width {
			cursorX = 0
			cursorY += VSTEP
		}
	}

	return DisplayList{Items: items, MaxY: maxY + VSTEP}
}

func lookUpEmojiCode(runeValue rune) string {
	emojiCode := fmt.Sprintf("%X", runeValue)
	filePath := fmt.Sprintf("%s/%s.png", EMOJI_PATH, emojiCode)
	if DoesFileExist(filePath) {
		return emojiCode
	} else {
		return ""
	}
}

func readEntityRef(reader *CharReader) string {
	start := reader.Index
	for !reader.Done() {
		c := reader.Next()
		if c == ';' {
			return reader.Content[start : reader.Index-1]
		}
	}

	return ""
}

type CharReader struct {
	Content string
	Index   int
}

func (cr *CharReader) Next() rune {
	if cr.Done() {
		return 0
	}

	// TODO: probably very inefficient?
	runeValue, width := utf8.DecodeRuneInString(cr.Content[cr.Index:])
	cr.Index += width
	return runeValue
}

func (cr *CharReader) Done() bool {
	return cr.Index >= len(cr.Content)
}
