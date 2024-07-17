package internal

import (
	"fmt"
	"os"
	"strings"

	"github.com/veandco/go-sdl2/sdl"
	"github.com/veandco/go-sdl2/ttf"
)

type Gui struct {
	Width  int32
	Height int32
	window *sdl.Window
	font   *ttf.Font
}

func (gui *Gui) Init() error {
	err := ttf.Init()
	if err != nil {
		return err
	}

	err = sdl.Init(sdl.INIT_EVERYTHING)
	if err != nil {
		return err
	}

	// gui.font, err = ttf.OpenFont("./assets/Atkinson_Hyperlegible/AtkinsonHyperlegible-Regular.ttf", 16)
	gui.font, err = ttf.OpenFont("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 16)
	if err != nil {
		return err
	}

	gui.window, err = sdl.CreateWindow("TinCan", sdl.WINDOWPOS_UNDEFINED, sdl.WINDOWPOS_UNDEFINED, gui.Width, gui.Height, sdl.WINDOW_SHOWN)
	if err != nil {
		return err
	}
	return nil
}

func (gui *Gui) ShowTextPage(text string) error {
	surface, err := gui.window.GetSurface()
	if err != nil {
		return err
	}

	text = stripNewlines(text)
	var cursorX int32 = 0
	var cursorY int32 = 0
	for _, c := range text {
		// TODO: why does this URL have so many null bytes?
		// https://browser.engineering/examples/xiyouji.html
		if c == 0 {
			continue
		}

		renderedText, err := gui.font.RenderUTF8Blended(string(c), sdl.Color{R: 255, G: 255, B: 255, A: 255})
		if err != nil {
			fmt.Fprintf(os.Stderr, "gui: warning: could not render character (code=%d): %s\n", c, err.Error())
			continue
		}
		defer renderedText.Free()

		err = renderedText.Blit(nil, surface, &sdl.Rect{X: cursorX, Y: cursorY})
		if err != nil {
			return err
		}

		cursorX += 15
		if cursorX >= gui.Width {
			cursorX = 0
			cursorY += 18

			if cursorY >= gui.Height {
				fmt.Fprintln(os.Stderr, "gui: warning: fell off bottom of page")
				break
			}
		}
	}

	gui.window.UpdateSurface()

	running := true
	for running {
		for event := sdl.PollEvent(); event != nil; event = sdl.PollEvent() {
			switch event.(type) {
			case *sdl.QuitEvent:
				running = false
				break
			}
		}
		sdl.Delay(33)
	}

	return nil
}

func stripNewlines(text string) string {
	return strings.ReplaceAll(text, "\n", " ")
}

func (gui *Gui) Cleanup() {
	gui.window.Destroy()
	gui.font.Close()
	sdl.Quit()
	ttf.Quit()
}
