package main

import (
	"fmt"

	"github.com/iafisher/browser-engineering/internal"
)

func main() {
	gui := internal.Gui{Width: 800, Height: 600}
	gui.Init()
	defer gui.Cleanup()
	gui.Show()
	// verbose := flag.Bool("verbose", false, "turn on verbose output")
	// noPrint := flag.Bool("no-print", false, "do not print responses")
	// flag.Parse()

	// if *verbose {
	// 	internal.SetVerbose(true)
	// }

	// argCount := len(flag.Args())
	// if argCount == 0 {
	// 	fmt.Fprintf(os.Stderr, "error: one command-line argument required\n")
	// 	os.Exit(1)
	// }

	// fetcher := internal.NewUrlFetcher()
	// defer fetcher.Cleanup()

	// success := true
	// for _, urlString := range flag.Args() {
	// 	if argCount > 1 {
	// 		fmt.Printf("tincan: fetching URL %s\n\n", urlString)
	// 	}
	// 	err := fetchAndPrintOne(&fetcher, urlString, *noPrint)
	// 	if err != nil {
	// 		fmt.Fprintf(os.Stderr, "error: could not fetch URL %s: %s\n", urlString, err.Error())
	// 		success = false
	// 	} else {
	// 		if argCount > 1 {
	// 			fmt.Printf("tincan: finished fetching URL %s\n\n", urlString)
	// 		}
	// 	}
	// }

	// if !success {
	// 	os.Exit(2)
	// }
}

func fetchAndPrintOne(fetcher *internal.UrlFetcher, urlString string, noPrint bool) error {
	url, err := internal.ParseUrl(urlString)
	if err != nil {
		return err
	}

	response, err := fetcher.Fetch(url)
	if err != nil {
		return err
	}

	if !noPrint {
		if url.ViewSource {
			fmt.Println(response.GetContent())
		} else {
			fmt.Println(response.GetTextContent())
		}
	}

	return nil
}
