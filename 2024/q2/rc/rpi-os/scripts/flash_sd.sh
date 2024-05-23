#!/bin/bash

set -eu

main() {
  cd $(dirname $(dirname "$0"))
  source scripts/utils.sh

  ensure_plugged_in

  if is_debian_kernel; then
    echo "kernel8.img appears to be Debian; making a back-up"
    cp "$KERNEL_PATH" "$KERNEL_BACKUP_PATH"
  fi

  if [[ -e "$KERNEL2712_PATH" ]]; then
    echo "backing up $KERNEL2712_PATH"
    mv "$KERNEL2712_PATH" "$KERNEL2712_BACKUP_PATH"
  fi

  cp kernel8.img "$SD_PATH"
  cp config/bare_metal.txt "$CONFIG_PATH"

  ls -l "$SD_PATH"/*.img
  echo
  echo "SD card flashed with bare-metal OS"
}

main "$@"
