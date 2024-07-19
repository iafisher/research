package internal

import (
	"fmt"
	"os"
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
	root    HtmlElement
	current *HtmlElement
	text    string
	index   int
	start   int
}

// func (p *HtmlParser) Parse(htmlText string) BaseElement {
// 	p.text = htmlText
// 	p.index = 0
// 	p.start = 0
// 	for !p.done() {
// 		i := p.index
// 		runeValue := p.ch()
// 		if runeValue == '<' {
// 			p.addText(i)
// 			p.readTag()
// 		}
// 	}
// 	p.addText(p.index)
// 	return p.root
// }

// func (p *HtmlParser) done() bool {
// 	return p.index >= len(p.text)
// }

// // invariant: p.index sits on the character *after* the opening bracket
// func (p *HtmlParser) readTag() {
// 	isClosing := p.chIf('/')
// 	tag := p.readWord()
// 	fmt.Printf("readWord finished at %d (tag=%q)\n", p.index, tag)
// 	// TODO: parse body of tag
// 	p.readUntil('>')

// 	if isClosing {
// 		p.close(tag)
// 	} else {
// 		p.open(tag)
// 	}
// 	fmt.Printf("readTag finished at %d (tag=%q)\n", p.index, tag)
// 	p.start = p.index
// }

// func (p *HtmlParser) readWord() string {
// 	start := p.index
// 	for !p.done() {
// 		runeValue, width := p.decodeOne()
// 		if !(unicode.IsLetter(runeValue) || unicode.IsDigit(runeValue)) {
// 			return p.text[start:p.index]
// 		}
// 		p.index += width
// 	}
// 	return p.text[start:]
// }

// func (p *HtmlParser) readUntil(delim rune) {
// 	for !p.done() {
// 		runeValue := p.ch()
// 		if runeValue == delim {
// 			return
// 		}
// 	}
// }

// func (p *HtmlParser) chIf(lookingFor rune) bool {
// 	runeValue, width := p.decodeOne()
// 	if runeValue == lookingFor {
// 		p.index += width
// 		return true
// 	} else {
// 		return false
// 	}
// }

// func (p *HtmlParser) ch() rune {
// 	r, width := p.decodeOne()
// 	p.index += width
// 	return r
// }

// func (p *HtmlParser) decodeOne() (rune, int) {
// 	// TODO: don't assume UTF-8 encoding
// 	return utf8.DecodeRuneInString(p.text[p.index:])
// }

// func (p *HtmlParser) close(tag string) {
// 	fmt.Printf("close (index=%d): %q\n", p.index, tag)
// 	if len(p.unfinished) == 0 {
// 		parserWarning("unmatched closing tag")
// 		return
// 	}

// 	last := p.unfinished[len(p.unfinished)-1]
// 	p.unfinished = p.unfinished[:len(p.unfinished)-1]
// 	if last.Tag != tag {
// 		parserWarning(fmt.Sprintf("expected closing tag for %q but got %q", tag, last.Tag))
// 	}

// 	fmt.Printf("unfinished: %+v\n", p.unfinished)
// 	fmt.Printf("root: %+v\n", p.root)
// }

// func (p *HtmlParser) open(tag string) {
// 	fmt.Printf("open (index=%d): %q\n", p.index, tag)
// 	parent := p.parent()
// 	elem := HtmlElement{Tag: tag, Parent: parent}
// 	if parent != nil {
// 		parent.Children = append(parent.Children, elem)
// 		fmt.Printf("parent not nil (%p, root=%p): %+v\n", parent, &p.root, parent)
// 		p.unfinished = append(p.unfinished, &parent.Children[len(parent.Children)-1])
// 	} else {
// 		fmt.Println("parent is nil")
// 		p.root = elem
// 		p.unfinished = append(p.unfinished, &p.root)
// 	}
// 	fmt.Printf("unfinished: %+v\n", p.unfinished)
// 	fmt.Printf("root: %+v\n", p.root)
// }

// func (p *HtmlParser) addText(i int) {
// 	text := p.text[p.start:i]
// 	if len(text) > 0 {
// 		fmt.Printf("adding text: %q\n", text)
// 		parent := p.parent()
// 		// TODO: what if parent is none?
// 		parent.Children = append(parent.Children, TextElement{Text: text, Parent: parent})
// 		fmt.Printf("adding text: parent: %+v (%p)\n", parent, parent)
// 		fmt.Printf("adding text: root: %+v\n", p.root)
// 	}
// }

// func (p *HtmlParser) parent() *HtmlElement {
// 	if len(p.unfinished) > 0 {
// 		return p.unfinished[len(p.unfinished)-1]
// 	} else {
// 		return nil
// 	}
// }

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
