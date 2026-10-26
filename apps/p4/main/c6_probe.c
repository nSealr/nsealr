// SPDX-License-Identifier: MIT
#include "c6_probe.h"
#include "p4_local.h"
#include "worker_watchdog.h"
#include "esp_log.h"
#include "esp_system.h"
#include "driver/gpio.h"
#include "driver/sdmmc_host.h"
#include "sdmmc_cmd.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>
#include <string.h>
#include <stdatomic.h>
#if P4_WDT_PROBE_MODE == 3
static sdmmc_host_t host;
static sdmmc_card_t card;
static uint8_t scratch[512] __attribute__((aligned(64)));
static uint64_t deadline;
static bool host_up,slot_up;
static atomic_bool low_admitted;
static int raw_io_error;
static bool time_ok(void) {int64_t t=p4_monotonic_ms();return t>=0 && (uint64_t)t<deadline;}
static int prepare(void) {
    gpio_config_t cfg={.pin_bit_mask=1ULL<<54,.mode=GPIO_MODE_INPUT,
        .pull_up_en=GPIO_PULLUP_DISABLE,.pull_down_en=GPIO_PULLDOWN_DISABLE,.intr_type=GPIO_INTR_DISABLE};
    // No output-latch write or low/release before a baseline is accepted.
    esp_err_t e=gpio_config(&cfg);if(e!=ESP_OK)return e;
    host=(sdmmc_host_t)SDMMC_HOST_DEFAULT();host.slot=1;host.max_freq_khz=400;
    host.command_timeout_ms=100;host.flags=SDMMC_HOST_FLAG_4BIT|SDMMC_HOST_FLAG_1BIT|SDMMC_HOST_FLAG_DEINIT_ARG;
    host.unaligned_multi_block_rw_max_chunk_size=1;host.dma_aligned_buffer=scratch;
    e=sdmmc_host_init();if(e!=ESP_OK)return e;host_up=true;
    sdmmc_slot_config_t slot=SDMMC_SLOT_CONFIG_DEFAULT();
    slot.width=4;slot.clk=18;slot.cmd=19;slot.d0=14;slot.d1=15;slot.d2=16;slot.d3=17;
    slot.gpio_cd=GPIO_NUM_NC;slot.gpio_wp=GPIO_NUM_NC;slot.flags=0;
    e=sdmmc_host_init_slot(1,&slot);if(e==ESP_OK)slot_up=true;return e;
}
static int pad(p4_c6_pad_t *p) {
    gpio_io_config_t c;esp_err_t e=gpio_get_io_config(54,&c);if(e!=ESP_OK) {p->level=-1;return e;}
    *p=(p4_c6_pad_t){.level=c.ie?gpio_get_level(54):-1,.input=c.ie,.output=c.oe,
        .function=c.fun_sel,.signal=c.sig_out};return 0;
}
static int low(void) {
    atomic_store(&low_admitted,true);
    esp_err_t e=gpio_set_level(54,0);if(e!=ESP_OK)return e;
    gpio_config_t cfg={.pin_bit_mask=1ULL<<54,.mode=GPIO_MODE_INPUT_OUTPUT,
        .pull_up_en=GPIO_PULLUP_DISABLE,.pull_down_en=GPIO_PULLDOWN_DISABLE,.intr_type=GPIO_INTR_DISABLE};
    return gpio_config(&cfg);
}
static int release(void) {return gpio_set_direction(54,GPIO_MODE_INPUT);}
static int read_byte(uint32_t addr,uint8_t *value) {
    if(!time_ok())return ESP_ERR_TIMEOUT;
    raw_io_error=sdmmc_io_read_byte(&card,0,addr,value);
    if(!time_ok())return ESP_ERR_TIMEOUT;
    return raw_io_error;
}
static int identity(p4_c6_identity_t *id) {
    if(!time_ok())return ESP_ERR_TIMEOUT;
    raw_io_error=sdmmc_card_init(&host,&card);
    if(raw_io_error!=ESP_OK)return raw_io_error;
    if(!time_ok())return ESP_ERR_TIMEOUT;
    if(!card.is_sdio || card.is_mem || card.num_io_functions<1)return ESP_ERR_INVALID_RESPONSE;
    ESP_LOGI("p4_c6","PUBLIC SDIO IO-only=%d funcs=%u real_freq_khz=%d width_log2=%u",!card.is_mem,card.num_io_functions,card.real_freq_khz,card.log_bus_width);
    memset(id,0,sizeof(*id));id->functions=(uint8_t)card.num_io_functions;
    int e=read_byte(0,&id->cccr);if(e)return e;
    uint32_t address=0;
    for(unsigned i=0;i<3;i++) {uint8_t b=0;e=read_byte(9+i,&b);if(e)return e;address|=(uint32_t)b<<(8*i);}
    if(address<0x1000 || address>0x18000-P4_C6_CIS_MAX)return ESP_ERR_INVALID_RESPONSE;
    uint8_t cis[P4_C6_CIS_MAX];memset(cis,0,sizeof(cis));
    // Read a bounded common CIS; stop only at tuple boundaries, not data0xff.
    size_t used=0;unsigned tuples=0;
    while(used<sizeof(cis) && tuples++<64) {
        e=read_byte(address+(uint32_t)used,&cis[used]);if(e)return e;
        uint8_t code=cis[used++];if(code==0xff)break;if(code==0)continue;
        if(used>=sizeof(cis))return ESP_ERR_INVALID_SIZE;
        e=read_byte(address+(uint32_t)used,&cis[used]);if(e)return e;
        size_t len=cis[used++];if(len>sizeof(cis)-used)return ESP_ERR_INVALID_SIZE;
        for(size_t i=0;i<len;i++) {e=read_byte(address+(uint32_t)used,&cis[used]);if(e)return e;used++;}
    }
    return p4_c6_parse_cis(cis,used,id)?ESP_OK:ESP_ERR_NOT_SUPPORTED;
}
static p4_c6_reply_t read_link(void) {
    if(!time_ok())return P4_C6_OTHER_ERROR;
    uint8_t value=0;raw_io_error=sdmmc_io_read_byte(&card,0,0,&value);
    return raw_io_error==ESP_OK?P4_C6_VALID:raw_io_error==ESP_ERR_TIMEOUT?P4_C6_TIMED_OUT:P4_C6_OTHER_ERROR;
}
static void wait_cooperative(uint32_t ms) {
    // IO call is already collected. Real waiting never modifies the core clock.
    if(ms<=10) {vTaskDelay(pdMS_TO_TICKS(ms));return;}
    while(ms && time_ok()) {uint32_t part=ms>10?10:ms;p4_worker_idle(part);ms-=part;}
}
static void report(const p4_c6_result_t *r) {
    ESP_LOGI("p4_c6","PUBLIC phase=%u outcome=%u baseline=%d low_admitted=%d released=%d recovered=%d raw_io=%d primary=%d cleanup=%d paderr=%d pad=%d ie=%d oe=%d func=%u signal=%u real_ms=%lld",
        r->phase,r->outcome,r->baseline,r->low_attempted,r->released,r->recovered,raw_io_error,r->primary_error,
        r->cleanup_error,r->pad_error,r->final.level,r->final.input,r->final.output,r->final.function,r->final.signal,(long long)p4_monotonic_ms());
    if(r->phase!=5) {
        char text[260];snprintf(text,sizeof(text),"PUBLIC C6 LINK PROBE\nNO KEYS / NOT OFFLINE PROOF\nPhase %u / no host approval",r->phase);p4_ui_status(text);
        p4_worker_idle(0); // All prior IO and this display commit are collected.
    }
    ESP_LOGI("p4_c6","PUBLIC phase=%u baseline_pad=%d/%d/%d low_pad=%d/%d/%d release_pad=%d/%d/%d first_reply=%d last_reply=%d VID=%04x DEV=%04x funcs=%u CCCR=%02x CISbytes=%u",
        r->phase,r->initial.level,r->initial.input,r->initial.output,r->low.level,r->low.input,r->low.output,
        r->release.level,r->release.input,r->release.output,r->first_low,r->last_low,r->identity.manufacturer,
        r->identity.device,r->identity.functions,r->identity.cccr,r->identity.cis_used);
}
void p4_c6_before_abort(void) {
    // Task-level best effort only. SDK panic/WDT hardware reset bypasses this;
    // no claim that GPIO54 stays asserted across a reset.
    if(!atomic_load(&low_admitted))return;
    int e=low();p4_c6_pad_t p={.level=-1};int pe=pad(&p);
    ESP_LOGE("p4_c6","PUBLIC abort cleanup=%d paderr=%d pad=%d input=%d output=%d",e,pe,p.level,p.input,p.output);
}

