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
	X       int32
	Y       int32
	Content DisplayListItemContent
}

type DisplayListItemContent interface {
	displayListItemContent()
}

type DisplayListItemText struct {
	Text     string
	IsItalic bool
	IsBold   bool
	BaseFont *ttf.Font
}

type DisplayListItemEmoji struct {
	Code string
}

func (x DisplayListItemText) displayListItemContent()  {}
func (x DisplayListItemEmoji) displayListItemContent() {}

const HSTEP int32 = 15
const VSTEP int32 = 18
const LINE_SPACING float32 = 1.25
const BASE_FONT string = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"

// if raw is true then text is rendered as-is, not treated as HTML
func Layout(htmlText string, raw bool, width int32, height int32) DisplayList {
	items := []DisplayListItem{}
	var maxY int32 = 0
	var cursorX int32 = 0
	var cursorY int32 = 0

	fonts := make(map[int]*ttf.Font)

	for _, elem := range extractText(htmlText, raw) {
		var err error

		fontSize := elem.GetFontSize()
		font, ok := fonts[fontSize]
		if !ok {
			font, err = ttf.OpenFont(BASE_FONT, fontSize)
			if err != nil {
				layoutWarning(fmt.Sprintf("error opening font (size=%d): %s", fontSize, err.Error()))
				continue
			}
			fonts[fontSize] = font
		}
		fontLineHeight := int32(font.Ascent() + font.Descent())
		fontLineHeightSpaced := int32(float32(fontLineHeight) * LINE_SPACING)

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

			spaceWidth, _, err := font.SizeUTF8(" ")
			if err != nil {
				layoutWarning(fmt.Sprintf("error from font.SizeUTF8 (space width): %s", err.Error()))
				continue
			}

			content := DisplayListItemText{Text: t.Content, IsItalic: t.IsItalic, IsBold: t.IsBold, BaseFont: font}
			items = append(items, DisplayListItem{X: cursorX, Y: cursorY, Content: content})
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
			content := DisplayListItemEmoji{Code: t.Code}
			items = append(items, DisplayListItem{X: cursorX, Y: cursorY, Content: content})
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
	GetFontSize() int
}

type Word struct {
	Content  string
	IsItalic bool
	IsBold   bool
	FontSize int
}

type Break struct {
	IsParagraph bool
	FontSize    int
}

type Emoji struct {
	Code     string
	FontSize int
}

func (w Word) GetFontSize() int  { return w.FontSize }
func (b Break) GetFontSize() int { return b.FontSize }
func (e Emoji) GetFontSize() int { return e.FontSize }

func (w Word) lineElement()  {}
func (b Break) lineElement() {}
func (e Emoji) lineElement() {}

func extractText(htmlText string, raw bool) []LineElement {
	text := replaceEntityRefs(htmlText)
	r := []LineElement{}
	isItalic := false
	isBold := false
	fontSize := 16
	for _, line := range strings.Split(text, "\n") {
		var tagsOrNot []TagOrNot
		if raw {
			tagsOrNot = []TagOrNot{{Content: line, IsTag: false}}
		} else {
			tagsOrNot = stripTags(line)
		}

		for _, tagOrNot := range tagsOrNot {
			if tagOrNot.IsTag {
				tag := tagOrNot.Content
				if tag == "p" {
					r = append(r, Break{IsParagraph: true})
				} else if tag == "i" {
					isItalic = true
				} else if tag == "/i" {
					isItalic = false
				} else if tag == "b" {
					isBold = true
				} else if tag == "/b" {
					isBold = false
				} else if tag == "big" {
					fontSize += 4
				} else if tag == "/big" {
					fontSize -= 4
				} else if tag == "small" {
					fontSize -= 2
				} else if tag == "/small" {
					fontSize += 2
				}
			} else {
				for _, word := range strings.Split(tagOrNot.Content, " ") {
					if word == "" {
						continue
					}

					// TODO: detect emojis
					r = append(r, Word{Content: word, IsItalic: isItalic, IsBold: isBold, FontSize: fontSize})
				}
			}
		}
		r = append(r, Break{IsParagraph: false, FontSize: fontSize})
	}
	return r
}

type TagOrNot struct {
	Content string
	IsTag   bool
}

func stripTags(htmlText string) []TagOrNot {
	inTag := false
	startOfTag := -1
	reader := CharReader{Content: htmlText}

	r := []TagOrNot{}
	for !reader.Done() {
		runeValue := reader.Next()
		if !inTag {
			if runeValue == '<' {
				startOfTag = reader.Index
				inTag = true
				continue
			}
		} else {
			if runeValue == '>' {
				fullTagBody := htmlText[startOfTag : reader.Index-1]
				r = append(r, TagOrNot{Content: strings.SplitN(fullTagBody, " ", 2)[0], IsTag: true})
				inTag = false
			}
			continue
		}

		r = append(r, TagOrNot{Content: string(runeValue), IsTag: false})
	}

	return mergeText(r)
}

func mergeText(tags []TagOrNot) []TagOrNot {
	r := []TagOrNot{}
	var sb strings.Builder
	for _, tag := range tags {
		if tag.IsTag {
			if sb.Len() > 0 {
				r = append(r, TagOrNot{Content: sb.String(), IsTag: false})
				sb.Reset()
			}
			r = append(r, tag)
		} else {
			sb.WriteString(tag.Content)
		}
	}

	if sb.Len() > 0 {
		r = append(r, TagOrNot{Content: sb.String(), IsTag: false})
	}

	return r
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
