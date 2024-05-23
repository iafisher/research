#!/bin/bash

set -eu

main() {
  cd "$(dirname "$0")"
  docker build -t rpi_builder:latest .
  docker run -v .:/app -w /app rpi_builder:latest make "${1:-all}"
}

main "$@"
