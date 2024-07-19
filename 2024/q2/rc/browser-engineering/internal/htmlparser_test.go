package internal

import (
	"fmt"
	"testing"
)

func TestTreeBuilder(t *testing.T) {
	tb := TreeBuilder{}
	tb.Open("p")
	tb.Open("bold")
	tb.Text("Hello")
	tb.Close("bold")
	tb.Text(" world")
	tb.Close("p")
	root := tb.Tree()

	assertIsHtml(t, root, "p")
	assertIntEqual(t, len(root.Children), 2)
	assertParentEqual(t, root, nil)

	bold := &root.Children[0]
	fmt.Printf("test: root: %p\n", root)
	fmt.Printf("test: bold: %p\n", bold)
	assertIsHtml(t, bold, "bold")
	assertIntEqual(t, len(bold.Children), 1)
	assertParentEqual(t, bold, root)

	txt := &bold.Children[0]
	assertIsText(t, txt)
	assertStrEqual(t, txt.Text, "Hello")
	assertParentEqual(t, txt, bold)

	txt = &root.Children[1]
	assertIsText(t, txt)
	assertStrEqual(t, txt.Text, " world")
	assertParentEqual(t, txt, root)
}

func TestParseHtml(t *testing.T) {
	parser := HtmlParser{}
	root := parser.Parse("<p><bold>Hello</bold> world</p>")

	assertIsHtml(t, root, "p")
	assertIntEqual(t, len(root.Children), 2)
	assertParentEqual(t, root, nil)

	bold := &root.Children[0]
	fmt.Printf("test: root: %p\n", root)
	fmt.Printf("test: bold: %p\n", bold)
	assertIsHtml(t, bold, "bold")
	assertIntEqual(t, len(bold.Children), 1)
	assertParentEqual(t, bold, root)

	txt := &bold.Children[0]
	assertIsText(t, txt)
	assertStrEqual(t, txt.Text, "Hello")
	assertParentEqual(t, txt, bold)

	txt = &root.Children[1]
	assertIsText(t, txt)
	assertStrEqual(t, txt.Text, " world")
	assertParentEqual(t, txt, root)
}

func assertIsHtml(t *testing.T, elem *HtmlElement, tag string) {
	t.Helper()
	if elem.Tag == "" {
		t.Fatalf("expected HTML element %q but got something else: %+v", tag, elem)
	}

	if elem.Tag != tag {
		t.Errorf("expected HTML element %q but got %q", tag, elem.Tag)
	}
}

func assertIsText(t *testing.T, elem *HtmlElement) {
	t.Helper()
	if elem.Tag != "" {
		t.Fatalf("expected text element but got <%s>", elem.Tag)
	}
}

func assertParentEqual(t *testing.T, elem *HtmlElement, p *HtmlElement) {
	t.Helper()
	if elem.Parent != p {
		t.Errorf("expected parent to be %p but was %p", p, elem.Parent)
	}
}
