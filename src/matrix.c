#include "matrix.h"
#include "board_config.h"
#include "pico/stdlib.h"

void matrix_init(void) {
    for (unsigned row = 0; row < MATRIX_ROWS; ++row) {
        gpio_init(row_gpios[row]);
        gpio_disable_pulls(row_gpios[row]);
        gpio_put(row_gpios[row], 0);
        gpio_set_dir(row_gpios[row], GPIO_IN);
    }
    for (unsigned col = 0; col < MATRIX_COLS; ++col) {
        gpio_init(col_gpios[col]);
        gpio_set_dir(col_gpios[col], GPIO_IN);
        gpio_pull_up(col_gpios[col]);
    }
}

void matrix_scan(matrix_row_t raw[MATRIX_ROWS]) {
    for (unsigned row = 0; row < MATRIX_ROWS; ++row) {
        /* Only the selected cathode/row sinks current. All other rows float.
         * Driving inactive rows high would contend through diode-less switches.
         */
        gpio_set_dir(row_gpios[row], GPIO_OUT);
        sleep_us(MATRIX_SETTLE_US);
        raw[row] = 0;
        for (unsigned col = 0; col < MATRIX_COLS; ++col) {
            if (!gpio_get(col_gpios[col])) raw[row] |= (matrix_row_t)(1u << col);
        }
        gpio_set_dir(row_gpios[row], GPIO_IN);
    }
}
