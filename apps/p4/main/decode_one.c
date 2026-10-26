// SPDX-License-Identifier: MIT
#include "decode_one.h"
#include <string.h>
int p4_decode_one(struct quirc_code *code,struct quirc_data *data,unsigned *attempts) {
    if(!code || !data || !attempts)return -1;
    *attempts=0;memset(data,0,sizeof(*data));
    if(code->size<21 || code->size>117)return -1;
    *attempts=1;quirc_decode_error_t result=quirc_decode(code,data);
    // Exactly the upstream README mirrored-QR recipe: one ECC-only fallback,
    // transpose extracted public modules, not another image pass or engine.
    if(result==QUIRC_ERROR_DATA_ECC) {
        quirc_flip(code);*attempts=2;result=quirc_decode(code,data);
    }
    if(result!=QUIRC_SUCCESS || data->payload_len<8 || data->payload_len>947 ||
       memcmp(data->payload,"nsealr1:",8)!=0) {memset(data,0,sizeof(*data));return -1;}
    return 0;
}
