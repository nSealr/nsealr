// SPDX-License-Identifier: MIT
#include "s3_entropy.h"
#include "s3_entropy_rcc.h"
#include "otg_transport.h"
#include "pin_config.h"
#include "bootloader_random.h"
#include "esp_random.h"
#include "esp_memory_utils.h"
#include "esp_timer.h"
#include "esp_rom_sys.h"
#include "esp_private/esp_clk.h"
#include "esp_private/periph_ctrl.h"
#include "hal/clk_gate_ll.h"
#include "hal/regi2c_ctrl.h"
#include "soc/system_reg.h"
#include "soc/syscon_reg.h"
#include "soc/apb_saradc_reg.h"
#include "soc/rtc_cntl_reg.h"
#include "soc/sens_reg.h"
#include "soc/regi2c_saradc.h"
#include "soc/lcd_cam_struct.h"
#include "soc/io_mux_reg.h"
#include "soc/gpio_reg.h"
#include "soc/gpio_periph.h"
#include "soc/rtc_cntl_struct.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <cstdio>
#include <cstring>
#if CONFIG_ESP_WIFI_ENABLED || CONFIG_BT_ENABLED || CONFIG_PM_ENABLE
#error "The public S3 entropy experiment requires no RF driver or dynamic power management"
#endif
static portMUX_TYPE owner_lock=portMUX_INITIALIZER_UNLOCKED;
static S3EntropyState history;
struct Context {
    TaskHandle_t task=nullptr,bound_task=nullptr;uint32_t generation=0,epoch=0;
    bool busy=false,module=false,poisoned=false,diagnostic=false;
    S3EntropyBudget budget;
    uint32_t pins[20]={},outputs[20]={},gpio_enable=0,gpio_enable1=0,lcd_clock=0;
};
static Context ctx;
static S3EntropyReport last_report; // Part of the <=2048byte public diagnostic store.
static_assert(sizeof(Context)+sizeof(S3EntropyState)+sizeof(owner_lock)<=256,"finite INTERNAL provider state");
static const int pins[]={PIN_LCD_DC,PIN_LCD_WR,PIN_LCD_RD,PIN_LCD_RES,PIN_LCD_CS,PIN_LCD_BL,
    PIN_LCD_D0,PIN_LCD_D1,PIN_LCD_D2,PIN_LCD_D3,PIN_LCD_D4,PIN_LCD_D5,PIN_LCD_D6,PIN_LCD_D7,19,20};
static_assert(sizeof(pins)/sizeof(*pins)<=20,"fixed pin ownership snapshot");
static uint32_t pin_config(unsigned i){return REG_READ(GPIO_PIN_MUX_REG[pins[i]]);}
static uint32_t output_config(unsigned i){return REG_READ(GPIO_FUNC0_OUT_SEL_CFG_REG+4*pins[i]);}
static uint32_t pin_signature(){uint32_t v=REG_READ(GPIO_ENABLE_REG)^REG_READ(GPIO_ENABLE1_REG);
    for(unsigned i=0;i<sizeof(pins)/sizeof(*pins);++i)v=(v<<3)^(v>>29)^pin_config(i)^output_config(i);return v;}
