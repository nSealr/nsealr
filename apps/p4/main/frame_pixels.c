// SPDX-License-Identifier: MIT
#include "frame_pixels.h"
bool p4_frame_gray_raw(const uint8_t *rgb,size_t length,uint32_t width,uint32_t height,uint8_t *gray,size_t capacity) {
    if(!rgb || !gray || width!=800 || height!=800 || length!=1280000 || capacity!=640000)return false;
    // Preserve acquisition coordinates. This is not a claim about optical parity.
    for(size_t i=0;i<640000;i++) {
        size_t at=i*2;uint16_t p=(uint16_t)rgb[at]|((uint16_t)rgb[at+1]<<8);
        unsigned red=((p>>11)&31)*255/31,green=((p>>5)&63)*255/63,blue=(p&31)*255/31;
        gray[i]=(uint8_t)((77*red+150*green+29*blue)>>8);
    }
    return true;
}
bool p4_gray_preview(const uint8_t *gray,size_t length,uint16_t *out,size_t pixels) {
    if(!gray || !out || length!=640000 || pixels!=153600)return false;
    // Same crop/scale geometry as measured peripheral2aaf; nearest CPU sample,
    // not a claim of bit-identical PPA filtering. No rotation or reflection.
    for(size_t y=0;y<480;y++) for(size_t x=0;x<320;x++) {
        unsigned g=gray[(16+y*8/5)*800+144+x*8/5];
        out[y*320+x]=(uint16_t)(((g>>3)<<11)|((g>>2)<<5)|(g>>3));
    }
    return true;
}
