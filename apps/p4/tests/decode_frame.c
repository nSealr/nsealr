// SPDX-License-Identifier: MIT
#include <stdio.h>
#include <stdlib.h>
#include "quirc.h"
int main(int argc,char **argv) {
 if(argc!=2)return 2;
 FILE *f=fopen(argv[1],"rb");if(!f)return 2;
 struct quirc *q=quirc_new();if(!q || quirc_resize(q,800,800))return 3;
 uint8_t *image=quirc_begin(q,NULL,NULL);if(fread(image,1,640000,f)!=640000 || fgetc(f)!=EOF)return 4;fclose(f);
 quirc_end(q);int n=quirc_count(q);printf("detected=%d\n",n);
 if(n==1) {struct quirc_code code;struct quirc_data data;quirc_extract(q,0,&code);
  int e=quirc_decode(&code,&data);printf("grid=%d decode=%d payload_bytes=%d\n",code.size,e,e?0:data.payload_len);}
 quirc_destroy(q);return 0;
}