static bool pins_unchanged(){
    if(LCD_CAM.lcd_clock.val!=ctx.lcd_clock||REG_READ(GPIO_ENABLE_REG)!=ctx.gpio_enable||REG_READ(GPIO_ENABLE1_REG)!=ctx.gpio_enable1)return false;
    for(unsigned i=0;i<sizeof(pins)/sizeof(*pins);++i)if(pin_config(i)!=ctx.pins[i]||output_config(i)!=ctx.outputs[i])return false;
    return true;
}
static uint32_t refs(){const auto n=periph_rcc_acquire_enter(PERIPH_SARADC_MODULE);periph_rcc_exit();return n;}
static uint32_t reference_mask(){
    return REGI2C_READ_MASK(I2C_SAR_ADC,ADC_SARADC_ENCAL_REF_ADDR)|
        (REGI2C_READ_MASK(I2C_SAR_ADC,ADC_SARADC_ENT_TSENS_ADDR)<<1)|
        (REGI2C_READ_MASK(I2C_SAR_ADC,ADC_SARADC_ENT_RTC_ADDR)<<2)|
        (REGI2C_READ_MASK(I2C_SAR_ADC,ADC_SARADC_DTEST_RTC_ADDR)<<3);
}
static void observe(S3EntropySnapshot &s){
    s=S3EntropySnapshot{};s.readable=EntropySystem|EntropySens|EntropyAnalog;
    s.system_clock=REG_READ(SYSTEM_PERIP_CLK_EN0_REG);s.system_reset=REG_READ(SYSTEM_PERIP_RST_EN0_REG);
    s.wifi_clock=REG_READ(SYSTEM_WIFI_CLK_EN_REG);s.rtc_clock=REG_READ(RTC_CNTL_CLK_CONF_REG);
    s.cpu_hz=esp_clk_cpu_freq();s.apb_hz=esp_clk_apb_freq();s.references=refs();
    s.reference_mask=reference_mask();s.lcd_clock=LCD_CAM.lcd_clock.val;
    s.usb_mux=(RTCCNTL.usb_conf.sw_hw_usb_phy_sel<<1)|RTCCNTL.usb_conf.sw_usb_phy_sel;
    s.pin_signature=pin_signature();
    if(s.wifi_clock&SYSTEM_WIFI_CLK_RNG_EN)s.flags|=E_Rng;
    if(s.rtc_clock&RTC_CNTL_DIG_CLK8M_EN)s.flags|=E_Rc;
    if(s.system_clock&SYSTEM_APB_SARADC_CLK_EN)s.flags|=E_Bus;
    if(!(s.system_reset&SYSTEM_APB_SARADC_RST))s.flags|=E_NoReset;
    if(REG_GET_FIELD(SENS_SAR_POWER_XPD_SAR_REG,SENS_FORCE_XPD_SAR)==3)s.flags|=E_Power;
    if(REG_READ(SENS_SAR_MEAS1_MUX_REG)&SENS_SAR1_DIG_FORCE)s.flags|=E_Digital1;
    if(!(REG_READ(SENS_SAR_MEAS2_MUX_REG)&SENS_SAR2_RTC_FORCE))s.flags|=E_NoRtc2;
    // Only read the digital/data bank while its bus clock is on and reset is off.
    if((s.flags&(E_Bus|E_NoReset))!=(E_Bus|E_NoReset))return;
    s.readable|=EntropyDigital|EntropyData;
    const uint32_t c=REG_READ(APB_SARADC_CTRL_REG),c2=REG_READ(APB_SARADC_CTRL2_REG),cm=REG_READ(APB_SARADC_APB_ADC_CLKM_CONF_REG);
    if(cm&APB_SARADC_CLK_EN)s.flags|=E_DigiClock;
    if(c&APB_SARADC_SAR_CLK_GATED)s.flags|=E_SarClock;
    if(c2&APB_SARADC_TIMER_EN)s.flags|=E_Timer;
    if(c2&APB_SARADC_TIMER_SEL)s.flags|=E_TimerSelect;
    if(!(c&APB_SARADC_START_FORCE))s.flags|=E_NoStartForce;
    if(!(c2&APB_SARADC_MEAS_NUM_LIMIT))s.flags|=E_Unlimited;
    const auto arb=REG_READ(APB_SARADC_APB_ADC_ARB_CTRL_REG);
    if(!(arb&(APB_SARADC_ADC_ARB_GRANT_FORCE|APB_SARADC_ADC_ARB_FIX_PRIORITY)))s.flags|=E_Arb;
    if(REG_GET_FIELD(APB_SARADC_CTRL_REG,APB_SARADC_WORK_MODE)==1)s.flags|=E_Double;
    if(REG_GET_FIELD(APB_SARADC_CTRL_REG,APB_SARADC_SAR1_PATT_LEN)==0&&REG_GET_FIELD(APB_SARADC_CTRL_REG,APB_SARADC_SAR2_PATT_LEN)==0)s.flags|=E_PatternLength;
    s.clock_select=REG_GET_FIELD(APB_SARADC_APB_ADC_CLKM_CONF_REG,APB_SARADC_CLK_SEL);
    s.clock_div=REG_GET_FIELD(APB_SARADC_APB_ADC_CLKM_CONF_REG,APB_SARADC_CLKM_DIV_NUM);
    s.sar_div=REG_GET_FIELD(APB_SARADC_CTRL_REG,APB_SARADC_SAR_CLK_DIV);
    s.timer_target=REG_GET_FIELD(APB_SARADC_CTRL2_REG,APB_SARADC_TIMER_TARGET);
    s.pattern1=REG_READ(APB_SARADC_SAR1_PATT_TAB1_REG);s.pattern2=REG_READ(APB_SARADC_SAR2_PATT_TAB1_REG);
    s.filter0=REG_GET_FIELD(APB_SARADC_FILTER_CTRL0_REG,APB_SARADC_FILTER_CHANNEL0);
    s.filter1=REG_GET_FIELD(APB_SARADC_FILTER_CTRL0_REG,APB_SARADC_FILTER_CHANNEL1);
    s.data1=REG_GET_FIELD(APB_SARADC_APB_SARADC1_DATA_STATUS_REG,APB_SARADC_ADC1_DATA);
    s.data2=REG_GET_FIELD(APB_SARADC_APB_SARADC2_DATA_STATUS_REG,APB_SARADC_ADC2_DATA);
}
static bool owner(){
    portENTER_CRITICAL_SAFE(&owner_lock);
    const bool ok=ctx.busy&&ctx.task==xTaskGetCurrentTaskHandle()&&xPortGetCoreID()==0&&!ctx.poisoned;
    portEXIT_CRITICAL_SAFE(&owner_lock);return ok;
}
static void unlock(void*){
    portENTER_CRITICAL_SAFE(&owner_lock);
    if(ctx.task!=xTaskGetCurrentTaskHandle())ctx.poisoned=true;
    else{ctx.busy=false;ctx.task=nullptr;}
    portEXIT_CRITICAL_SAFE(&owner_lock);
}
struct Rcc {
    uint8_t acquire_enter(){return periph_rcc_acquire_enter(PERIPH_SARADC_MODULE);}
    uint8_t release_enter(){return periph_rcc_release_enter(PERIPH_SARADC_MODULE);}
    void acquire_exit(uint8_t n){periph_rcc_acquire_exit(PERIPH_SARADC_MODULE,n);}
    void release_exit(uint8_t n){periph_rcc_release_exit(PERIPH_SARADC_MODULE,n);}
    void exit(){periph_rcc_exit();}
    bool inactive(){return !(REG_READ(SYSTEM_PERIP_CLK_EN0_REG)&SYSTEM_APB_SARADC_CLK_EN)&&
        (REG_READ(SYSTEM_PERIP_RST_EN0_REG)&SYSTEM_APB_SARADC_RST);}
    void enable_clock(){periph_ll_enable_clk_clear_rst(PERIPH_SARADC_MODULE);}
    void disable_clock(){periph_ll_disable_clk_set_rst(PERIPH_SARADC_MODULE);}
};
static S3EntropyStatus claim(void*,S3EntropySnapshot *before){
    portENTER_CRITICAL_SAFE(&owner_lock);
    if(ctx.busy){portEXIT_CRITICAL_SAFE(&owner_lock);return S3EntropyStatus::Ownership;}
    if(ctx.poisoned||history.poisoned||ctx.generation==UINT32_MAX||xPortGetCoreID()!=0||xPortInIsrContext()||ctx.bound_task!=xTaskGetCurrentTaskHandle()){
        portEXIT_CRITICAL_SAFE(&owner_lock);return S3EntropyStatus::Unavailable;}
    ctx.busy=true;ctx.task=xTaskGetCurrentTaskHandle();++ctx.generation;
    portEXIT_CRITICAL_SAFE(&owner_lock);
    ctx.lcd_clock=LCD_CAM.lcd_clock.val;ctx.gpio_enable=REG_READ(GPIO_ENABLE_REG);ctx.gpio_enable1=REG_READ(GPIO_ENABLE1_REG);
    for(unsigned i=0;i<sizeof(pins)/sizeof(*pins);++i){ctx.pins[i]=pin_config(i);ctx.outputs[i]=output_config(i);}
    observe(*before);Rcc rcc;
    const auto status=s3_entropy_rcc_claim(rcc);
    if(status!=S3EntropyStatus::PublicDraw){unlock(nullptr);return status;}
    ctx.module=true;return S3EntropyStatus::PublicDraw;
}
static S3EntropyStatus enable(void*){
    if(!owner())return S3EntropyStatus::Ownership;
    bootloader_random_enable();
    // Restore the provider-owned APB gate, without a reset pulse or vendor edit.
    Rcc rcc;return s3_entropy_rcc_gate(rcc);
}
static S3EntropyStatus snapshot(void*,S3EntropySnapshot *out){
    if(!owner())return S3EntropyStatus::Ownership;observe(*out);
    if(out->references!=1||!pins_unchanged()||out->usb_mux!=3)return S3EntropyStatus::Ownership;
    return S3EntropyStatus::PublicDraw;
}
static S3EntropyStatus word(void*,uint32_t *out,size_t *n){
    if(!owner())return S3EntropyStatus::Ownership;
    *out=esp_random();*n=4;return S3EntropyStatus::PublicDraw;
}
static S3EntropyStatus cleanup(void*,bool attempted,S3EntropySnapshot *rest){
    if(attempted)bootloader_random_disable(); // Also after partial enable/error.
    Rcc rcc;
    const auto status=ctx.module?s3_entropy_rcc_release(rcc):S3EntropyStatus::Cleanup;
    if(status!=S3EntropyStatus::PublicDraw)ctx.poisoned=true;
    else ctx.module=false;
    // Changed/underflowed foreign counts remain untouched; terminal failure,
    // never a claim of balanced hardware/reference recovery from corruption.
    observe(*rest);
    return status==S3EntropyStatus::PublicDraw&&pins_unchanged()?status:S3EntropyStatus::Cleanup;
}
static int64_t now(void*){return esp_timer_get_time();}
static bool interrupted(void*){return !otg_current(ctx.epoch);}
static void pause(void*){esp_rom_delay_us(20);}
void s3_entropy_bind_public_epoch(uint32_t epoch){
    portENTER_CRITICAL_SAFE(&owner_lock);
    if(ctx.busy||(ctx.bound_task&&ctx.bound_task!=xTaskGetCurrentTaskHandle()))ctx.poisoned=true;
    else{ctx.bound_task=xTaskGetCurrentTaskHandle();ctx.epoch=epoch;}
    portEXIT_CRITICAL_SAFE(&owner_lock);
}
void s3_entropy_diagnostic_mode(bool enabled){
    portENTER_CRITICAL_SAFE(&owner_lock);
    if(ctx.busy)ctx.poisoned=true;else ctx.diagnostic=enabled;
    portEXIT_CRITICAL_SAFE(&owner_lock);
}
extern "C" int32_t nsealr_s3_public_auxiliary(uint8_t *out,size_t capacity,size_t *written){
    if(!out||capacity!=32||!written)return int32_t(S3EntropyStatus::Argument);
    if(!esp_ptr_internal(out)||!esp_ptr_internal(out+31)){*written=0;s3_entropy_wipe(out,32);return int32_t(S3EntropyStatus::Unavailable);}
    *written=0;s3_entropy_wipe(out,32);
    portENTER_CRITICAL_SAFE(&owner_lock);
    if(ctx.busy||ctx.bound_task!=xTaskGetCurrentTaskHandle()||xPortInIsrContext()){
        portEXIT_CRITICAL_SAFE(&owner_lock);return int32_t(S3EntropyStatus::Ownership);}
    if(!ctx.budget.take(ctx.diagnostic)){
        last_report=S3EntropyReport{};last_report.status=S3EntropyStatus::Unavailable;
        portEXIT_CRITICAL_SAFE(&owner_lock);return int32_t(S3EntropyStatus::Unavailable);}
    portEXIT_CRITICAL_SAFE(&owner_lock);
    const S3EntropyOps ops={nullptr,claim,enable,snapshot,word,cleanup,unlock,now,interrupted,pause};
    S3EntropyReport report;
    const auto status=s3_entropy_collect(history,ops,out,capacity,written,report);
    portENTER_CRITICAL_SAFE(&owner_lock);last_report=report;portEXIT_CRITICAL_SAFE(&owner_lock);
    return int32_t(status);
}
const S3EntropyReport &s3_entropy_last_report(){return last_report;}
void s3_entropy_log_report(unsigned draw,const uint8_t *sample){
    // Fixed public diagnostics only. Banks omitted by readable are UNKNOWN.
    const auto &r=last_report;char line[384];
    std::snprintf(line,sizeof(line),"s3-public-rng-v1 draw=%u status=%ld bytes=%u elapsed_us=%lld flags=%lx/%lx/%lx readable=%lu/%lu/%lu/%lu refs=%lu/%lu/%lu/%lu\n",draw,(long)r.status,r.words*4,(long long)r.elapsed_us,
      (unsigned long)r.enabled.flags,(unsigned long)r.after.flags,(unsigned long)r.rest.flags,
      (unsigned long)r.before.readable,(unsigned long)r.enabled.readable,(unsigned long)r.after.readable,(unsigned long)r.rest.readable,
      (unsigned long)r.before.references,(unsigned long)r.enabled.references,(unsigned long)r.after.references,(unsigned long)r.rest.references);otg_line(line);
    const auto &s=r.enabled;
    std::snprintf(line,sizeof(line),"s3-public-rng-reg-v1 sys=%lx/%lx wifi=%lx rtc=%lx configured_cpu=%lu apb=%lu sel=%lu div=%lu/%lu timer=%lu patt=%lx/%lx ref=%lu data=%lx/%lx->%lx/%lx lcd=%lx mux=%lu pins=%lx\n",
      (unsigned long)s.system_clock,(unsigned long)s.system_reset,(unsigned long)s.wifi_clock,(unsigned long)s.rtc_clock,(unsigned long)s.cpu_hz,(unsigned long)s.apb_hz,
      (unsigned long)s.clock_select,(unsigned long)s.clock_div,(unsigned long)s.sar_div,(unsigned long)s.timer_target,(unsigned long)s.pattern1,(unsigned long)s.pattern2,(unsigned long)s.reference_mask,
      (unsigned long)s.data1,(unsigned long)s.data2,(unsigned long)r.after.data1,(unsigned long)r.after.data2,(unsigned long)s.lcd_clock,(unsigned long)s.usb_mux,(unsigned long)s.pin_signature);otg_line(line);
    if(sample&&r.status==S3EntropyStatus::PublicDraw){char hex[65];constexpr char digits[]="0123456789abcdef";
      for(unsigned i=0;i<32;++i){hex[2*i]=digits[sample[i]>>4];hex[2*i+1]=digits[sample[i]&15];}hex[64]=0;
      std::snprintf(line,sizeof(line),"s3-public-rng-sample-v1 draw=%u public-not-identity=%s\n",draw,hex);otg_line(line);}
}
