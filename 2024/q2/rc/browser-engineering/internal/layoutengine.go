package internal

type DisplayListItem struct {
	X int32
	Y int32
	C string
}

const HSTEP int32 = 15
const VSTEP int32 = 18

func Layout(text string, width int32, height int32) []DisplayListItem {
	r := []DisplayListItem{}
	text = stripNewlines(text)
	var cursorX int32 = 0
	var cursorY int32 = 0
	for _, c := range text {
		// TODO: why does this URL have so many null bytes?
		// https://browser.engineering/examples/xiyouji.html
		if c == 0 {
			continue
		}

		r = append(r, DisplayListItem{X: cursorX, Y: cursorY, C: string(c)})

		cursorX += HSTEP
		if cursorX >= width {
			cursorX = 0
			cursorY += VSTEP
		}
	}
	return r
}
