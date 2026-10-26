// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
#include <stdbool.h>
#define ESP_OK 0
#define GPIO_MODE_INPUT_OUTPUT 3
#define GPIO_PULLUP_DISABLE 0
#define GPIO_PULLDOWN_DISABLE 0
#define GPIO_INTR_DISABLE 0
typedef struct {uint64_t pin_bit_mask;int mode,pull_up_en,pull_down_en,intr_type;} gpio_config_t;
typedef struct {
    bool ie,oe,oe_ctrl_by_periph,oe_inv,od,pu,pd;
    uint32_t fun_sel,sig_out;
} gpio_io_config_t;
int gpio_set_level(int pin,uint32_t value);
int gpio_config(const gpio_config_t *config);
int gpio_get_io_config(int pin,gpio_io_config_t *config);
int gpio_get_level(int pin);
