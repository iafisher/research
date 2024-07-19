Following along with [Web Browser Engineering](https://browser.engineering/), in Go.

You will need to download the PNG Color 72x72 emoji pack from [OpenMoji](https://openmoji.org/) and
place it in `assets/openmoji` to render emoji.

To run tests:

```shell
$ go test ./internal
```

## Structure
1. The **URL fetcher** resolves the URL (`http://`, `https://`, `file:///`, etc.) and fetches the resource. (`urlfetcher.go`)
2. The resource is passed to the **GUI** to be shown. (`gui.go`)
3. The GUI calls the **layout engine** to compute the position of elements. (`layoutengine.go`)
4. The GUI draws the elements from the layout engine on the screen.

### URL fetcher
- HTTP request encoding
- HTTP request decoding
- TLS support (using the standard library)
- Other resources (`file:///`, `data:`, etc.)

### GUI
- Using SDL2 to draw things on the screen
- Handling user interaction: scrolling, resizing

### Layout engine
- Laying out text and elements
- Breaking long lines
- Positioning text based on font metrics
