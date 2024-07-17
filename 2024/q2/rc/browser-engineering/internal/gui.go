package internal

import (
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/veandco/go-sdl2/sdl"
	"github.com/veandco/go-sdl2/ttf"
)

type Gui struct {
	Width       int32
	Height      int32
	Scroll      int32
	displayList []DisplayListItem
	window      *sdl.Window
	font        *ttf.Font
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
	gui.displayList = Layout(text, gui.Width, gui.Height)
	gui.Draw()

	gui.window.UpdateSurface()
	gui.eventLoop()
	return nil
}

func (gui *Gui) Draw() error {
	start := time.Now()
	surface, err := gui.window.GetSurface()
	if err != nil {
		return err
	}

	// clear the screen
	surface.FillRect(nil, 0)

	for _, item := range gui.displayList {
		if gui.isOffscreen(item.Y) {
			continue
		}

		renderedText, err := gui.font.RenderUTF8Blended(item.C, sdl.Color{R: 255, G: 255, B: 255, A: 255})
		if err != nil {
			fmt.Fprintf(os.Stderr, "gui: warning: could not render character (code=%d): %s\n", item.C[0], err.Error())
			continue
		}
		defer renderedText.Free()

		err = renderedText.Blit(nil, surface, &sdl.Rect{X: item.X, Y: item.Y - gui.Scroll})
		if err != nil {
			fmt.Fprintf(os.Stderr, "gui: warning: could not blit rendered text at X=%d, Y=%d\n", item.X, item.Y)
			continue
		}
	}

	timeElapsed := time.Since(start)
	PrintVerbose(fmt.Sprintf("gui: redraw time: %d ms", timeElapsed.Milliseconds()))

	return nil
}

func (gui *Gui) isOffscreen(y int32) bool {
	return y > gui.Scroll+gui.Height || y+VSTEP < gui.Scroll
}

const SCROLL_STEP int32 = 10

func (gui *Gui) scrollDown() {
	gui.Scroll += SCROLL_STEP
	gui.Draw()
}

func (gui *Gui) scrollUp() {
	gui.Scroll -= SCROLL_STEP
	if gui.Scroll < 0 {
		gui.Scroll = 0
	}
	gui.Draw()
}

func (gui *Gui) eventLoop() {
	running := true
	for running {
		for event := sdl.PollEvent(); event != nil; event = sdl.PollEvent() {
			switch t := event.(type) {
			case *sdl.KeyboardEvent:
				// fmt.Printf("gui: keyboard event: %+v\n", t)
				// https://wiki.libsdl.org/SDL2/SDL_Scancode
				if t.Keysym.Scancode == sdl.SCANCODE_DOWN {
					gui.scrollDown()
				} else if t.Keysym.Scancode == sdl.SCANCODE_UP {
					gui.scrollUp()
				}
			case *sdl.QuitEvent:
				running = false
				return
			}
		}
		gui.window.UpdateSurface()
		sdl.Delay(33)
	}
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
