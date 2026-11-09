#include "nsealr.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static _Alignas(NS_CONTEXT_ALIGN) uint8_t storage[3][NS_CONTEXT_BYTES];
static ns_context *device[3];
static char keys[3][65], roster[3][65], public_key[65];
static uint8_t group_record[64];
static char messages[6][NS_MAX_MESSAGE], input[NS_MAX_MESSAGE], frame[NS_MAX_FRAME];
static char event[NS_MAX_MESSAGE], quoted[NS_MAX_MESSAGE];
static uint8_t backup[3][NS_THRESHOLD_MAX_BACKUP], entropy[32];
static size_t backup_len[3];
static unsigned sequence=1;
static uint64_t now=1;
static uint64_t previous_generation[3];
static void fresh(void){memset(entropy,(int)sequence++,32);++now;}
static void wiped(const uint8_t *bytes,size_t len){for(size_t i=0;i<len;i++)assert(bytes[i]==0);}
static int compare(const void *a,const void *b){return strcmp(a,b);}
static void quote(const char *value){
    size_t out=0;quoted[out++]='"';
    for(const char *p=value;*p;p++){
        assert(out+4<sizeof quoted);
        if(*p=='"' || *p=='\\')quoted[out++]='\\';
        quoted[out++]=*p;
    }
    quoted[out++]='"';quoted[out]=0;
}
static void field(const char *json,const char *name,char out[65]){
    char needle[64];snprintf(needle,sizeof needle,"\"%s\":\"",name);
    const char *start=strstr(json,needle);assert(start);start+=strlen(needle);
    memcpy(out,start,64);out[64]=0;assert(start[64]=='"');
}
static void approve(int index){
    uint64_t generation=ns_review_generation(device[index]);
    ns_text label;assert(ns_review_confirmation(device[index],&label)==0 && label.len>0);
    for(uint32_t i=0;i<ns_review_count(device[index]);i++)assert(ns_review_seen(device[index],generation,i)==0);
    fresh();assert(ns_approve(device[index],generation,false,entropy,32,now)==0);wiped(entropy,32);
}
static unsigned outputs(void){
    unsigned total=0;
    for(int i=0;i<3;i++){
        unsigned count=ns_threshold_output_count(device[i]);
        for(unsigned k=0;k<count;k++){
            ns_text output;assert(total<6);assert(ns_threshold_output(device[i],k,&output)==0);
            assert(output.len<sizeof messages[0]);memcpy(messages[total],output.data,output.len);messages[total++][output.len]=0;
        }
        ns_finish_response(device[i]);
    }
    return total;
}
static void route(unsigned count){
    for(unsigned k=0;k<count;k++){
        char recipient[65];field(messages[k],"recipient",recipient);
        int index=0;while(index<3 && strcmp(recipient,keys[index]))index++;assert(index<3);
        size_t len=strlen(messages[k]);
        for(size_t j=0;j<(len+NS_QR_CHUNK-1)/NS_QR_CHUNK;j++){
            size_t written;assert(ns_encode_frame((const uint8_t*)messages[k],len,(uint32_t)j,(uint8_t*)frame,sizeof frame,&written)==0);
            fresh();int result=ns_threshold_receive_frame(device[index],(const uint8_t*)frame,written,entropy,now);wiped(entropy,32);
            assert(result==(j+1==(len+NS_QR_CHUNK-1)/NS_QR_CHUNK?NS_OK:NS_MORE));
        }
    }
}
int main(void){
    for(int i=0;i<3;i++){
        device[i]=(ns_context*)storage[i];assert(ns_init(storage[i],sizeof storage[i])==0);
        fresh();assert(ns_generate(device[i],0,entropy,NULL,0,0)==0);wiped(entropy,32);
        const char *normal="{\"id\":\"normal\",\"method\":\"get_public_key\",\"params\":[]}";
        assert(ns_request(device[i],(const uint8_t*)normal,strlen(normal),now)==0);
        previous_generation[i]=ns_review_generation(device[i]);
        fresh();assert(ns_threshold_start(device[i],entropy,now)==0);wiped(entropy,32);
        ns_text output;assert(ns_threshold_output(device[i],0,&output)==0);
        memcpy(input,output.data,output.len);input[output.len]=0;field(input,"key",keys[i]);strcpy(roster[i],keys[i]);
        ns_finish_response(device[i]);
    }
    qsort(roster,3,sizeof roster[0],compare);
    snprintf(input,sizeof input,"{\"type\":\"nsealr_setup\",\"session\":\"%064d\",\"members\":[\"%s\",\"%s\",\"%s\"]}",1,roster[0],roster[1],roster[2]);
    for(int i=0;i<3;i++){
        fresh();assert(ns_threshold_receive(device[i],(const uint8_t*)input,strlen(input),entropy,now)==0);wiped(entropy,32);
        assert(ns_threshold_state(device[i])==NS_THRESHOLD_REVIEW);
        assert(ns_review_generation(device[i])!=previous_generation[i]);
        assert(ns_review_seen(device[i],previous_generation[i],0)<0);
        approve(i);
    }
    assert(outputs()==6);route(6);assert(outputs()==6);route(6);
    for(int i=0;i<3;i++){
        uint8_t key[64];size_t written;
        assert(ns_is_loaded(device[i]));assert(ns_threshold_state(device[i])==NS_THRESHOLD_READY);
        uint8_t record[1024];
        assert(ns_threshold_record(device[i],record,sizeof record,&written)==0 && written>0);
        ns_text ready;assert(ns_threshold_output(device[i],0,&ready)==0);
        assert(ready.len==written && memcmp(ready.data,record,written)==0);
        assert(ns_threshold_record(device[i],record,1,&written)<0 && written==0 && record[0]==0);
        assert(ns_threshold_state(device[i])==NS_THRESHOLD_READY);
        assert(ns_word_count(device[i])==0);
        assert(ns_backup(device[i],1,backup[i],sizeof backup[i],&written)<0 && written==0);
        wiped(backup[i],sizeof backup[i]);
        assert(ns_public_key(device[i],0,key,sizeof key,&written)==0 && written==64);
        if(i==0){memcpy(public_key,key,64);public_key[64]=0;}else{assert(memcmp(public_key,key,64)==0);}
        assert(ns_threshold_backup(device[i],backup[i],sizeof backup[i],&backup_len[i])==0);
        assert(backup_len[i]<NS_THRESHOLD_MAX_BACKUP);
        uint8_t fingerprint[64];uint32_t member;
        assert(ns_threshold_info(device[i],fingerprint,&member)==0 && member>=1 && member<=3);
        if(i==0)memcpy(group_record,fingerprint,64);else assert(memcmp(group_record,fingerprint,64)==0);
        for(size_t j=0;j<(backup_len[i]+NS_QR_CHUNK-1)/NS_QR_CHUNK;j++){
            size_t len;assert(ns_encode_frame(backup[i],backup_len[i],(uint32_t)j,(uint8_t*)frame,sizeof frame,&len)==0);
            ++now;int result=ns_threshold_check_backup_frame(device[i],(uint8_t*)frame,len,now);wiped((uint8_t*)frame,sizeof frame);
            assert(result==(j+1==(backup_len[i]+NS_QR_CHUNK-1)/NS_QR_CHUNK?NS_OK:NS_MORE));
        }
        assert(ns_is_loaded(device[i]));
        ns_lock(device[i]);assert(!ns_is_loaded(device[i]));
        for(size_t j=0;j<(backup_len[i]+NS_QR_CHUNK-1)/NS_QR_CHUNK;j++){
            size_t len;assert(ns_encode_frame(backup[i],backup_len[i],(uint32_t)j,(uint8_t*)frame,sizeof frame,&len)==0);
            ++now;int result=ns_threshold_import_frame(device[i],(uint8_t*)frame,len,now);wiped((uint8_t*)frame,sizeof frame);
            assert(result==(j+1==(backup_len[i]+NS_QR_CHUNK-1)/NS_QR_CHUNK?NS_OK:NS_MORE));
        }
        memset(backup[i],0,sizeof backup[i]);
        assert(!ns_is_loaded(device[i]));approve(i);assert(ns_is_loaded(device[i]));
    }
    outputs();
    /* Lose member0 entirely: the surviving quorum repairs a new transport owner. */
    uint8_t record[1024];size_t record_len;uint32_t lost_member;
    assert(ns_threshold_record(device[1],record,sizeof record-1,&record_len)==0);
    record[record_len]=0;
    char descriptor[461];const char *descriptor_start=strstr((const char*)record,"\"descriptor\":\"");
    assert(descriptor_start);descriptor_start+=14;
    memcpy(descriptor,descriptor_start,460);descriptor[460]=0;assert(descriptor_start[460]=='"');
    assert(ns_threshold_info(device[0],group_record,&lost_member)==0);
    fresh();assert(ns_threshold_start(device[0],entropy,now)==0);wiped(entropy,32);
    ns_text join;assert(ns_threshold_output(device[0],0,&join)==0);
    memcpy(input,join.data,join.len);input[join.len]=0;field(input,"key",keys[0]);
    ns_finish_response(device[0]);
    snprintf(input,sizeof input,"{\"type\":\"nsealr_repair\",\"session\":\"%064d\",\"group\":\"%.*s\",\"descriptor\":\"%s\",\"members\":[{\"id\":1,\"key\":\"%s\"},{\"id\":2,\"key\":\"%s\"},{\"id\":3,\"key\":\"%s\"}],\"participant\":%u,\"replacement\":\"%s\"}",3,64,group_record,descriptor,roster[0],roster[1],roster[2],lost_member,keys[0]);
    for(int i=0;i<3;i++){
        fresh();assert(ns_threshold_receive(device[i],(const uint8_t*)input,strlen(input),entropy,now)==0);approve(i);
    }
    assert(outputs()==2);route(2);assert(outputs()==2);route(2);
    assert(outputs()==3);route(2);assert(outputs()==2);
    for(int i=0;i<3;i++){
        uint8_t key[64],fingerprint[64];size_t written;uint32_t member;
        assert(ns_threshold_state(device[i])==NS_THRESHOLD_READY);
        assert(ns_public_key(device[i],0,key,sizeof key,&written)==0 && written==64);
        assert(memcmp(public_key,key,64)==0);
        assert(ns_threshold_info(device[i],fingerprint,&member)==0);
        if(i==0){assert(member==lost_member);memcpy(group_record,fingerprint,64);}
        else assert(memcmp(group_record,fingerprint,64)==0);
    }
    char selected[2][65];strcpy(selected[0],keys[0]);strcpy(selected[1],keys[1]);
    qsort(selected,2,sizeof selected[0],compare);
    size_t offset=(size_t)snprintf(event,sizeof event,"{\"pubkey\":\"%s\",\"created_at\":1,\"kind\":1,\"tags\":[",public_key);
    for(unsigned i=0;i<256;i++)offset+=(size_t)snprintf(event+offset,sizeof event-offset,"%s[\"t\",\"example\"]",i?",":"");
    offset+=(size_t)snprintf(event+offset,sizeof event-offset,"],\"content\":\"Native custody signing");
    size_t remainder=NS_MAX_CONTENT-strlen("Native custody signing");memset(event+offset,'x',remainder);offset+=remainder;
    offset+=(size_t)snprintf(event+offset,sizeof event-offset,"\"}");assert(offset<sizeof event);quote(event);
    int n=snprintf(input,sizeof input,"{\"type\":\"nsealr_sign\",\"id\":\"native-threshold\",\"session\":\"%064d\",\"members\":[\"%s\",\"%s\"],\"event\":%s}",2,selected[0],selected[1],quoted);
    assert(n>0 && (size_t)n<sizeof input);
    for(int i=0;i<2;i++){
        fresh();assert(ns_threshold_receive(device[i],(const uint8_t*)input,strlen(input),entropy,now)==0);approve(i);
    }
    assert(outputs()==2);route(2);assert(outputs()==2);route(2);assert(outputs()==2);
    assert(strcmp(messages[0],messages[1])==0);assert(strstr(messages[0],"native-threshold"));assert(strstr(messages[0],"Native custody signing"));
    now+=300000;assert(ns_tick(device[0],now)==1);assert(ns_is_loaded(device[0]));
    for(int i=0;i<3;i++){ns_lock(device[i]);ns_deinit(device[i]);wiped(storage[i],sizeof storage[i]);}
    printf("PASS C ABI setup, backup restore, quorum repair, 2-party sign, animated QR; backup=%zu heap peak=%zu live=%zu\n",backup_len[0],ns_heap_peak(),ns_heap_reserved());
    assert(ns_heap_reserved()==0);return 0;
}
