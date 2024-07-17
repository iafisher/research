package internal

import (
	"fmt"
	"os"
	"time"

	"github.com/veandco/go-sdl2/img"
	"github.com/veandco/go-sdl2/sdl"
	"github.com/veandco/go-sdl2/ttf"
)

type Gui struct {
	Width       int32
	Height      int32
	Scroll      int32
	text        string
	raw         bool
	displayList DisplayList
	window      *sdl.Window
	font        *ttf.Font
}

type DisplayList struct {
	Items []DisplayListItem
	MaxY  int32
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

	gui.font, err = ttf.OpenFont("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 16)
	if err != nil {
		return err
	}

	gui.window, err = sdl.CreateWindow("TinCan", sdl.WINDOWPOS_UNDEFINED, sdl.WINDOWPOS_UNDEFINED, gui.Width, gui.Height, sdl.WINDOW_SHOWN|sdl.WINDOW_RESIZABLE)
	if err != nil {
		return err
	}

	return nil
}

// raw passed on to Layout()
func (gui *Gui) ShowTextPage(text string, raw bool) error {
	gui.text = text
	gui.raw = raw
	gui.displayList = Layout(gui.text, gui.raw, gui.Width, gui.Height)
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

	for _, item := range gui.displayList.Items {
		if gui.isOffscreen(item.Y) {
			continue
		}

		x := item.X
		y := item.Y - gui.Scroll
		if item.EmojiCode != "" {
			gui.drawEmoji(surface, x, y, item.EmojiCode)
		} else {
			gui.drawChar(surface, x, y, item.C)
		}
	}

	gui.drawScrollbar(surface)

	timeElapsed := time.Since(start)
	PrintVerbose(fmt.Sprintf("gui: redraw time: %d ms", timeElapsed.Milliseconds()))

	return nil
}

const SCROLLBAR_HEIGHT int32 = 30
const SCROLLBAR_WIDTH int32 = 5

func (gui *Gui) drawScrollbar(surface *sdl.Surface) {
	scrollbarY := int32((float32(gui.Scroll+SCROLLBAR_HEIGHT) / float32(gui.displayList.MaxY)) * float32(gui.Height))
	rect := sdl.Rect{X: gui.Width - SCROLLBAR_WIDTH, Y: scrollbarY, W: SCROLLBAR_WIDTH, H: SCROLLBAR_HEIGHT}
	surface.FillRect(&rect, sdl.Color{R: 0, G: 0, B: 255, A: sdl.ALPHA_OPAQUE}.Uint32())
}

const EMOJI_PATH string = "assets/openmoji/"

func (gui *Gui) drawEmoji(surface *sdl.Surface, x int32, y int32, emojiCode string) {
	pngImage, err := img.Load(fmt.Sprintf("%s/%s.png", EMOJI_PATH, emojiCode))
	if err != nil {
		guiWarning(fmt.Sprintf("could not load emoji (code=%s): %s\n", emojiCode, err))
		return
	}
	defer pngImage.Free()

	pngImage.BlitScaled(nil, surface, &sdl.Rect{X: x, Y: y, W: HSTEP, H: VSTEP})
}

func (gui *Gui) drawChar(surface *sdl.Surface, x int32, y int32, c string) {
	renderedText, err := gui.font.RenderUTF8Blended(c, sdl.Color{R: 255, G: 255, B: 255, A: 255})
	if err != nil {
		guiWarning(fmt.Sprintf("could not render character (code=%d): %s\n", c[0], err.Error()))
		return
	}
	defer renderedText.Free()

	err = renderedText.Blit(nil, surface, &sdl.Rect{X: x, Y: y})
	if err != nil {
		guiWarning(fmt.Sprintf("could not blit rendered text at X=%d, Y=%d\n", x, y))
	}
}

func (gui *Gui) isOffscreen(y int32) bool {
	return y > gui.Scroll+gui.Height || y+VSTEP < gui.Scroll
}

const SCROLL_STEP int32 = 50

// pixels of padding past the last content that you can scroll to
const BOTTOM_SCROLL_PADDING int32 = 10

func (gui *Gui) scrollDown() {
	maxY := gui.displayList.MaxY + BOTTOM_SCROLL_PADDING
	if maxY < gui.Height {
		return
	}

	gui.Scroll += SCROLL_STEP
	bottomOfScreen := gui.Scroll + gui.Height
	if bottomOfScreen > maxY {
		gui.Scroll = maxY - gui.Height
	}
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
			case *sdl.MouseWheelEvent:
				// TODO: consider magnitude of Y (works fairly well even with this naive impl though)
				if t.Y > 0 {
					gui.scrollUp()
				} else if t.Y < 0 {
					gui.scrollDown()
				}
			case *sdl.QuitEvent:
				running = false
				return
			case *sdl.WindowEvent:
				if t.Event == sdl.WINDOWEVENT_RESIZED {
					gui.Width = t.Data1
					gui.Height = t.Data2
					gui.displayList = Layout(gui.text, gui.raw, gui.Width, gui.Height)
					gui.Draw()
				}
			}
		}
		gui.window.UpdateSurface()
		sdl.Delay(33)
	}
}

func (gui *Gui) Cleanup() {
	gui.window.Destroy()
	gui.font.Close()
	sdl.Quit()
	ttf.Quit()
}

func guiWarning(msg string) {
	fmt.Fprintf(os.Stderr, "gui: warning: %s\n", msg)
}
