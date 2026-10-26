// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <stdint.h>
#include "s3_entropy_logic.h"
void s3_entropy_bind_public_epoch(uint32_t epoch);
void s3_entropy_diagnostic_mode(bool enabled);
extern "C" int32_t nsealr_s3_public_auxiliary(uint8_t*,size_t,size_t*);
const S3EntropyReport &s3_entropy_last_report();
void s3_entropy_log_report(unsigned draw,const uint8_t *public_sample);
