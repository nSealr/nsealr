// SPDX-License-Identifier: MIT
#include "frame_pixels.h"
bool p4_frame_gray180(const uint8_t *rgb,size_t length,uint32_t width,uint32_t height,uint8_t *gray,size_t capacity) {
    if(!rgb || !gray || width!=800 || height!=800 || length!=1280000 || capacity!=640000)return false;
    for(size_t i=0;i<640000;i++) {
        size_t at=(639999-i)*2;uint16_t p=(uint16_t)rgb[at]|((uint16_t)rgb[at+1]<<8);
        unsigned red=((p>>11)&31)*255/31,green=((p>>5)&63)*255/63,blue=(p&31)*255/31;
        gray[i]=(uint8_t)((77*red+150*green+29*blue)>>8);
    }
    return true;
}
