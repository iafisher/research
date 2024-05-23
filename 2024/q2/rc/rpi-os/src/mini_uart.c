void uart_init(void) {
  // Manual: https://github.com/raspberrypi/documentation/files/1888662/BCM2837-ARM-Peripherals.-.Revised.-.V2-1.pdf

  // == Activate the GPIO pins ==
  // Note that bit numbers are 0-indexed.
  unsigned int selector = get32(GPFSEL1);
  // This line clears bits 12-14.
  //
  //   7          =           0000 0111
  //   7 << 12    = 0111 0000 0000 0000
  //   ~(7 << 12) = 1000 1111 1111 1111
  //
  // Bits 12-14 set the function of pin 14. (p. 92)
  selector &= ~(7 << 12);
  // This line sets bits 12-14 to 010.
  //
  //   2 =                 0000 0010
  //   2 << 12 = 0010 0000 0000 0000
  //              ^^^
  //
  // 010 sets the alternative function to 5 (p. 92), which is UART 1 Transmit Data for pin 14 (p. 102).
  selector |= 2 << 12;
  // This line clears bits 15-17 (pin 15).
  selector &= ~(7 << 15);
  // This line sets bit 15-17 to 010 (UART 1 Receive Data).
  selector |= 2 << 15;
  put32(GPFSEL1, selector);

  // === Set pull-up/pull-down state ===
  // Set the state to 0 (meaning neither pull-up nor pull-down), as described on p. 101.
  //
  // Pull-up/pull-down refers to the behavior of the pin when nothing is connected to it. We don't
  // care because we are going to connect a serial line to our pins.
  put32(GPPUD, 0);
  delay(150);
  put32(GPPUDCLK0, (1 << 14) | (1 << 15));
  delay(150);
  put32(GPPUDCLK0, 0);

  // === Initialize the Mini UART device ===
  // Enable Mini UART.
  put32(AUX_ENABLE, 1);
  // Disable receiver/transmitter temporarily while configuring. (p. 16)
  //
  // Also, permanently disable auto flow control as it doesn't work with our TTL-to-serial cable.
  put32(AUX_MU_CNTL_REG, 0);
  // Disable interrupts. (p. 12)
  put32(AUX_MU_IER_REG, 0);
  // Enable 8-bit mode. (p. 14)
  put32(AUX_MU_LCR_REG, 3);
  // Set RTS line to high (used for flow control, which we don't need). (p. 14)
  put32(AUX_MU_MCR_REG, 0);
  // Set baud rate to 115200.
  //
  // Formula: `baudrate = system_clock_freq / (8 * (baudrate_reg + 1))` (p. 11)
  //   system_clock_freq = 250 MHz on RPi
  //   baudrate = 115200 for the terminal emulator
  put32(AUX_MU_BAUD_REG, 270);

  // Enable receiver/transmitter again.
  put32(AUX_MU_CNTL_REG, 3);
}

void uart_send(char c) {
  while (1) {
    // bit 5 is set if the transmitter can accept another byte. (p. 15)
    if (get32(AUX_MU_LSR_REG) & 0x20) {
      break;
    }
  }

  // (p. 11)
  put32(AUX_MU_IO_REG, c);
}

char uart_recv(void) {
  while (1) {
    // bit 0 is set if the receiver has a byte to be read. (p. 15)
    if ((get32(AUX_MU_IIR_REG) & 6) == 2) {
      break;
    }
  }

  // (p. 11)
  return get32(AUX_MU_IO_REG) & 0xFF;
}

void uart_send_string(const char* str) {
  for (size_t i = 0; str[i] != '\0'; i++) {
    uart_send(str[i]);
  }
}
