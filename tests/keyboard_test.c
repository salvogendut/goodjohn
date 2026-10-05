#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "keyboard.h"
#include "hid_keys.h"

/* Keep checks active even in Release builds. */
#define CHECK(expr) do { if (!(expr)) { \
    fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #expr); exit(1); \
} } while (0)

static bool contains(const keyboard_report_t *report, uint8_t key) {
    for (unsigned i = 0; i < KEYBOARD_REPORT_KEYS; ++i) {
        if (report->keys[i] == key) return true;
    }
    return false;
}

static void settle(keyboard_t *keyboard, matrix_row_t *raw, uint32_t time, bool diodes) {
    keyboard_update(keyboard, raw, time, diodes);
    keyboard_update(keyboard, raw, time + KEYBOARD_DEBOUNCE_MS, diodes);
}

static void test_debounce(void) {
    keyboard_t keyboard = {0};
    matrix_row_t raw[MATRIX_ROWS] = {0};
    keyboard_report_t report;
    raw[8] = 1u << 5; /* A */
    keyboard_update(&keyboard, raw, 100, false);
    keyboard_update(&keyboard, raw, 104, false);
    CHECK(keyboard.stable[8] == 0);
    raw[8] = 0; /* Bounce back; the clock must restart. */
    keyboard_update(&keyboard, raw, 105, false);
    raw[8] = 1u << 5;
    keyboard_update(&keyboard, raw, 106, false);
    keyboard_update(&keyboard, raw, 110, false);
    CHECK(keyboard.stable[8] == 0);
    keyboard_update(&keyboard, raw, 111, false);
    keyboard_report(&keyboard, &report);
    CHECK(contains(&report, KEY_A));

    raw[8] = 0;
    keyboard_update(&keyboard, raw, 120, false);
    keyboard_update(&keyboard, raw, 124, false);
    CHECK(keyboard.stable[8] != 0);
    keyboard_update(&keyboard, raw, 125, false);
    keyboard_report(&keyboard, &report);
    keyboard_report_t empty = {0};
    CHECK(memcmp(&report, &empty, sizeof(report)) == 0);
}

static void test_independent_keys_and_wrap(void) {
    keyboard_t keyboard = {0};
    matrix_row_t raw[MATRIX_ROWS] = {0};
    raw[8] = 1u << 5;
    keyboard_update(&keyboard, raw, UINT32_MAX - 2u, false);
    raw[7] = 1u << 4; /* S begins bouncing independently. */
    keyboard_update(&keyboard, raw, UINT32_MAX, false);
    raw[7] = 0;
    keyboard_update(&keyboard, raw, 1, false);
    CHECK(keyboard.stable[8] == 0);
    keyboard_update(&keyboard, raw, 2, false);
    CHECK(keyboard.stable[8] == (1u << 5));
    CHECK(keyboard.stable[7] == 0);
}

static void test_ghost_suppression(void) {
    keyboard_t keyboard = {0};
    matrix_row_t raw[MATRIX_ROWS] = {0};
    raw[8] = 1u << 5; /* Accept A before a rectangle appears. */
    settle(&keyboard, raw, 0, false);
    raw[8] |= 1u << 4;
    raw[7] = (1u << 4) | (1u << 5);
    raw[5] = 1u << 7; /* Unrelated Space should still work. */
    settle(&keyboard, raw, 10, false);
    CHECK(keyboard.stable[8] == (1u << 5));
    CHECK(keyboard.stable[7] == 0);
    CHECK(keyboard.stable[5] == (1u << 7));

    raw[8] = 0;
    raw[7] = 1u << 4; /* Ambiguity gone: accept S and release A. */
    settle(&keyboard, raw, 20, false);
    CHECK(keyboard.stable[8] == 0);
    CHECK(keyboard.stable[7] == (1u << 4));

    memset(&keyboard, 0, sizeof(keyboard));
    raw[8] = raw[7] = (1u << 4) | (1u << 5);
    settle(&keyboard, raw, 30, false);
    CHECK(keyboard.stable[8] == 0 && keyboard.stable[7] == 0);
    settle(&keyboard, raw, 40, true); /* Diodes make all four corners real. */
    CHECK(keyboard.stable[8] == raw[8] && keyboard.stable[7] == raw[7]);
}

static void test_pending_press_becomes_ambiguous(void) {
    keyboard_t keyboard = {0};
    matrix_row_t raw[MATRIX_ROWS] = {0};
    raw[8] = 1u << 5;
    keyboard_update(&keyboard, raw, 0, false);
    raw[8] |= 1u << 4;
    raw[7] = raw[8];
    settle(&keyboard, raw, 3, false);
    CHECK(keyboard.stable[8] == 0 && keyboard.stable[7] == 0);
    raw[7] = 0;
    raw[8] = 1u << 5;
    keyboard_update(&keyboard, raw, 10, false);
    keyboard_update(&keyboard, raw, 14, false);
    CHECK(keyboard.stable[8] == 0);
    keyboard_update(&keyboard, raw, 15, false);
    CHECK(keyboard.stable[8] == (1u << 5));
}

static void test_mapping_and_rollover(void) {
    keyboard_t keyboard = {0};
    keyboard_report_t report;
    keyboard.stable[2] = (1u << 5) | (1u << 7); /* Shift + Ctrl */
    keyboard.stable[1] = 1u << 1; /* COPY -> Alt */
    keyboard.stable[8] = 1u << 5; /* A */
    keyboard.stable[9] = 1u << 8; /* Dedicated DEL column */
    keyboard.stable[0] = 1u << 6; /* Keypad Enter */
    keyboard_report(&keyboard, &report);
    CHECK(report.modifiers == 7);
    CHECK(contains(&report, KEY_A));
    CHECK(contains(&report, KEY_BACKSPACE));
    CHECK(contains(&report, KEY_KP_ENTER));
    CHECK(report.reserved == 0);

    memset(&keyboard, 0, sizeof(keyboard));
    keyboard.stable[9] = 1u << 7; /* Logical bit 7 is NOT physical X9. */
    keyboard_report(&keyboard, &report);
    CHECK(report.keys[0] == KEY_NONE);
    keyboard.stable[9] = 0;
    keyboard.stable[6] = 0x3f; /* Six non-modifier keys. */
    keyboard_report(&keyboard, &report);
    CHECK(report.keys[5] != KEY_NONE && report.keys[0] != KEY_ROLLOVER);
    keyboard.stable[2] = 1u << 5;
    keyboard.stable[6] = 0x7f; /* Seven -> ErrorRollOver in every slot. */
    keyboard_report(&keyboard, &report);
    CHECK(report.modifiers == 2);
    for (unsigned i = 0; i < KEYBOARD_REPORT_KEYS; ++i) CHECK(report.keys[i] == KEY_ROLLOVER);
    keyboard.stable[6] = 0x3f;
    keyboard_report(&keyboard, &report);
    CHECK(report.keys[0] != KEY_ROLLOVER);
}

int main(void) {
    test_debounce();
    test_independent_keys_and_wrap();
    test_ghost_suppression();
    test_pending_press_becomes_ambiguous();
    test_mapping_and_rollover();
    puts("Keyboard tests passed");
    return 0;
}
