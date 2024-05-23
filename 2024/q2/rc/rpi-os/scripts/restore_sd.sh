#!/bin/bash

set -eu

main() {
  cd $(dirname $(dirname "$0"))
  source scripts/utils.sh

  ensure_plugged_in

  if [[ ! -e "$KERNEL_BACKUP_PATH" ]]; then
    echo "kernel backup not found at $KERNEL_BACKUP_PATH; aborting"
    exit 1
  fi

  cp "$KERNEL_BACKUP_PATH" "$KERNEL_PATH"
  cp "$KERNEL2712_BACKUP_PATH" "$KERNEL2712_PATH"
  cp config/debian.txt "$CONFIG_PATH"

  ls -l "$SD_PATH"/*.img
  echo
  echo "SD card restored to Debian"
}

main "$@"
