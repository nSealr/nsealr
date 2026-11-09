#include "board_power.h"
#include "power_status.h"

static i2c_master_dev_handle_t pmic;

bool board_power_init(i2c_master_bus_handle_t bus) {
    if (!bus || pmic)
        return false;
    const i2c_device_config_t config = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7, .device_address = 0x34, .scl_speed_hz = 400000};
    return i2c_master_bus_add_device(bus, &config, &pmic) == ESP_OK;
}

unsigned board_power_state(void) {
    uint8_t status[4] = {0};
    const uint8_t address = 0;
    /* Read-only, with no cached permission after a failed or missing read. */
    if (!pmic ||
        i2c_master_transmit_receive(pmic, &address, 1, status, sizeof(status), 20) != ESP_OK)
        return P4_POWER_UNKNOWN;
    return p4_power_classify(status[3], status[0], status[1]);
}
