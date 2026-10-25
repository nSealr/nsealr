// SPDX-License-Identifier: MIT
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include "esp_heap_caps.h"
// Allocations occur only during fixed-size decoder startup, never from QR sizes.
typedef union {max_align_t alignment;size_t bytes;} header_t;
static size_t retained;
void *p4_quirc_malloc(size_t n) {
    if(!n || n>700000 || retained>700000-n) return NULL;
    header_t *h=heap_caps_malloc(sizeof(*h)+n,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
    if(!h) return NULL;
    h->bytes=n;retained+=n;return h+1;
}
void *p4_quirc_calloc(size_t count,size_t width) {
    if(width && count>SIZE_MAX/width) return NULL;
    size_t n=count*width;void *p=p4_quirc_malloc(n);if(p)memset(p,0,n);return p;
}
void p4_quirc_free(void *p) {
    if(!p)return;
    header_t *h=(header_t *)p-1;retained-=h->bytes;heap_caps_free(h);
}
size_t p4_decoder_retained(void) {return retained;}
