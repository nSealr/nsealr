// SPDX-License-Identifier: MIT
#pragma once
void p4_test_log(const char *tag,const char *format,...);
#define ESP_LOGI(tag,...) p4_test_log(tag,__VA_ARGS__)
#define ESP_LOGE(tag,...) p4_test_log(tag,__VA_ARGS__)
