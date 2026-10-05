#ifndef GOODJOHN_BOARD_CONFIG_H
#define GOODJOHN_BOARD_CONFIG_H

#include <stdint.h>
#include "keyboard.h"

/* GPIO numbers, NOT Pico header pin numbers. See docs/wiring.md. */
static const uint8_t row_gpios[MATRIX_ROWS] = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11};
static const uint8_t col_gpios[MATRIX_COLS] = {12, 13, 14, 15, 16, 17, 18, 19, 20};
enum { MATRIX_SETTLE_US = 5, MATRIX_SCAN_INTERVAL_US = 1000 };

#ifndef GOODJOHN_MATRIX_HAS_DIODES
#define GOODJOHN_MATRIX_HAS_DIODES 0
#endif

#endif
