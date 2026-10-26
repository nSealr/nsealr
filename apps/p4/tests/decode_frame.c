// SPDX-License-Identifier: MIT
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "decode_one.h"
static double seconds(void) {struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))abort();return t.tv_sec+t.tv_nsec/1e9;}
int main(int argc,char **argv) {
 if(argc<2 || argc>3)return 2;
 FILE *f=fopen(argv[1],"rb");if(!f)return 2;
 struct quirc *q=quirc_new();if(!q || quirc_resize(q,800,800))return 3;
 uint8_t *image=quirc_begin(q,NULL,NULL);if(fread(image,1,640000,f)!=640000 || fgetc(f)!=EOF)return 4;fclose(f);
 double start=seconds();quirc_end(q);int n=quirc_count(q);printf("detected=%d\n",n);
 if(n==1) {struct quirc_code code;struct quirc_data data;quirc_extract(q,0,&code);
  int first=quirc_decode(&code,&data);unsigned attempts=0;
  int e=p4_decode_one(&code,&data,&attempts);
  printf("grid=%d initial_decode=%d bounded_result=%d attempts=%u payload_bytes=%d elapsed_ms=%.3f\n",code.size,first,e,attempts,e?0:data.payload_len,(seconds()-start)*1000);
  if(argc==3 && e==0) {FILE *out=fopen(argv[2],"wb");if(!out || fwrite(data.payload,1,(size_t)data.payload_len,out)!=(size_t)data.payload_len)return 5;fclose(out);}
 }
 struct quirc_code too_big={.size=118};struct quirc_data clean;unsigned attempts=99;
 memset(&clean,0xff,sizeof(clean));if(p4_decode_one(&too_big,&clean,&attempts)!=-1 || attempts)return 6;
 const unsigned char *bytes=(const unsigned char *)&clean;for(size_t i=0;i<sizeof(clean);i++)if(bytes[i])return 7;
 quirc_destroy(q);return 0;
}
