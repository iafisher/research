package internal

import (
	"fmt"
	"os"
	"strings"
	"unicode"
	"unicode/utf8"
)

// TODO: would be better to have separate HtmlElement and TextElement classes
// (but this makes typing harder, especially for TreeBuilder)
type HtmlElement struct {
	Tag      string
	Attrs    map[string]string
	Text     string
	Children []HtmlElement
	Parent   *HtmlElement
}

func (e HtmlElement) String() string {
	if e.Text != "" {
		return e.Text
	}

	var sb strings.Builder
	sb.WriteString("<")
	sb.WriteString(e.Tag)
	for key, value := range e.Attrs {
		sb.WriteString(fmt.Sprintf(" %s=%s", key, quote(value)))
	}
	sb.WriteString(">")

	for _, child := range e.Children {
		sb.WriteString(child.String())
	}

	sb.WriteString(fmt.Sprintf("</%s>", e.Tag))
	return sb.String()
}

type HtmlParser struct {
	text                string
	index               int
	start               int
	tb                  TreeBuilder
	disableImplicitTags bool
	inScriptTag         bool
}

func (p *HtmlParser) Parse(htmlText string) *HtmlElement {
	p.text = htmlText
	p.index = 0
	p.start = 0
	p.tb = TreeBuilder{}

	for !p.done() {
		i := p.index
		runeValue := p.ch()
		if runeValue == '<' && (!p.inScriptTag || p.startsWith("/script>")) {
			p.implicitTags("")
			p.tb.Text(p.text[p.start:i])
			p.readTag()
		}
	}
	p.implicitTags("")
	p.tb.Text(p.text[p.start:])
	return p.tb.Tree()
}

func (p *HtmlParser) done() bool {
	return p.index >= len(p.text)
}

var SELF_CLOSING_TAGS = map[string]bool{
	"area":   true,
	"base":   true,
	"br":     true,
	"col":    true,
	"embed":  true,
	"hr":     true,
	"img":    true,
	"input":  true,
	"link":   true,
	"meta":   true,
	"param":  true,
	"source": true,
	"track":  true,
	"wbr":    true,
}
var HEAD_TAGS = map[string]bool{
	"base":     true,
	"basefont": true,
	"bgsound":  true,
	"noscript": true,
	"link":     true,
	"meta":     true,
	"title":    true,
	"style":    true,
	"script":   true,
}

// invariant: p.index sits on the character *after* the opening bracket
func (p *HtmlParser) readTag() {
	if p.startsWith("!--") {
		p.readComment()
		return
	}

	isClosing := p.chIf('/')
	tag := p.readTagName()
	attrs := p.readTagAttrs()
	p.start = p.index

	// ignore <!doctype> declaration and comments
	if strings.HasPrefix(tag, "!") {
		return
	}

	if tag == "script" {
		p.inScriptTag = !isClosing
	}

	if isClosing {
		p.tb.Close(tag)
	} else {
		p.implicitTags(tag)
		p.tb.Open(tag, attrs)
		if isSelfClosing(tag) {
			p.tb.Close(tag)
		}
	}
}

func (p *HtmlParser) readComment() {
	for !p.done() && !p.startsWith("-->") {
		p.ch()
	}

	if p.startsWith("-->") {
		p.index += 3
	}

	p.start = p.index
}

func isSelfClosing(tag string) bool {
	ok1, ok2 := SELF_CLOSING_TAGS[tag]
	return ok2 && ok1
}

func isHeadTag(tag string) bool {
	ok1, ok2 := HEAD_TAGS[tag]
	return ok2 && ok1
}

func (p *HtmlParser) readTagName() string {
	start := p.index
	for !p.done() {
		runeValue, width := p.decodeOne()
		if !(unicode.IsLetter(runeValue) || unicode.IsDigit(runeValue) || runeValue == '!') {
			return p.text[start:p.index]
		}
		p.index += width
	}
	return strings.ToLower(p.text[start:])
}

