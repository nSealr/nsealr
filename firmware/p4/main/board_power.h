#pragma once
#include "driver/i2c_master.h"
#include <stdbool.h>
#include <stdint.h>

bool board_power_init(i2c_master_bus_handle_t bus);
unsigned board_power_state(void);
