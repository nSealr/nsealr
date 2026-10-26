// SPDX-License-Identifier: MIT
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
extern int p4_engine_init(void);
extern int p4_engine_run(const uint8_t *,size_t,uint8_t *,size_t);
static const char *mode;
static unsigned presented, auxiliary;
static int64_t offset;
int64_t p4_monotonic_ms(void) {
 struct timespec now;assert(clock_gettime(CLOCK_MONOTONIC,&now)==0);
 return now.tv_sec*1000+now.tv_nsec/1000000+offset;
}
int p4_memory_internal(const uint8_t *p,size_t n) {(void)p;(void)n;return 1;} // synthetic only; no physical memory claim
_Noreturn void p4_fatal(void) {abort();}
// Host sysroot EH metadata references this even with abort; target ELF does not.
_Noreturn void rust_eh_personality(void) {abort();}
#ifndef P4_MISSING_PROVIDER
ptrdiff_t p4_entropy_fill32(uint8_t *out,size_t n) {
 assert(n==32);auxiliary++;memset(out,0x22,32);
 if(!strcmp(mode,"aux-short"))return 31;
 if(!strcmp(mode,"aux-error"))return -1;
 if(!strcmp(mode,"aux-zero"))return 0;
 if(!strcmp(mode,"aux-over"))return 33;
 return 32;
}
#endif
int p4_present(uint32_t decision,const uint8_t *label,size_t label_len,const uint8_t *body,size_t body_len,
 const uint8_t *position,size_t position_len,size_t index,size_t total,uint64_t deadline) {
 (void)label;(void)body;(void)position;(void)index;(void)deadline;
 assert(label_len<=176&&body_len<=264&&position_len<=9&&total<=64);presented++;
 if(!strcmp(mode,"expire"))offset+=101000;
 if(!strcmp(mode,"display-error"))return -1;
 if(!strcmp(mode,"reject"))return 4;
 if(!strcmp(mode,"approve-data"))return 3;
 return decision?3:1;
}
int main(int argc,char **argv) {
 assert(argc==4);mode=argv[1];FILE *f=fopen(argv[2],"rb");assert(f);
 uint8_t input[948],output[1536];size_t n=fread(input,1,sizeof(input),f);assert(n<sizeof(input) || fgetc(f)==EOF);fclose(f);
 assert(p4_engine_init()==0);memset(output,0xa5,sizeof(output));
 int result=p4_engine_run(input,n,output,sizeof(output));
 if(!strcmp(mode,"positive")) {
  assert(result>0&&presented>2&&auxiliary==1);FILE *out=fopen(argv[3],"wb");assert(out);assert(fwrite(output,1,(size_t)result,out)==(size_t)result);fclose(out);
  unsigned seen=presented;int replay=p4_engine_run(input,n,output,sizeof(output));assert(replay==-6&&presented==seen&&auxiliary==1);
  for(size_t i=0;i<sizeof(output);i++)assert(output[i]==0);
 } else {
  assert(result<0);
  assert(auxiliary==((!strcmp(mode,"aux-short")||!strcmp(mode,"aux-error")||!strcmp(mode,"aux-zero")||!strcmp(mode,"aux-over"))?1:0));
  if(auxiliary)assert(presented>2);
  for(size_t i=0;i<sizeof(output);i++)assert(output[i]==0);
 }
 printf("mode=%s result=%d synthetic_presentations=%u output_policy=PASS\n",mode,result,presented);
}
