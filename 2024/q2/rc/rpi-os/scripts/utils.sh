SD_PATH=/Volumes/bootfs
KERNEL_PATH="$SD_PATH"/kernel8.img
KERNEL_BACKUP_PATH="$SD_PATH"/backup_debian_kernel.img
KERNEL2712_PATH="$SD_PATH"/kernel_2712.img
KERNEL2712_BACKUP_PATH="$SD_PATH"/backup_kernel_2712.img
CONFIG_PATH="$SD_PATH"/config.txt

ensure_plugged_in() {
  if [[ ! -e "$SD_PATH" ]]; then
    echo "SD card not found at $SD_PATH"
    exit 1
  fi
}

is_debian_kernel() {
  sz=$(stat -f '%z' "$KERNEL_PATH")
  if [[ "$sz" -gt 100000 ]]; then
    return 0
  else
    return 1
  fi
}
