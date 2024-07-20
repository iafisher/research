package internal

import (
	"fmt"
	"os"
	"regexp"
	"strings"

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
	htmlTree    *HtmlElement
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

	var tf TreeFlattener
	for _, elem := range tf.FlattenTree(engine.htmlTree) {
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

type TreeWalker interface {
	StartTag(string, map[string]string)
	EndTag(string)
	Text(string)
}

type TreeFlattener struct {
	lineElements    []LineElement
	isItalic        bool
	isBold          bool
	isSuperscript   bool
	fontSize        int
	fontSizeRestore int
}

func walkTree(tree *HtmlElement, walker TreeWalker) {
	if tree.Tag == "" {
		walker.Text(tree.Text)
	} else {
		walker.StartTag(tree.Tag, tree.Attrs)
		for i := range tree.Children {
			walkTree(&tree.Children[i], walker)
		}
		walker.EndTag(tree.Tag)
	}
}

const DEFAULT_FONT_SIZE = 16

// font size increment for <big> tags
const BIG_FONT_SIZE_INCREMENT = 4

// font size decrement for <small> tags
const SMALL_FONT_SIZE_DECREMENT = 2

// font size factor (divided by) for <sup> tags
const SUP_FONT_SIZE_FACTOR = 2

func (tf *TreeFlattener) FlattenTree(tree *HtmlElement) []LineElement {
	tf.lineElements = []LineElement{}
	tf.isItalic = false
	tf.isBold = false
	tf.isSuperscript = false
	tf.fontSize = DEFAULT_FONT_SIZE
	tf.fontSizeRestore = tf.fontSize

	walkTree(tree, tf)

	return tf.lineElements
}

func (tf *TreeFlattener) StartTag(tag string, attrs map[string]string) {
	if tag == "i" {
		tf.isItalic = true
	} else if tag == "b" {
		tf.isBold = true
	} else if tag == "big" {
		tf.fontSize += BIG_FONT_SIZE_INCREMENT
	} else if tag == "small" {
		tf.fontSize -= SMALL_FONT_SIZE_DECREMENT
	} else if tag == "sup" {
		if !tf.isSuperscript {
			tf.isSuperscript = true
			tf.fontSizeRestore = tf.fontSize
			tf.fontSize /= SUP_FONT_SIZE_FACTOR
		}
	} else if tag == "br" {
		tf.lineElements = append(tf.lineElements, Break{IsParagraph: false})
	}
}

func (tf *TreeFlattener) EndTag(tag string) {
	if tag == "i" {
		tf.isItalic = false
	} else if tag == "b" {
		tf.isBold = false
	} else if tag == "big" {
		tf.fontSize -= BIG_FONT_SIZE_INCREMENT
	} else if tag == "small" {
		tf.fontSize += SMALL_FONT_SIZE_DECREMENT
	} else if tag == "sup" {
		tf.isSuperscript = false
		tf.fontSize = tf.fontSizeRestore
	} else if tag == "p" {
		tf.lineElements = append(tf.lineElements, Break{IsParagraph: true})
	}
}

func (tf *TreeFlattener) Text(text string) {
	// TODO: detect emojis
	tf.lineElements = append(tf.lineElements, tf.makeWord(text))
}

func (tf *TreeFlattener) makeWord(text string) Word {
	return Word{
		// TODO: more principled handling of whitespace
		Content:       replaceEntityRefs(strings.ReplaceAll(text, "\n", " ")),
		IsItalic:      tf.isItalic,
		IsBold:        tf.isBold,
		IsSuperscript: tf.isSuperscript,
		FontSize:      tf.fontSize,
	}
}

func replaceEntityRefs(text string) string {
	// TODO: compile once
	pat := regexp.MustCompile(`\&([A-Za-z]+;)`)
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

func layoutWarning(msg string) {
	fmt.Fprintf(os.Stderr, "tincan: layout: warning: %s", msg)
}
