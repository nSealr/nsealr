// SPDX-License-Identifier: MIT
#include "p4_entropy.h"
#include "p4_entropy_logic.h"
#include "c6_guard.h"
#include "bootloader_random.h"
#include "esp_random.h"
#include "esp_memory_utils.h"
#include "esp_private/esp_clk.h"
#include "esp_private/adc_share_hw_ctrl.h"
#include "esp_private/periph_ctrl.h"
#include "esp_private/regi2c_ctrl.h"
#include "hal/adc_ll.h"
#include "hal/trng_ll.h"
#include "soc/hp_sys_clkrst_reg.h"
#include "esp_timer.h"
#include "esp_rom_sys.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>
#if CONFIG_ESP32P4_REV_MIN_FULL < 300 || CONFIG_PM_ENABLE || CONFIG_ESP_BRINGUP_BYPASS_RANDOM_SETTING
#error "This public P4 source requires reviewed hw_ver3, fixed clocks and real SDK RNG"
#endif
#ifndef P4_ENTROPY_FIXED_UNAVAILABLE
#define P4_ENTROPY_FIXED_UNAVAILABLE 0
#endif
static const char *TAG="p4_public_entropy";
static portMUX_TYPE owner_lock=portMUX_INITIALIZER_UNLOCKED;
static p4_entropy_state_t history;
static struct {
 TaskHandle_t task;
 uint32_t shared_bus,shared_source,shared_div,shared_reset;
 p4_entropy_admission_t admission;
} owner;
static p4_entropy_report_t last_report;
_Static_assert(sizeof(owner)+sizeof(history)+sizeof(owner_lock)<=256,"INTERNAL provider cap");
_Static_assert(sizeof(last_report)<=512,"INTERNAL diagnostic cap");
static uint32_t analog_refs(void) {
 const uint8_t n=periph_rcc_acquire_enter(PERIPH_ANA_I2C_MASTER_MODULE);
 periph_rcc_exit();return n; // Read only; never acquire_exit/increment a foreign ref.
}
static bool owned(void) {
 portENTER_CRITICAL(&owner_lock);
 const bool ok=owner.admission.busy && owner.task==xTaskGetCurrentTaskHandle() &&
  xPortGetCoreID()==1 && !owner.admission.poisoned;
 portEXIT_CRITICAL(&owner_lock);return ok;
}
static bool guard(void *unused) {
 (void)unused;return owned() && p4_c6_guard_check(NULL);
}
static uint32_t adc_div_mask(void) {
 return HP_SYS_CLKRST_REG_ADC_CLK_EN | HP_SYS_CLKRST_REG_ADC_CLK_DIV_NUM_M |
  HP_SYS_CLKRST_REG_ADC_CLK_DIV_NUMERATOR_M | HP_SYS_CLKRST_REG_ADC_CLK_DIV_DENOMINATOR_M;
}
static bool shared_unchanged(void) {
 return (HP_SYS_CLKRST.soc_clk_ctrl2.val&~HP_SYS_CLKRST_REG_ADC_APB_CLK_EN)==owner.shared_bus &&
  (HP_SYS_CLKRST.peri_clk_ctrl22.val&~HP_SYS_CLKRST_REG_ADC_CLK_SRC_SEL_M)==owner.shared_source &&
  (HP_SYS_CLKRST.peri_clk_ctrl23.val&~adc_div_mask())==owner.shared_div &&
  (HP_SYS_CLKRST.hp_rst_en2.val&~HP_SYS_CLKRST_REG_RST_EN_ADC)==owner.shared_reset;
}
static int snapshot(void *unused,bool analog,p4_entropy_snapshot_t *s) {
 (void)unused;memset(s,0,sizeof(*s));s->readable=P4_BANK_SYSTEM;
 s->clock_bus=HP_SYS_CLKRST.soc_clk_ctrl2.val;
 s->clock_source=HP_SYS_CLKRST.peri_clk_ctrl22.val;
 s->clock_div=HP_SYS_CLKRST.peri_clk_ctrl23.val;s->reset_adc=HP_SYS_CLKRST.hp_rst_en2.val;
 s->cpu_hz=(uint32_t)esp_clk_cpu_freq();s->apb_hz=(uint32_t)esp_clk_apb_freq();
 s->xtal_hz=(uint32_t)esp_clk_xtal_freq();s->analog_refs=analog_refs();
 // LP date/reset controls are accessed by the pinned LL even when sample clock is off.
 s->trng_date=LP_TRNG.date.val;s->trng_reset=LP_TRNG.rstn.val;
 if(s->clock_bus&HP_SYS_CLKRST_REG_ADC_APB_CLK_EN)s->flags|=P4_E_BUS;
 if(s->clock_div&HP_SYS_CLKRST_REG_ADC_CLK_EN)s->flags|=P4_E_FUNC;
 if(!(s->reset_adc&HP_SYS_CLKRST_REG_RST_EN_ADC))s->flags|=P4_E_RESET_RELEASED;
 if(HP_SYS_CLKRST.peri_clk_ctrl22.reg_adc_clk_src_sel==0)s->flags|=P4_E_XTAL;
 if(HP_SYS_CLKRST.peri_clk_ctrl23.reg_adc_clk_div_num==0 &&
    HP_SYS_CLKRST.peri_clk_ctrl23.reg_adc_clk_div_numerator==0 &&
    HP_SYS_CLKRST.peri_clk_ctrl23.reg_adc_clk_div_denominator==0)s->flags|=P4_E_DIV0;
 if(LP_TRNG.date.clk_en){
  s->flags|=P4_E_TRNG_CLOCK;s->readable|=P4_BANK_TRNG;s->trng_cfg=LP_TRNG.cfg.val;
  if(LP_TRNG.cfg.sample_enable)s->flags|=P4_E_SAMPLE;
  if(LP_TRNG.cfg.timer_en)s->flags|=P4_E_XOR_TIMER;
  if(LP_TRNG.cfg.timer_pscale==255)s->flags|=P4_E_PSCALE255;
 }
 if(LP_TRNG.rstn.rstn)s->flags|=P4_E_TRNG_RESET;
 if(s->cpu_hz==CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ*1000000U &&
    s->xtal_hz==CONFIG_XTAL_FREQ*1000000U && s->apb_hz>0)s->flags|=P4_E_CPU_XTAL;
 if((s->flags&(P4_E_BUS|P4_E_FUNC|P4_E_RESET_RELEASED))==
    (P4_E_BUS|P4_E_FUNC|P4_E_RESET_RELEASED)){
  s->readable|=P4_BANK_ADC;s->adc_ctrl=ADC.ctrl_reg.val;s->adc_ctrl2=ADC.ctrl2.val;
  s->pattern=ADC.sar1_patt_tab[0].sar1_patt_tab;
  if(ADC.ctrl_reg.sar_clk_div==15)s->flags|=P4_E_SAR_DIV15;
  if(ADC.ctrl2.timer_en)s->flags|=P4_E_TIMER;
  if(ADC.ctrl2.timer_sel)s->flags|=P4_E_TIMER_SELECT;
  if(ADC.ctrl2.timer_target==100)s->flags|=P4_E_TARGET100;
  if(ADC.ctrl_reg.sar1_patt_len==0)s->flags|=P4_E_PATTERN_LEN;
  if(s->pattern==0xAEBAEB)s->flags|=P4_E_PATTERN;
  if(LP_ADC.meas1_mux.sar1_dig_force)s->flags|=P4_E_DIGITAL;
  if(ADC.ctrl_reg.xpd_sar1_force==LP_ADC_FORCE_XPD_SAR_PU)s->flags|=P4_E_POWER;
 }
 if(analog){
  if(!s->analog_refs || !ANALOG_CLOCK_IS_ENABLED())return P4_RNG_READBACK;
  s->readable|=P4_BANK_ANALOG;
  s->calibration=(REGI2C_READ_MASK(I2C_SAR_ADC,ADC_SAR1_INITIAL_CODE_HIGH_ADDR)<<8) |
   REGI2C_READ_MASK(I2C_SAR_ADC,ADC_SAR1_INITIAL_CODE_LOW_ADDR);
  s->reference=(REGI2C_READ_MASK(I2C_SAR_ADC,I2C_SAR_ADC_DTEST_VDD_GRP1)<<8) |
   REGI2C_READ_MASK(I2C_SAR_ADC,I2C_SAR_ADC_ENT_VDD_GRP1);
  if(s->calibration==2166)s->flags|=P4_E_CAL2166;
  if(s->reference==1)s->flags|=P4_E_REFERENCE;
 }
 return shared_unchanged()?P4_RNG_OK:P4_RNG_OWNERSHIP;
}
static int try_lock(void *unused,unsigned unit) {
 (void)unused;return adc_lock_try_acquire(unit==0?ADC_UNIT_1:ADC_UNIT_2);
}
static int release_lock(void *unused,unsigned unit) {
 (void)unused;return adc_lock_release(unit==0?ADC_UNIT_1:ADC_UNIT_2);
}
static void bus(void *unused,bool enable) {
 (void)unused;if(enable)adc_apb_periph_claim();else adc_apb_periph_free();
}
static bool bus_released(void *unused) {
 (void)unused;return !HP_SYS_CLKRST.soc_clk_ctrl2.reg_adc_apb_clk_en &&
  !HP_SYS_CLKRST.peri_clk_ctrl23.reg_adc_clk_en && shared_unchanged();
}
static void source(void *unused,bool enable) {
 (void)unused;if(enable)bootloader_random_enable();else bootloader_random_disable();
}
static int word(void *unused,uint32_t *out,size_t *n) {
 (void)unused;if(!guard(NULL))return P4_RNG_INTERRUPTED;
 *out=esp_random();*n=4;return P4_RNG_OK;
}
static int64_t now(void *unused){(void)unused;return esp_timer_get_time();}
static void pause_source(void *unused){(void)unused;esp_rom_delay_us(20);}
bool p4_entropy_bind_worker(void) {
 portENTER_CRITICAL(&owner_lock);
 const bool ok=P4_WDT_PROBE_MODE==0 && xPortGetCoreID()==1 && !xPortInIsrContext() && !owner.admission.bound && !owner.admission.poisoned;
 if(ok){owner.task=xTaskGetCurrentTaskHandle();owner.admission.bound=true;}else owner.admission.poisoned=true;
 portEXIT_CRITICAL(&owner_lock);return ok;
}
bool p4_entropy_used(void) {
 portENTER_CRITICAL(&owner_lock);const bool used=owner.admission.used;portEXIT_CRITICAL(&owner_lock);return used;
}
int p4_entropy_fault_mode(void){return P4_ENTROPY_FIXED_UNAVAILABLE;}
ptrdiff_t p4_entropy_fill32(uint8_t *out,size_t capacity) {
 if(!out || capacity!=32)return P4_RNG_ARGUMENT;
 if(!esp_ptr_internal(out) || !esp_ptr_internal(out+31) ||
    !esp_ptr_byte_accessible(out) || !esp_ptr_byte_accessible(out+31))return P4_RNG_ARGUMENT;
 p4_entropy_wipe(out,32);
 portENTER_CRITICAL(&owner_lock);
 const int admission=p4_entropy_admit(&owner.admission,
  owner.task==xTaskGetCurrentTaskHandle() && xPortGetCoreID()==1 && !xPortInIsrContext());
 if(admission!=P4_RNG_OK){portEXIT_CRITICAL(&owner_lock);return admission;}
 portEXIT_CRITICAL(&owner_lock);
 memset(&last_report,0,sizeof(last_report));last_report.status=P4_RNG_UNAVAILABLE;
 const int64_t started=esp_timer_get_time();
 int status=P4_RNG_INTERRUPTED;
 if(p4_c6_guard_check("entropy-before")){
  if(P4_ENTROPY_FIXED_UNAVAILABLE){status=P4_RNG_UNAVAILABLE;last_report.elapsed_us=esp_timer_get_time()-started;}
  else{
   owner.shared_bus=HP_SYS_CLKRST.soc_clk_ctrl2.val&~HP_SYS_CLKRST_REG_ADC_APB_CLK_EN;
   owner.shared_source=HP_SYS_CLKRST.peri_clk_ctrl22.val&~HP_SYS_CLKRST_REG_ADC_CLK_SRC_SEL_M;
   owner.shared_div=HP_SYS_CLKRST.peri_clk_ctrl23.val&~adc_div_mask();
   owner.shared_reset=HP_SYS_CLKRST.hp_rst_en2.val&~HP_SYS_CLKRST_REG_RST_EN_ADC;
   const p4_entropy_ops_t ops={.context=NULL,.try_lock=try_lock,.release_lock=release_lock,
    .bus=bus,.bus_released=bus_released,.source=source,.snapshot=snapshot,.word=word,
    .guard=guard,.now=now,.pause=pause_source,.analog_increment=1,.start_us=started};
   status=p4_entropy_collect(&history,&ops,out,capacity,&last_report);
  }
 }
 if(!p4_c6_guard_check("entropy-after"))status=P4_RNG_INTERRUPTED;
 const int64_t ended=esp_timer_get_time();last_report.elapsed_us=ended>=started?ended-started:-1;
 if(status==P4_RNG_OK && (ended<started || ended-started>=50000))status=P4_RNG_TIMEOUT;
 if(status!=P4_RNG_OK){p4_entropy_wipe(out,32);p4_entropy_wipe(history.previous,32);history.have_previous=false;}
 last_report.status=status;
 portENTER_CRITICAL(&owner_lock);
 if(history.poisoned)owner.admission.poisoned=true;
 owner.admission.busy=false;portEXIT_CRITICAL(&owner_lock);
 return status==P4_RNG_OK?32:status;
}
void p4_entropy_log_report(void) {
 if(!p4_entropy_used())return;
 const p4_entropy_report_t *r=&last_report;const p4_entropy_snapshot_t *s=&r->enabled;
 ESP_LOGI(TAG,"PUBLIC RNG status=%ld words=%lu supplied=%u us=%lld helper=%lu/%lu released=%lu banks=%lu/%lu/%lu/%lu flags=%lx/%lx/%lx; no entropy-quality claim",
  (long)r->status,(unsigned long)r->words,r->status==P4_RNG_OK?32U:0U,(long long)r->elapsed_us,
  (unsigned long)r->source_enable_calls,(unsigned long)r->source_disable_calls,(unsigned long)r->released,
  (unsigned long)r->before.readable,(unsigned long)s->readable,(unsigned long)r->after.readable,(unsigned long)r->rest.readable,
  (unsigned long)s->flags,(unsigned long)r->after.flags,(unsigned long)r->rest.flags);
 ESP_LOGI(TAG,"PUBLIC RNG cfg=%lx date=%lx rst=%lx adc=%lx/%lx clocks=%lx/%lx/%lx pattern=%lx cal=%lu ref=%lu ANArefs=%lu/%lu/%lu/%lu configured_hz=%lu/%lu/%lu sample_cnt=%lu/%lu; counters diagnostic only",
  (unsigned long)s->trng_cfg,(unsigned long)s->trng_date,(unsigned long)s->trng_reset,
  (unsigned long)s->adc_ctrl,(unsigned long)s->adc_ctrl2,(unsigned long)s->clock_bus,
  (unsigned long)s->clock_source,(unsigned long)s->clock_div,(unsigned long)s->pattern,
  (unsigned long)s->calibration,(unsigned long)s->reference,(unsigned long)r->before.analog_refs,
  (unsigned long)s->analog_refs,(unsigned long)r->after.analog_refs,(unsigned long)r->rest.analog_refs,
  (unsigned long)s->cpu_hz,(unsigned long)s->apb_hz,(unsigned long)s->xtal_hz,
  (unsigned long)(s->trng_cfg>>24),(unsigned long)(r->after.trng_cfg>>24));
}
