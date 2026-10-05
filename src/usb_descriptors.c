#include <string.h>
#include "pico/unique_id.h"
#include "tusb.h"

static const uint8_t report_descriptor[] = {TUD_HID_REPORT_DESC_KEYBOARD()};
static const tusb_desc_device_t device_descriptor = {
    .bLength = sizeof(tusb_desc_device_t),
    .bDescriptorType = TUSB_DESC_DEVICE,
    .bcdUSB = 0x0200,
    .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor = GOODJOHN_USB_VID,
    .idProduct = GOODJOHN_USB_PID,
    .bcdDevice = 0x0100,
    .iManufacturer = 1,
    .iProduct = 2,
    .iSerialNumber = 3,
    .bNumConfigurations = 1
};

enum { CONFIG_LENGTH = TUD_CONFIG_DESC_LEN + TUD_HID_DESC_LEN };
static const uint8_t configuration_descriptor[] = {
    TUD_CONFIG_DESCRIPTOR(1, 1, 0, CONFIG_LENGTH, 0, 100),
    TUD_HID_DESCRIPTOR(0, 0, HID_ITF_PROTOCOL_KEYBOARD,
                       sizeof(report_descriptor), 0x81, 8, 1)
};

const uint8_t *tud_descriptor_device_cb(void) {
    return (const uint8_t *)&device_descriptor;
}

const uint8_t *tud_descriptor_configuration_cb(uint8_t index) {
    return index == 0 ? configuration_descriptor : NULL;
}

const uint8_t *tud_hid_descriptor_report_cb(uint8_t instance) {
    return instance == 0 ? report_descriptor : NULL;
}

const uint16_t *tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
    (void)langid;
    static uint16_t descriptor[32];
    if (index == 0) {
        descriptor[0] = (TUSB_DESC_STRING << 8) | 4;
        descriptor[1] = 0x0409;
        return descriptor;
    }

    char serial[PICO_UNIQUE_BOARD_ID_SIZE_BYTES * 2 + 1];
    const char *string;
    switch (index) {
        case 1: string = "Goodjohn"; break;
        case 2: string = "CPC USB Keyboard"; break;
        case 3:
            pico_get_unique_board_id_string(serial, sizeof(serial));
            string = serial;
            break;
        default: return NULL;
    }
    size_t length = strlen(string);
    if (length > 31) length = 31;
    for (size_t i = 0; i < length; ++i) descriptor[i + 1] = (uint8_t)string[i];
    descriptor[0] = (uint16_t)((TUSB_DESC_STRING << 8) | (2 * length + 2));
    return descriptor;
}