_Noreturn void p4_c6_public_probe(void) {
    esp_reset_reason_t reason=esp_reset_reason();
    if(reason!=ESP_RST_POWERON) {
        p4_ui_status("PUBLIC C6 UNAVAILABLE\nNO KEYS / NO RETRY\nPrevious reset; inspect log");
        p4_c6_pad_t skipped={.level=-1};int pe=pad(&skipped);
        ESP_LOGW("p4_c6","PUBLIC skipped reset_reason=%d paderr=%d pad=%d input=%d output=%d; no low/release attempted",
            (int)reason,pe,skipped.level,skipped.input,skipped.output);
        for(;;)p4_worker_idle(250);
    }
    int64_t now=p4_monotonic_ms();if(now<0)p4_fatal();deadline=(uint64_t)now+P4_C6_PROBE_MS;
    const p4_c6_ops_t ops={p4_monotonic_ms,prepare,identity,low,release,pad,read_link,wait_cooperative,report};
    p4_c6_result_t result;p4_c6_run(&ops,&result,(uint64_t)now);
    // Cleanup GPIO assertion was attempted independently of all SDIO results.
    int cleanup_io=slot_up?sdmmc_host_deinit_slot(1):host_up?sdmmc_host_deinit():ESP_OK;
    if(result.low_attempted) {
        int again=low();if(again)result.cleanup_error=again;
    }
    p4_c6_pad_t after={.level=-1};int err=pad(&after);
    result.final=after;result.pad_error=err;
    if(result.low_attempted && (result.cleanup_error || err || !after.input || !after.output || after.level!=0))result.outcome=P4_C6_CLEANUP_FAILED;
    ESP_LOGI("p4_c6","PUBLIC stopped host_cleanup=%d pad_error=%d final_pad=%d input=%d output=%d func=%u signal=%u; no engine/key initialized",
        cleanup_io,err,after.level,after.input,after.output,after.function,after.signal);
    if(cleanup_io!=ESP_OK) {
        ESP_LOGE("p4_c6","PUBLIC host teardown failed; no feed or new probe admitted");p4_fatal();
    }
    static const char *names[]={"UNAVAILABLE","LINK CAUSALITY OBSERVED","INCONCLUSIVE","FAILED","CLEANUP FAILED"};
    char text[360];snprintf(text,sizeof(text),"PUBLIC C6 LINK PROBE\nNO KEYS / NOT OFFLINE PROOF\n%s\nVID %04x DEV %04x\nPad %d IN%d OUT%d\nCleanup %d / readback %d\nC6 die/rev/FW unknown",
        names[result.outcome],result.identity.manufacturer,result.identity.device,after.level,after.input,after.output,result.cleanup_error,err);
    p4_ui_status(text);
    for(;;)p4_worker_idle(250);
}
#else
_Noreturn void p4_c6_public_probe(void) {p4_fatal();}
void p4_c6_before_abort(void) {}
#endif
