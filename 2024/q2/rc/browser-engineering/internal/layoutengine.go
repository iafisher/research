package internal

import (
	"fmt"
	"regexp"
	"strings"
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

	for _, elem := range extractText(htmlText, raw) {
		switch t := elem.(type) {
		case Word:
			items = append(items, DisplayListItem{X: cursorX, Y: cursorY, C: t.Content})
			cursorX += HSTEP * int32(len(t.Content))
		case Break:
			cursorX = 0
			if t.IsParagraph {
				cursorY += VSTEP * 2
			} else {
				cursorY += VSTEP
			}
			continue
		case Emoji:
			items = append(items, DisplayListItem{X: cursorX, Y: cursorY, EmojiCode: t.Code})
			cursorX += HSTEP
		}

		if cursorY > maxY {
			maxY = cursorY
		}

		if cursorX >= width {
			cursorX = 0
			cursorY += VSTEP
		}
	}

	return DisplayList{Items: items, MaxY: maxY + VSTEP}
}

type LineElement interface {
	lineElement()
}

type Word struct {
	Content string
}

type Break struct {
	IsParagraph bool
}

type Emoji struct {
	Code string
}

func (w Word) lineElement()  {}
func (b Break) lineElement() {}
func (e Emoji) lineElement() {}

func extractText(htmlText string, raw bool) []LineElement {
	var text string
	if raw {
		text = htmlText
	} else {
		text = stripTags(htmlText)
	}

	text = replaceEntityRefs(text)
	r := []LineElement{}
	for _, line := range strings.Split(text, "\n") {
		for _, word := range strings.Split(line, " ") {
			if word == "" {
				continue
			}

			// TODO: detect emojis
			r = append(r, Word{Content: word})
		}
		r = append(r, Break{IsParagraph: false})
	}
	return r
}

func stripTags(htmlText string) string {
	inTag := false
	reader := CharReader{Content: htmlText}
	var sb strings.Builder

	for !reader.Done() {
		runeValue := reader.Next()
		if !inTag {
			if runeValue == '<' {
				inTag = true
				continue
			}
		} else {
			if runeValue == '>' {
				inTag = false
			}
			continue
		}

		sb.WriteRune(runeValue)
	}

	return sb.String()
}

func replaceEntityRefs(text string) string {
	// TODO: compile once
	pat := regexp.MustCompile("\\&([A-Za-z]+;)")
	return pat.ReplaceAllStringFunc(text, func(code string) string {
		code = strings.ToLower(code)
		if code == "&gt;" {
			return ">"
		} else if code == "&lt;" {
			return "<"
		} else {
			return code
		}
	})
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
