// SPDX-License-Identifier: MIT
#pragma once
#include "s3_entropy_logic.h"
// These three short policies are shared with the S3 RCC fault tests. The target
// adapter maps each operation directly to the pinned e099 primitive/HAL.
template<class Rcc> S3EntropyStatus s3_entropy_rcc_claim(Rcc &r){
    const auto count=r.acquire_enter();
    if(count!=0||!r.inactive()){r.exit();return S3EntropyStatus::Ownership;}
    r.enable_clock();r.acquire_exit(count);return S3EntropyStatus::PublicDraw;
}
template<class Rcc> S3EntropyStatus s3_entropy_rcc_gate(Rcc &r){
    const auto count=r.acquire_enter();
    if(count!=1){r.exit();return S3EntropyStatus::Ownership;}
    r.enable_clock();r.exit();return S3EntropyStatus::PublicDraw;
}
template<class Rcc> S3EntropyStatus s3_entropy_rcc_release(Rcc &r){
    const auto remaining=r.release_enter();
    if(remaining!=0){r.exit();return S3EntropyStatus::Cleanup;}
    r.disable_clock();r.release_exit(remaining);return S3EntropyStatus::PublicDraw;
}
