package internal

import (
	"fmt"
	"os"
	"regexp"
	"strings"
	"unicode/utf8"

	"github.com/veandco/go-sdl2/ttf"
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
func Layout(htmlText string, raw bool, font *ttf.Font, width int32, height int32) DisplayList {
	items := []DisplayListItem{}
	var maxY int32 = 0
	var cursorX int32 = 0
	var cursorY int32 = 0

	spaceWidth, _, err := font.SizeUTF8(" ")
	if err != nil {
		layoutWarning(fmt.Sprintf("error from font.SizeUTF8 for space width: %s", err.Error()))
		spaceWidth = 15
	}

	fontLineHeight := int32(font.Ascent() + font.Descent())
	fontLineHeightSpaced := int32(float32(fontLineHeight) * 1.25)
	for _, elem := range extractText(htmlText, raw) {
		var elemHeight int32
		switch t := elem.(type) {
		case Word:
			wordWidth, wordHeight, err := font.SizeUTF8(t.Content)
			if err != nil {
				layoutWarning(fmt.Sprintf("error from font.SizeUTF8: %s", err.Error()))
				continue
			}
			elemHeight = int32(wordHeight)

			if cursorX+int32(wordWidth) > width {
				cursorX = 0
				cursorY += fontLineHeightSpaced
			}

			items = append(items, DisplayListItem{X: cursorX, Y: cursorY, C: t.Content})
			cursorX += int32(wordWidth)
			cursorX += int32(spaceWidth)
		case Break:
			cursorX = 0
			if t.IsParagraph {
				cursorY += fontLineHeight * 2
			} else {
				cursorY += fontLineHeightSpaced
			}
			elemHeight = 0
			continue
		case Emoji:
			items = append(items, DisplayListItem{X: cursorX, Y: cursorY, EmojiCode: t.Code})
			cursorX += HSTEP
			elemHeight = VSTEP
		}

		if cursorY > maxY {
			maxY = cursorY + elemHeight
		}

		if cursorX >= width {
			cursorX = 0
			cursorY += fontLineHeightSpaced
		}
	}

	return DisplayList{Items: items, MaxY: maxY}
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

func layoutWarning(msg string) {
	fmt.Fprintf(os.Stderr, "tincan: layout: warning: %s", msg)
}
