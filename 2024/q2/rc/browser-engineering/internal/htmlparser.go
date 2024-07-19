package internal

import (
	"fmt"
	"os"
	"unicode"
	"unicode/utf8"
)

// TODO: would be better to have separate HtmlElement and TextElement classes
// (but this makes typing harder, especially for TreeBuilder)
type HtmlElement struct {
	Tag      string
	Text     string
	Children []HtmlElement
	Parent   *HtmlElement
}

type HtmlParser struct {
	text  string
	index int
	start int
	tb    TreeBuilder
}

func (p *HtmlParser) Parse(htmlText string) *HtmlElement {
	p.text = htmlText
	p.index = 0
	p.start = 0
	for !p.done() {
		i := p.index
		runeValue := p.ch()
		if runeValue == '<' {
			p.tb.Text(p.text[p.start:i])
			p.readTag()
		}
	}
	p.tb.Text(p.text[p.start:])
	return p.tb.Tree()
}

func (p *HtmlParser) done() bool {
	return p.index >= len(p.text)
}

// invariant: p.index sits on the character *after* the opening bracket
func (p *HtmlParser) readTag() {
	isClosing := p.chIf('/')
	tag := p.readWord()
	// TODO: parse body of tag
	p.readUntil('>')

	if isClosing {
		p.tb.Close(tag)
	} else {
		p.tb.Open(tag)
	}
	p.start = p.index
}

func (p *HtmlParser) readWord() string {
	start := p.index
	for !p.done() {
		runeValue, width := p.decodeOne()
		if !(unicode.IsLetter(runeValue) || unicode.IsDigit(runeValue)) {
			return p.text[start:p.index]
		}
		p.index += width
	}
	return p.text[start:]
}

func (p *HtmlParser) readUntil(delim rune) {
	for !p.done() {
		runeValue := p.ch()
		if runeValue == delim {
			return
		}
	}
}

func (p *HtmlParser) chIf(lookingFor rune) bool {
	runeValue, width := p.decodeOne()
	if runeValue == lookingFor {
		p.index += width
		return true
	} else {
		return false
	}
}

func (p *HtmlParser) ch() rune {
	r, width := p.decodeOne()
	p.index += width
	return r
}

func (p *HtmlParser) decodeOne() (rune, int) {
	// TODO: don't assume UTF-8 encoding
	return utf8.DecodeRuneInString(p.text[p.index:])
}

type TreeBuilder struct {
	root  HtmlElement
	stack []*HtmlElement
}

func (tb *TreeBuilder) Open(tag string) {
	elem := HtmlElement{Tag: tag}
	if len(tb.stack) == 0 {
		tb.root = elem
		tb.stack = []*HtmlElement{&tb.root}
	} else {
		current := tb.stack[len(tb.stack)-1]
		current.Children = append(current.Children, elem)
		tb.stack = append(tb.stack, &current.Children[len(current.Children)-1])
	}
}

func (tb *TreeBuilder) Close(tag string) {
	if len(tb.stack) == 0 {
		parserWarning(fmt.Sprintf("closing an un-opened tag: %q", tag))
		return
	}

	current := tb.stack[len(tb.stack)-1]
	if current.Tag != tag {
		parserWarning(fmt.Sprintf("expected to close %q but saw %q instead", current.Tag, tag))
	}

	tb.stack = tb.stack[:len(tb.stack)-1]
}

func (tb *TreeBuilder) Text(text string) {
	if len(text) == 0 {
		return
	}

	if len(tb.stack) == 0 {
		parserWarning("saw text at document roo")
		return
	}

	current := tb.stack[len(tb.stack)-1]
	current.Children = append(current.Children, HtmlElement{Text: text})
}

func (tb *TreeBuilder) Tree() *HtmlElement {
	setParents(&tb.root)
	return &tb.root
}

func setParents(elem *HtmlElement) {
	for i := range elem.Children {
		elem.Children[i].Parent = elem
		setParents(&elem.Children[i])
	}
}

func parserWarning(msg string) {
	fmt.Fprintf(os.Stderr, "parser: warning: %s\n", msg)
}