func (p *HtmlParser) readTagAttrs() map[string]string {
	r := map[string]string{}
	for {
		p.skipWhitespace()
		isOver := p.chIf('>')
		if isOver {
			break
		}

		key, value := p.readOneAttr()
		r[key] = value
	}
	return r
}

func (p *HtmlParser) readOneAttr() (string, string) {
	start := p.index
	for !p.done() {
		runeValue, width := p.decodeOne()
		if unicode.IsSpace(runeValue) {
			return p.text[start:p.index], ""
		} else if runeValue == '=' {
			break
		} else {
			p.index += width
		}
	}

	name := p.text[start:p.index]
	value := ""
	if p.startsWith("=") {
		p.ch()
		value = p.readOneAttrValue()
	}
	return name, value
}

func (p *HtmlParser) readOneAttrValue() string {
	if p.startsWith("\"") {
		return p.readQuotedString()
	} else {
		start := p.index
		for !p.done() {
			runeValue, width := p.decodeOne()
			if unicode.IsSpace(runeValue) {
				break
			} else {
				p.index += width
			}
		}
		return p.text[start:p.index]
	}
}

func (p *HtmlParser) readQuotedString() string {
	p.ch()
	start := p.index
	end := len(p.text)
	for !p.done() {
		index := p.index
		runeValue := p.ch()
		if runeValue == '"' {
			end = index
			break
		} else if runeValue == '\\' {
			// TODO: actually decode backslash escapes
			p.ch()
		}
	}
	return p.text[start:end]
}

func (p *HtmlParser) implicitTags(tag string) {
	if p.disableImplicitTags {
		return
	}

	for {
		openTags := len(p.tb.stack)
		var lastTag string
		var secondToLastTag string
		if openTags >= 2 {
			lastTag = p.tb.stack[openTags-1].Tag
			secondToLastTag = p.tb.stack[openTags-2].Tag
		} else if openTags == 1 {
			lastTag = p.tb.stack[0].Tag
		}

		if lastTag == "" && tag != "html" {
			// if no tags are open and we see something other than <html>, we have to open <html> first
			parserWarning(fmt.Sprintf("implicitly opening <html> tag ahead of %q", tag))
			p.tb.Open("html", map[string]string{})
		} else if openTags == 1 && lastTag == "html" && tag != "head" && tag != "body" && tag != "" {
			// if only <html> is open and we see something other than <head> or <body>, we must open one of thsoe first
			if isHeadTag(tag) {
				parserWarning(fmt.Sprintf("implicitly opening <head> tag ahead of %q", tag))
				p.tb.Open("head", map[string]string{})
			} else {
				parserWarning(fmt.Sprintf("implicitly opening <body> tag ahead of %q", tag))
				p.tb.Open("body", map[string]string{})
			}
		} else if openTags == 2 && lastTag == "head" && secondToLastTag == "html" && tag != "" && !isHeadTag(tag) {
			// if we are in <head> and we see a non-head tag, we must close the <head>
			parserWarning(fmt.Sprintf("implicitly closing <head> tag ahead of %q", tag))
			p.tb.Close("head")
		} else {
			break
		}
	}
}

func (p *HtmlParser) readUntil(delim rune) string {
	start := p.index
	for !p.done() {
		i := p.index
		runeValue := p.ch()
		if runeValue == delim {
			return p.text[start:i]
		}
	}
	return p.text[start:]
}

