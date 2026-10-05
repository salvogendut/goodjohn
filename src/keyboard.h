#ifndef GOODJOHN_KEYBOARD_H
#define GOODJOHN_KEYBOARD_H

#include <stdbool.h>
#include <stdint.h>

enum { MATRIX_ROWS = 10, MATRIX_COLS = 9, KEYBOARD_REPORT_KEYS = 6 };
enum { KEYBOARD_DEBOUNCE_MS = 5 };
typedef uint16_t matrix_row_t;

typedef struct {
    matrix_row_t stable[MATRIX_ROWS];
    matrix_row_t candidate[MATRIX_ROWS];
    uint32_t changed_at[MATRIX_ROWS][MATRIX_COLS];
} keyboard_t;

/* Same eight-byte layout in HID boot and report protocols; no report ID. */
typedef struct {
    uint8_t modifiers;
    uint8_t reserved;
    uint8_t keys[KEYBOARD_REPORT_KEYS];
} keyboard_report_t;

void keyboard_update(keyboard_t *keyboard, const matrix_row_t raw[MATRIX_ROWS],
                     uint32_t now_ms, bool has_diodes);
void keyboard_report(const keyboard_t *keyboard, keyboard_report_t *report);

/* Physical Y1..Y10 by X1..X9, not the CPC's logical 10x8 matrix. */
extern const uint8_t keymap[MATRIX_ROWS][MATRIX_COLS];

#endif
