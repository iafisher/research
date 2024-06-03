#ifndef RPI_OS_P_GPIO_H
#define RPI_OS_P_GPIO_H

#include "peripherals/base.h"

// pp. 90-91 of datasheet
#define GPFSEL1         (PBASE+0x00200004)
#define GPSET0          (PBASE+0x0020001C)
#define GPCLR0          (PBASE+0x00200028)
#define GPPUD           (PBASE+0x00200094)
#define GPPUDCLK0       (PBASE+0x00200098)

#endif  /* RPI_OS_P_GPIO_H */
