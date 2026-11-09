#pragma once
#include <stdint.h>

enum { P4_POWER_BATTERY, P4_POWER_EXTERNAL, P4_POWER_UNKNOWN };

/* AXP2101 status1: VBUS good bit5, battery present bit3.
 * Status2 bits6:5: 0 standby, 1 charging, 2 discharging. */
static inline unsigned p4_power_classify(uint8_t chip, uint8_t status1, uint8_t status2) {
    if (chip != 0x4a)
        return P4_POWER_UNKNOWN;
    if (status1 & 0x20)
        return P4_POWER_EXTERNAL;
    if ((status1 & 0x08) && !(status1 & 0x06) && (status2 & 0xe0) == 0x40)
        return P4_POWER_BATTERY;
    return P4_POWER_UNKNOWN;
}
