#include <string.h>
#include "pico/stdlib.h"
#include "tusb.h"
#include "board_config.h"
#include "matrix.h"

static keyboard_report_t current_report;
static keyboard_report_t last_report;
static bool sent_report;
static uint8_t idle_rate; /* HID units: 4 ms, zero means changes only. */
static uint32_t last_report_ms;
static uint8_t host_leds;

void tud_mount_cb(void) {
    sent_report = false;
    idle_rate = 0;
}

void tud_umount_cb(void) {
    sent_report = false;
    host_leds = 0;
}

void tud_resume_cb(void) {
    sent_report = false;
}

bool tud_hid_set_idle_cb(uint8_t instance, uint8_t rate) {
    (void)instance;
    idle_rate = rate;
    return true;
}

uint16_t tud_hid_get_report_cb(uint8_t instance, uint8_t report_id,
                              hid_report_type_t type, uint8_t *buffer, uint16_t length) {
    if (instance != 0 || report_id != 0) return 0;
    if (type == HID_REPORT_TYPE_OUTPUT) {
        if (length == 0) return 0;
        buffer[0] = host_leds;
        return 1;
    }
    if (type != HID_REPORT_TYPE_INPUT) return 0;
    if (length > sizeof(current_report)) length = sizeof(current_report);
    memcpy(buffer, &current_report, length);
    return length;
}

void tud_hid_set_report_cb(uint8_t instance, uint8_t report_id,
                          hid_report_type_t type, const uint8_t *buffer, uint16_t length) {
    if (instance == 0 && report_id == 0 && type == HID_REPORT_TYPE_OUTPUT && length) {
        host_leds = buffer[0]; /* Reserved for lock LEDs on the interface board. */
    }
}

int main(void) {
    matrix_init();
    tusb_init();
    keyboard_t keyboard = {0};
    uint32_t last_scan_us = time_us_32();

    while (true) {
        tud_task();
        uint32_t now_us = time_us_32();
        uint32_t now_ms = to_ms_since_boot(get_absolute_time());
        if ((uint32_t)(now_us - last_scan_us) >= MATRIX_SCAN_INTERVAL_US) {
            last_scan_us = now_us;
            matrix_row_t raw[MATRIX_ROWS];
            matrix_scan(raw);
            keyboard_update(&keyboard, raw, now_ms, GOODJOHN_MATRIX_HAS_DIODES);
            keyboard_report(&keyboard, &current_report);
        }
        bool changed = !sent_report || memcmp(&last_report, &current_report, sizeof(last_report)) != 0;
        bool idle_due = idle_rate && (uint32_t)(now_ms - last_report_ms) >= (uint32_t)idle_rate * 4u;
        if (tud_hid_ready() && (changed || idle_due)) {
            if (tud_hid_keyboard_report(0, current_report.modifiers, current_report.keys)) {
                last_report = current_report;
                last_report_ms = now_ms;
                sent_report = true;
            }
        }
    }
}
