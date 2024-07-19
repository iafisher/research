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
	Text          string
	IsItalic      bool
	IsBold        bool
	IsSuperscript bool
	BaseFont      *ttf.Font
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

type Engine struct {
	htmlText    string
	raw         bool
	fonts       map[int]*ttf.Font
	lineBuffer  []DisplayListItem
	maxY        int32
	cursorX     int32
	cursorY     int32
	displayList []DisplayListItem
}

// if raw is true then text is rendered as-is, not treated as HTML
func (engine *Engine) Layout(width int32, height int32) DisplayList {
	engine.displayList = []DisplayListItem{}
	engine.maxY = 0
	engine.cursorX = 0
	engine.cursorY = 0
	engine.fonts = make(map[int]*ttf.Font)

	for _, elem := range extractText(engine.htmlText, engine.raw) {
		engine.layoutOne(elem, width, height)
	}
	engine.flush(false)

	return DisplayList{Items: engine.displayList, MaxY: engine.maxY}
}

func (engine *Engine) layoutOne(elem LineElement, width int32, height int32) {
	switch t := elem.(type) {
	case Word:
		font := engine.loadFont(t)
		if font == nil {
			return
		}

		wordWidth, _, err := font.SizeUTF8(t.Content)
		if err != nil {
			layoutWarning(fmt.Sprintf("error from font.SizeUTF8: %s", err.Error()))
			return
		}

		if engine.cursorX+int32(wordWidth) > width {
			engine.flush(false)
		}

		spaceWidth, _, err := font.SizeUTF8(" ")
		if err != nil {
			layoutWarning(fmt.Sprintf("error from font.SizeUTF8 (space width): %s", err.Error()))
			return
		}

		content := DisplayListItemText{Text: t.Content, IsItalic: t.IsItalic, IsBold: t.IsBold, IsSuperscript: t.IsSuperscript, BaseFont: font}
		engine.lineBuffer = append(engine.lineBuffer, DisplayListItem{X: engine.cursorX, Y: engine.cursorY, Content: content})
		engine.cursorX += int32(wordWidth + spaceWidth)
	case Break:
		engine.flush(t.IsParagraph)
		return
	case Emoji:
		content := DisplayListItemEmoji{Code: t.Code}
		engine.lineBuffer = append(engine.lineBuffer, DisplayListItem{X: engine.cursorX, Y: engine.cursorY, Content: content})
		// TODO: compute actual width
		engine.cursorX += HSTEP
	}

	if engine.cursorX >= width {
		engine.flush(false)
	}
}

// we accumulate display items into the line buffer, and then flush them when we hit the end of the line.
// flush() is responsible for determining the vertical position of elements (e.g., in case words have different
// font sizes on the same line).
func (engine *Engine) flush(isParagraph bool) {
	if len(engine.lineBuffer) == 0 {
		return
	}

	maxAscent := 0
	maxDescent := 0

	for _, elem := range engine.lineBuffer {
		switch t := elem.Content.(type) {
		case DisplayListItemText:
			maxAscent = max(t.BaseFont.Ascent(), maxAscent)
			// Descent() returns a negative value
			maxDescent = max(-1*t.BaseFont.Descent(), maxDescent)
			// TODO: handle other display list item content types
		}
	}

	for i := range engine.lineBuffer {
		elem := &engine.lineBuffer[i]
		switch t := elem.Content.(type) {
		case DisplayListItemText:
			ascent := t.BaseFont.Ascent()
			// superscript text is aligned at the top of the line
			if !t.IsSuperscript {
				elem.Y += int32(maxAscent - ascent)
			}
			// TODO: handle other display list item content types
		}
	}

	engine.displayList = append(engine.displayList, engine.lineBuffer...)
	engine.cursorX = 0

	yInc := int32(float32(maxAscent)*1.25) + int32(maxDescent)
	if isParagraph {
		yInc *= 2
	}

	engine.cursorY += yInc
	engine.maxY = max(engine.maxY, engine.cursorY)
	engine.lineBuffer = []DisplayListItem{}
}

func (engine *Engine) loadFont(word Word) *ttf.Font {
	fontSize := word.FontSize
	font, ok := engine.fonts[fontSize]
	if !ok {
		var err error
		font, err = ttf.OpenFont(BASE_FONT, fontSize)
		if err != nil {
			layoutWarning(fmt.Sprintf("error opening font (size=%d): %s", fontSize, err.Error()))
			return nil
		}
		engine.fonts[fontSize] = font
	}
	return font
}

func (engine *Engine) Cleanup() {
	for _, value := range engine.fonts {
		value.Close()
	}
}

type LineElement interface {
	lineElement()
}

type Word struct {
	Content       string
	IsItalic      bool
	IsBold        bool
	IsSuperscript bool
	FontSize      int
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
	text := replaceEntityRefs(htmlText)
	r := []LineElement{}
	isItalic := false
	isBold := false
	isSuperscript := false
	fontSize := 16
	fontSizeRestore := fontSize
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
				if tag == "/p" {
					r = append(r, Break{IsParagraph: true})
				} else if tag == "br" {
					r = append(r, Break{IsParagraph: false})
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
				} else if tag == "sup" {
					isSuperscript = true
					fontSizeRestore = fontSize
					fontSize /= 2
				} else if tag == "/sup" {
					isSuperscript = false
					fontSize = fontSizeRestore
				}
			} else {
				for _, word := range strings.Split(tagOrNot.Content, " ") {
					if word == "" {
						continue
					}

					// TODO: detect emojis
					r = append(r, Word{Content: word, IsItalic: isItalic, IsBold: isBold, IsSuperscript: isSuperscript, FontSize: fontSize})
				}
			}
		}
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
