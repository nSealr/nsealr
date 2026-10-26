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
 // Four unequal corners plus an off-axis marker distinguish all eight
 // square transforms. Expectations derive from source coordinates, never LCD.
 rgb[0]=0;rgb[1]=0xf8; // origin red ->76
 rgb[1598]=0xe0;rgb[1599]=0x07; // top right green ->149
 rgb[1278400]=0x1f;rgb[1278401]=0; // bottom left blue ->28
 rgb[1279998]=0xff;rgb[1279999]=0xff; // bottom right white ->255
 rgb[(123*800+456)*2]=0xff;rgb[(123*800+456)*2+1]=0xff;
 assert(p4_frame_gray_raw(rgb,1280000,800,800,gray,640000));
 assert(gray[0]==76 && gray[799]==149 && gray[639200]==28 && gray[639999]==255);
 assert(gray[123*800+456]==255 && gray[456*800+123]==0);
 assert(!p4_frame_gray_raw(rgb,1279999,800,800,gray,640000));assert(!p4_frame_gray_raw(rgb,1280000,801,800,gray,640000));assert(!p4_frame_gray_raw(rgb,1280000,800,800,gray,639999));
 uint16_t *preview=malloc(307200);assert(preview);
 for(size_t i=0;i<640000;i++)gray[i]=(uint8_t)((i/800*13+i%800*7)%256);
 assert(p4_gray_preview(gray,640000,preview,153600));
 for(size_t y=0;y<480;y++)for(size_t x=0;x<320;x++) {
  unsigned g=gray[(16+y*8/5)*800+144+x*8/5];
  assert(preview[y*320+x]==(uint16_t)(((g>>3)<<11)|((g>>2)<<5)|(g>>3)));
 }
 assert(!p4_gray_preview(gray,639999,preview,153600));assert(!p4_gray_preview(gray,640000,preview,153599));free(preview);
 free(rgb);free(gray);puts("GPIO freshness/debounce/hold/frame-reset/clock and RGB565 raw coordinates/asymmetric gray/crop bounds PASS");
}
