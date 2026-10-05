#include "keyboard.h"
#include "hid_keys.h"

#include <string.h>

_Static_assert(sizeof(keyboard_report_t) == 8, "HID boot report must be 8 bytes");

void keyboard_update(keyboard_t *keyboard, const matrix_row_t raw[MATRIX_ROWS],
                     uint32_t now_ms, bool has_diodes) {
    matrix_row_t ambiguous[MATRIX_ROWS] = {0};
    if (!has_diodes) {
        for (unsigned a = 0; a < MATRIX_ROWS; ++a) {
            for (unsigned b = a + 1; b < MATRIX_ROWS; ++b) {
                matrix_row_t common = raw[a] & raw[b];
                if (common && (common & (common - 1u))) {
                    ambiguous[a] |= common;
                    ambiguous[b] |= common;
                }
            }
        }
    }

    for (unsigned row = 0; row < MATRIX_ROWS; ++row) {
        /* Block new ambiguous presses, but retain previously accepted holds.
         * Releases still pass through debounce. Never invent a rectangle corner.
         */
        matrix_row_t target = raw[row] & (~ambiguous[row] | keyboard->stable[row]);
        for (unsigned col = 0; col < MATRIX_COLS; ++col) {
            matrix_row_t bit = (matrix_row_t)(1u << col);
            if ((target ^ keyboard->candidate[row]) & bit) {
                keyboard->candidate[row] ^= bit;
                keyboard->changed_at[row][col] = now_ms;
            }
            if ((uint32_t)(now_ms - keyboard->changed_at[row][col]) >= KEYBOARD_DEBOUNCE_MS) {
                keyboard->stable[row] = (keyboard->stable[row] & ~bit) | (target & bit);
            }
        }
    }
}

void keyboard_report(const keyboard_t *keyboard, keyboard_report_t *report) {
    memset(report, 0, sizeof(*report));
    unsigned count = 0;
    bool overflow = false;
    for (unsigned row = 0; row < MATRIX_ROWS; ++row) {
        for (unsigned col = 0; col < MATRIX_COLS; ++col) {
            if (!(keyboard->stable[row] & (1u << col))) continue;
            uint8_t key = keymap[row][col];
            if (key == KEY_NONE) continue;
            if (key >= KEY_LEFT_CTRL && key <= KEY_RIGHT_GUI) {
                report->modifiers |= (uint8_t)(1u << (key - KEY_LEFT_CTRL));
                continue;
            }
            bool duplicate = false;
            for (unsigned i = 0; i < count; ++i) {
                if (report->keys[i] == key) duplicate = true;
            }
            if (duplicate) continue;
            if (count < KEYBOARD_REPORT_KEYS) report->keys[count++] = key;
            else overflow = true;
        }
    }
    if (overflow) memset(report->keys, KEY_ROLLOVER, sizeof(report->keys));
}
