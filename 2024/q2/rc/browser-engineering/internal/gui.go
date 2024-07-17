package internal

import (
	"github.com/veandco/go-sdl2/sdl"
)

type Gui struct {
	Width  int32
	Height int32
	window *sdl.Window
}

func (gui *Gui) Init() error {
	err := sdl.Init(sdl.INIT_EVERYTHING)
	if err != nil {
		return err
	}
	gui.window, err = sdl.CreateWindow("test", sdl.WINDOWPOS_UNDEFINED, sdl.WINDOWPOS_UNDEFINED, gui.Width, gui.Height, sdl.WINDOW_SHOWN)
	if err != nil {
		return err
	}
	return nil
}

func (gui *Gui) Show() error {
	surface, err := gui.window.GetSurface()
	if err != nil {
		return err
	}
	surface.FillRect(nil, 0)

	rect := sdl.Rect{0, 0, 200, 200}
	color := sdl.Color{R: 255, G: 0, B: 255, A: 255}
	pixel := sdl.MapRGBA(surface.Format, color.R, color.G, color.B, color.A)
	surface.FillRect(&rect, pixel)
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

func (gui *Gui) Cleanup() {
	sdl.Quit()
	gui.window.Destroy()
}
