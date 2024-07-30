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
	parser := HtmlParser{disableImplicitTags: true}
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
	parser := HtmlParser{disableImplicitTags: true}
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

func TestParseImplicitTags(t *testing.T) {
	parser := HtmlParser{}
	root := parser.Parse("<p>Hello</p>")
	assertStrEqual(t, root.String(), "<html><body><p>Hello</p></body></html>")

	root = parser.Parse("<title>Title</title><p>Hello</p>")
	assertStrEqual(t, root.String(), "<html><head><title>Title</title></head><body><p>Hello</p></body></html>")
}

func TestParseComments(t *testing.T) {
	parser := HtmlParser{disableImplicitTags: true}
	root := parser.Parse("<p>Hello<!-- a comment --> world!</p>")
	assertStrEqual(t, root.String(), "<p>Hello world!</p>")

	root = parser.Parse("<p>Hello<!-- a comment with a tag: <p> --></p>")
	assertStrEqual(t, root.String(), "<p>Hello</p>")

	root = parser.Parse("<p>Hello<!--></p>")
	assertStrEqual(t, root.String(), "<p>Hello</p>")
}

func TestParseNestedParagraphs(t *testing.T) {
	parser := HtmlParser{disableImplicitTags: true}
	root := parser.Parse("<div><p>Hello<p>World!</p></div>")
	assertStrEqual(t, root.String(), "<div><p>Hello</p><p>World!</p></div>")

	root = parser.Parse("<div><P><b class=\"whatever\">Hello<p>World!</b></p></div>")
	assertStrEqual(t, root.String(), "<div><p><b class=\"whatever\">Hello</b></p><p><b class=\"whatever\">World!</b></p></div>")
}

func TestParseNestedListItems(t *testing.T) {
	parser := HtmlParser{disableImplicitTags: true}
	root := parser.Parse("<ul><li>one<li>two</li></ul>")
	assertStrEqual(t, root.String(), "<ul><li>one</li><li>two</li></ul>")

	// nested list
	root = parser.Parse("<ul><li>one<ol><li>nested</li></ol></li></ul>")
	assertStrEqual(t, root.String(), "<ul><li>one<ol><li>nested</li></ol></li></ul>")
}

func TestScriptElement(t *testing.T) {
	parser := HtmlParser{disableImplicitTags: true}
	root := parser.Parse("<script>x < 5 && x > 0</script>")
	assertStrEqual(t, root.String(), "<script>x < 5 && x > 0</script>")
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