func (p *HtmlParser) skipWhitespace() {
	for !p.done() {
		runeValue, width := p.decodeOne()
		if unicode.IsSpace(runeValue) {
			p.index += width
		} else {
			break
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

func (p *HtmlParser) startsWith(prefix string) bool {
	return strings.HasPrefix(p.text[p.index:], prefix)
}

func (p *HtmlParser) decodeOne() (rune, int) {
	// TODO: don't assume UTF-8 encoding
	return utf8.DecodeRuneInString(p.text[p.index:])
}

type TreeBuilder struct {
	root  HtmlElement
	stack []*HtmlElement
}

func (tb *TreeBuilder) Open(tag string, attrs map[string]string) {
	tag = strings.ToLower(tag)
	elementsToReopen := tb.maybeCloseParent(tag)

	elem := HtmlElement{Tag: tag, Attrs: attrs}
	if len(tb.stack) == 0 {
		tb.root = elem
		tb.stack = []*HtmlElement{&tb.root}
	} else {
		current := tb.stack[len(tb.stack)-1]
		current.Children = append(current.Children, elem)
		tb.stack = append(tb.stack, &current.Children[len(current.Children)-1])
	}

	tb.maybeReopenElements(elementsToReopen)
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
	stripped := strings.TrimSpace(text)
	if len(stripped) == 0 {
		return
	}

	if len(tb.stack) == 0 {
		parserWarning("saw text at document root")
		return
	}

	current := tb.stack[len(tb.stack)-1]
	current.Children = append(current.Children, HtmlElement{Text: text})
}

func (tb *TreeBuilder) Tree() *HtmlElement {
	setParents(&tb.root)
	return &tb.root
}

func (tb *TreeBuilder) maybeCloseParent(tag string) []*HtmlElement {
	// <p>X<p>Y</p> should be interpreted as <p>X</p><p>Y</p>
	// i.e., the nested <p> opens a new paragraph
	// this may require us to close and reopen tags that were open if <p> is not the direct parent
	// e.g., <p><b>X<p>Y</b></p> becomes <p><b>X</b></p><p><b>Y</b></p> (notice how <b> is reopened)

	if len(tb.stack) == 0 || (tag != "p" && tag != "li") {
		return []*HtmlElement{}
	}

	stopAt := []string{}
	if tag == "li" {
		stopAt = append(stopAt, "ul", "ol")
	}

	index := tb.findLastOpenTag(tag, stopAt)
	if index == -1 {
		return []*HtmlElement{}
	}

	tagsToReopen := tb.stack[index+1:]
	numToClose := len(tb.stack) - index

	for numToClose > 0 {
		tb.closeLast()
		numToClose--
	}

	return tagsToReopen
}

func (tb *TreeBuilder) maybeReopenElements(elems []*HtmlElement) {
	for _, elem := range elems {
		tb.Open(elem.Tag, elem.Attrs)
	}
}

func (tb *TreeBuilder) closeLast() {
	tb.Close(tb.stack[len(tb.stack)-1].Tag)
}

func (tb *TreeBuilder) findLastOpenTag(tagToSearch string, stopAt []string) int {
	for i := len(tb.stack) - 1; i >= 0; i-- {
		thisTag := tb.stack[i].Tag

		for _, stopAtTag := range stopAt {
			if thisTag == stopAtTag {
				return -1
			}
		}

		if thisTag == tagToSearch {
			return i
		}
	}
	return -1
}

func setParents(elem *HtmlElement) {
	for i := range elem.Children {
		elem.Children[i].Parent = elem
		setParents(&elem.Children[i])
	}
}

func printTree(root *HtmlElement, indent int) {
	for i := 0; i < indent; i++ {
		fmt.Print(" ")
	}

	if root.Tag != "" {
		fmt.Printf("<%s> %d attr(s)\n", root.Tag, len(root.Attrs))
		for i := range root.Children {
			printTree(&root.Children[i], indent+2)
		}
	} else {
		fmt.Printf("%d char(s) of text\n", len(root.Text))
	}
}

func parserWarning(msg string) {
	fmt.Fprintf(os.Stderr, "parser: warning: %s\n", msg)
}

func quote(s string) string {
	return fmt.Sprintf("\"%s\"", strings.ReplaceAll(s, "\"", "\\\""))
}
