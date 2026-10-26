// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
uint32_t p4_test_reg_read(uint32_t address);
void p4_test_reg_write(uint32_t address,uint32_t value);
#define REG_READ(address) p4_test_reg_read(address)
#define REG_WRITE(address,value) p4_test_reg_write(address,value)
