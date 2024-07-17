package main

import (
	"flag"
	"fmt"
	"os"

	"github.com/iafisher/browser-engineering/internal"
)

func main() {
	verbose := flag.Bool("verbose", false, "turn on verbose output")
	noGui := flag.Bool("no-gui", false, "do not open browser GUI")
	flag.Parse()

	if *verbose {
		internal.SetVerbose(true)
	}

	argCount := len(flag.Args())
	if argCount == 0 {
		fmt.Fprintf(os.Stderr, "error: one command-line argument required\n")
		os.Exit(1)
	}

	fetcher := internal.NewUrlFetcher()
	defer fetcher.Cleanup()

	gui := internal.Gui{Width: 800, Height: 600}
	if !*noGui {
		gui.Init()
		defer gui.Cleanup()
	}

	success := true
	for _, urlString := range flag.Args() {
		if argCount > 1 {
			fmt.Printf("tincan: fetching URL %s\n\n", urlString)
		}
		err := fetchAndShowOne(&fetcher, &gui, urlString, *noGui)
		if err != nil {
			fmt.Fprintf(os.Stderr, "error: could not fetch URL %s: %s\n", urlString, err.Error())
			success = false
		} else {
			if argCount > 1 {
				fmt.Printf("tincan: finished fetching URL %s\n\n", urlString)
			}
		}
	}

	if !success {
		os.Exit(2)
	}
}

func fetchAndShowOne(fetcher *internal.UrlFetcher, gui *internal.Gui, urlString string, noGui bool) error {
	url, err := internal.ParseUrl(urlString)
	if err != nil {
		fmt.Fprintf(os.Stderr, "tincan: error parsing URL: %s\n", err.Error())
		url = internal.Url{Scheme: "about", Path: "blank"}
	}

	response, err := fetcher.Fetch(url)
	if err != nil {
		return err
	}

	if !noGui {
		// TODO: not sure that data URLs are handled properly anymore
		err = gui.ShowTextPage(response.GetContent(), url.ViewSource)
		if err != nil {
			return err
		}
	}

	return nil
}
