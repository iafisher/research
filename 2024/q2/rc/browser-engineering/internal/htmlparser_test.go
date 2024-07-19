package internal

import (
	"testing"
)

func TestTreeBuilder(t *testing.T) {
	emptyAttrs := map[string]string{}

	tb := TreeBuilder{}
	tb.Open("p", emptyAttrs)
	tb.Open("bold", emptyAttrs)
	tb.Text("Hello")
	tb.Close("bold")
	tb.Text(" world")
	tb.Close("p")
	root := tb.Tree()

	assertIsHtml(t, root, "p")
	assertIntEqual(t, len(root.Children), 2)
	assertParentEqual(t, root, nil)

	bold := &root.Children[0]
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
	root := parser.Parse("<p class=\"whatever\"><bold>Hello</bold> world</p>")

	assertIsHtml(t, root, "p")
	assertIntEqual(t, len(root.Children), 2)
	assertStrEqual(t, root.Attrs["class"], "whatever")
	assertParentEqual(t, root, nil)

	bold := &root.Children[0]
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

func TestParseMissingClosingTags(t *testing.T) {
	parser := HtmlParser{}
	root := parser.Parse("<p><i><bold>Hello")

	assertIsHtml(t, root, "p")
	assertIntEqual(t, len(root.Children), 1)
	assertIsHtml(t, &root.Children[0], "i")
	assertIntEqual(t, len(root.Children[0].Children), 1)
	assertIsHtml(t, &root.Children[0].Children[0], "bold")
	assertIntEqual(t, len(root.Children[0].Children[0].Children), 1)
	txt := &root.Children[0].Children[0].Children[0]
	assertIsText(t, txt)
	assertStrEqual(t, txt.Text, "Hello")
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
