// SPDX-License-Identifier: MIT
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "local_input.h"
#include "frame_pixels.h"
static void ready(p4_button_t *b) {p4_button_begin(b,false,0);assert(p4_button_poll(b,false,40,true)==0);}
static void down(p4_button_t *b) {assert(p4_button_poll(b,true,100,true)==0);assert(p4_button_poll(b,true,140,true)==0);}
int main(void) {
 p4_button_t b;
 ready(&b);down(&b);assert(p4_button_poll(&b,false,400,true)==0);assert(p4_button_poll(&b,false,440,true)==4); // tap rejects
 ready(&b);down(&b);assert(p4_button_poll(&b,false,1600,true)==0);assert(p4_button_poll(&b,false,1640,true)==3); //1500ms committed hold
 assert(p4_button_poll(&b,false,2000,true)==0); // one action only
 ready(&b);down(&b);assert(p4_button_poll(&b,true,5141,true)==4); // too long rejects without signature
 ready(&b);down(&b);assert(p4_button_poll(&b,false,1600,false)==0);assert(p4_button_poll(&b,false,1640,false)==4); // data cannot approve
 p4_button_begin(&b,true,0);assert(p4_button_poll(&b,true,4000,true)==0);assert(p4_button_poll(&b,false,4100,true)==0);assert(p4_button_poll(&b,false,4140,true)==0); // pre-held release ignored
 assert(b.state==1);assert(p4_button_poll(&b,false,5000,true)==0);
 ready(&b);down(&b);p4_button_begin(&b,true,1000);assert(p4_button_poll(&b,false,4000,true)==0);assert(p4_button_poll(&b,false,4040,true)==0); // frame/reset crossing cannot approve or reject
 ready(&b);assert(p4_button_poll(&b,true,100,true)==0);assert(p4_button_poll(&b,false,110,true)==0);assert(p4_button_poll(&b,false,150,true)==0); // bounce never arms a press
 assert(p4_button_poll(&b,false,149,true)==-1); // rolled-back clock
 uint8_t *rgb=calloc(1280000,1),*gray=malloc(640000);assert(rgb&&gray);
 rgb[0]=0;rgb[1]=0xf8; // input origin red -> rotated opposite corner
 rgb[1279998]=0xff;rgb[1279999]=0xff; // bottom-right white ->output origin
 assert(p4_frame_gray180(rgb,1280000,800,800,gray,640000));assert(gray[0]==255);assert(gray[639999]==76);
 assert(!p4_frame_gray180(rgb,1279999,800,800,gray,640000));assert(!p4_frame_gray180(rgb,1280000,801,800,gray,640000));assert(!p4_frame_gray180(rgb,1280000,800,800,gray,639999));
 free(rgb);free(gray);puts("GPIO freshness/debounce/hold/frame-reset/clock and RGB565 bounds/orientation PASS");
}
