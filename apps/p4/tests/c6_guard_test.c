// SPDX-License-Identifier: MIT
#include "c6_guard.h"
#include "driver/gpio.h"
#include "soc/gpio_reg.h"
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>
enum { GOOD,READ_ERROR,INPUT_OFF,OUTPUT_OFF,HIGH_PAD,BAD_MUX,BAD_SIGNAL,
       PERIPH,INVERTED,OPEN_DRAIN,PULL_UP,PULL_DOWN };
static unsigned fault,sets,configs,reads,level_reads;
static int set_error,config_error;
static bool abort_on_read;
static uint32_t output_select; // SDK hw_ver3 reset OEN_SEL=0, inversion=0.
static unsigned register_writes;
uint32_t p4_test_reg_read(uint32_t address) {assert(address==GPIO_FUNC54_OUT_SEL_CFG_REG);return output_select;}
void p4_test_reg_write(uint32_t address,uint32_t value) {
    assert(address==GPIO_FUNC54_OUT_SEL_CFG_REG && sets>0);
    assert((value&GPIO_FUNC54_OEN_SEL) && !(value&GPIO_FUNC54_OEN_INV_SEL));
    register_writes++;output_select=value;
}
void p4_test_log(const char *tag,const char *fmt,...) {
    printf("%s: ",tag);va_list args;va_start(args,fmt);vprintf(fmt,args);va_end(args);putchar('\n');
}
int gpio_set_level(int pin,uint32_t value) {
    assert(pin==54 && value==0);sets++;return set_error;
}
int gpio_config(const gpio_config_t *c) {
    assert(c && c->pin_bit_mask==(1ULL<<54) && c->mode==GPIO_MODE_INPUT_OUTPUT);
    assert(!c->pull_up_en && !c->pull_down_en && !c->intr_type);
    configs++;return config_error; // No release/input-only operation is accepted.
}
int gpio_get_io_config(int pin,gpio_io_config_t *c) {
    assert(pin==54);reads++;
    if(abort_on_read) {abort_on_read=false;p4_c6_guard_before_abort();}
    if(fault==READ_ERROR)return -7;
    *c=(gpio_io_config_t){.ie=true,.oe=true,.fun_sel=1,.sig_out=256,
        .oe_ctrl_by_periph=!(output_select&GPIO_FUNC54_OEN_SEL),.oe_inv=!!(output_select&GPIO_FUNC54_OEN_INV_SEL)};
    if(fault==INPUT_OFF)c->ie=false;
    if(fault==OUTPUT_OFF)c->oe=false;
    if(fault==BAD_MUX)c->fun_sel=0;
    if(fault==BAD_SIGNAL)c->sig_out=17;
    if(fault==PERIPH)c->oe_ctrl_by_periph=true;
    if(fault==INVERTED)c->oe_inv=true;
    if(fault==OPEN_DRAIN)c->od=true;
    if(fault==PULL_UP)c->pu=true;
    if(fault==PULL_DOWN)c->pd=true;
    return 0;
}
int gpio_get_level(int pin) {assert(pin==54);level_reads++;return fault==HIGH_PAD?1:0;}
static void one(unsigned scenario) {
    if(scenario==14) {
        assert(!p4_c6_guard_check(NULL));assert(!p4_c6_guard_begin());
        assert(!sets && !configs && !reads);
    } else if(scenario==24) {
        p4_c6_guard_before_abort();assert(!p4_c6_guard_begin());assert(!sets);
    } else if(scenario==26) {
        abort_on_read=true;assert(!p4_c6_guard_begin());
    } else {
        if(scenario==1)set_error=-5;
        if(scenario==2)config_error=-6;
        if(scenario>=3 && scenario<=13)fault=scenario-2;
        bool began=p4_c6_guard_begin();
        if(scenario==1 || scenario==2 || (scenario>=3 && scenario<=13)) {
            assert(!began);
            if(scenario==4)assert(!level_reads); // Disabled input never fabricates pad0.
        } else {
            assert(began && sets==1 && configs==1 && reads==1 && register_writes==1);
            assert(p4_c6_guard_check("before-operation"));
            if(scenario==15)assert(!p4_c6_guard_begin());
            if(scenario>=16 && scenario<=20) {
                static const unsigned late[]={READ_ERROR,HIGH_PAD,BAD_MUX,INPUT_OFF,OUTPUT_OFF};
                fault=late[scenario-16];assert(!p4_c6_guard_check("after-operation"));
            }
            if(scenario==21)set_error=-8;
            if(scenario==22)config_error=-9;
            if(scenario==23)fault=READ_ERROR;
            if(scenario==25) {
                fault=HIGH_PAD;assert(!p4_c6_guard_check(NULL));
                fault=GOOD;unsigned old=reads;
                assert(!p4_c6_guard_check(NULL) && reads==old); // No repair/continue.
            }
        }
    }
    p4_c6_guard_before_abort();
    unsigned old_sets=sets,old_configs=configs,old_reads=reads;
    assert(!p4_c6_guard_check(NULL));
    fault=GOOD;set_error=config_error=0;
    assert(!p4_c6_guard_begin());
    p4_c6_guard_before_abort();
    assert(sets==old_sets && configs==old_configs && reads==old_reads);
    printf("guard_case=%u PASS set0=%u configIO=%u read=%u no_release sticky_failed\n",
        scenario,sets,configs,reads);
}
int main(void) {
    for(unsigned scenario=0;scenario<27;scenario++) {
        pid_t child=fork();assert(child>=0);
        if(!child) {one(scenario);fflush(stdout);_Exit(0);}
        int status;assert(waitpid(child,&status,0)==child);
        assert(WIFEXITED(status) && WEXITSTATUS(status)==0);
    }
    puts("27 real-helper GPIO-stub cases PASS; no hardware/RF/reset-continuity claim");
}
