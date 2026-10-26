// SPDX-License-Identifier: MIT
#include "c6_guard.h"
#include <stdatomic.h>
#include <stddef.h>
#if P4_WDT_PROBE_MODE == 0
#include "driver/gpio.h"
#include "soc/io_mux_reg.h"
#include "soc/gpio_sig_map.h"
#include "soc/gpio_reg.h"
#include "soc/soc.h"
#include "esp_log.h"

enum { NEW, ADMITTING, ACTIVE, FAILED };
static atomic_uint state;
static atomic_bool low_admitted;
static atomic_flag aborting=ATOMIC_FLAG_INIT;
static const char *TAG="p4_c6_guard";
typedef struct {
    int error,level;
    gpio_io_config_t config;
} sample_t;

static bool sample(sample_t *s) {
    *s=(sample_t){.level=-1};
    s->error=gpio_get_io_config(54,&s->config);
    if(s->error!=ESP_OK)return false;
    const gpio_io_config_t *c=&s->config;
    if(c->ie)s->level=gpio_get_level(54);
    return c->ie && c->oe && s->level==0 && c->fun_sel==PIN_FUNC_GPIO &&
        c->sig_out==SIG_GPIO_OUT_IDX && !c->oe_ctrl_by_periph && !c->oe_inv &&
        !c->od && !c->pu && !c->pd;
}
static void report(bool good,const char *phase,int write_error,const sample_t *s) {
    const gpio_io_config_t *c=&s->config;
    if(good) {
        ESP_LOGI(TAG,"PUBLIC phase=%s pad=%d ie=%d oe=%d func=%u signal=%u; no RF/USB-host proof",
            phase,s->level,c->ie,c->oe,c->fun_sel,c->sig_out);
    } else {
        ESP_LOGE(TAG,"PUBLIC FAILED phase=%s write=%d read=%d pad=%d ie=%d oe=%d func=%u signal=%u periph=%d inv=%d od=%d pu=%d pd=%d",
            phase?phase:"cooperative",write_error,s->error,s->level,c->ie,c->oe,
            c->fun_sel,c->sig_out,c->oe_ctrl_by_periph,c->oe_inv,c->od,c->pu,c->pd);
    }
}
static bool fail(const char *phase,int write_error,const sample_t *s) {
    atomic_store(&state,FAILED);report(false,phase,write_error,s);return false;
}
static int drive_low(void) {
    // Fatal cleanup is required even if the first GPIO call fails partially.
    atomic_store(&low_admitted,true);
    int e=gpio_set_level(54,0);if(e!=ESP_OK)return e;
    // Pinned P4 hw_ver3: gpio_config(output) does not normalize OEN_SEL.
    // Select the GPIO enable register without disabling/releasing the output.
    // Preserve other routing bits; gpio_config below selects simple GPIO data.
    uint32_t routing=REG_READ(GPIO_FUNC54_OUT_SEL_CFG_REG);
    REG_WRITE(GPIO_FUNC54_OUT_SEL_CFG_REG,
        (routing|GPIO_FUNC54_OEN_SEL)&~GPIO_FUNC54_OEN_INV_SEL);
    const gpio_config_t config={.pin_bit_mask=1ULL<<54,.mode=GPIO_MODE_INPUT_OUTPUT,
        .pull_up_en=GPIO_PULLUP_DISABLE,.pull_down_en=GPIO_PULLDOWN_DISABLE,
        .intr_type=GPIO_INTR_DISABLE};
    return gpio_config(&config);
}
bool p4_c6_guard_begin(void) {
    unsigned expected=NEW;
    sample_t s={.level=-1};
    if(!atomic_compare_exchange_strong(&state,&expected,ADMITTING))
        return fail("begin-state",-1,&s);
    int e=drive_low();
    bool valid=sample(&s);
    if(e!=ESP_OK || !valid)return fail("begin",e,&s);
    // A simultaneous task-level fatal must never be overwritten by ACTIVE.
    expected=ADMITTING;
    if(!atomic_compare_exchange_strong(&state,&expected,ACTIVE))
        return fail("begin-aborted",-1,&s);
    report(true,"begin",0,&s);return true;
}
bool p4_c6_guard_check(const char *phase) {
    sample_t s={.level=-1};
    if(atomic_load(&state)!=ACTIVE)return fail(phase,-1,&s);
    bool valid=sample(&s);
    if(!valid || atomic_load(&state)!=ACTIVE)return fail(phase,0,&s);
    if(phase)report(true,phase,0,&s);
    return true;
}
void p4_c6_guard_before_abort(void) {
    // No p4_fatal/UI/feed call here. Reentry/concurrent fatal never recurses.
    atomic_store(&state,FAILED);
    if(atomic_flag_test_and_set(&aborting) || !atomic_load(&low_admitted))return;
    int e=drive_low();sample_t s;
    bool valid=sample(&s);
    report(false,valid && e==ESP_OK?"abort-low-observed":"abort-cleanup-failed",e,&s);
    // A successful best-effort low does not restore ACTIVE or promise reset hold.
}
#else
bool p4_c6_guard_begin(void) {return true;}
bool p4_c6_guard_check(const char *phase) {(void)phase;return true;}
void p4_c6_guard_before_abort(void) {}
#endif
