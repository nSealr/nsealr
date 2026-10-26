// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
// Diagnostic pattern and accidental-corruption checksum only, never a secret,
// cryptographic proof, authentication mechanism or full-memory erase test.
struct PublicMarker { uint32_t words[16]; };
static_assert(sizeof(PublicMarker)==64,"bounded public marker");
inline uint32_t marker_checksum(const PublicMarker &m) {
    uint32_t sum=0x5042554c;
    for(unsigned i=0;i<15;++i)sum=((sum<<5)|(sum>>27))^m.words[i];
    return sum;
}
inline PublicMarker public_marker(uint32_t generation) {
    PublicMarker m={};m.words[0]=0x53334f54;m.words[1]=1;m.words[2]=generation;
    for(unsigned i=3;i<15;++i)m.words[i]=0x5055424cU^(i*0x01010101U)^generation;
    m.words[15]=marker_checksum(m);return m;
}
inline bool marker_valid(const PublicMarker &m) {
    if(m.words[0]!=0x53334f54||m.words[1]!=1||m.words[2]==0||m.words[15]!=marker_checksum(m))return false;
    const auto expected=public_marker(m.words[2]);
    for(unsigned i=0;i<16;++i)if(m.words[i]!=expected.words[i])return false;
    return true;
}
