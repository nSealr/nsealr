// SPDX-License-Identifier: MIT
#pragma once
// Fixed 800x800 decoder configuration. Valid version25 static QR rasters can
// exhaust quirc's254 default regions before the third finder is reached.
#define QUIRC_MAX_REGIONS 1024
// uint16 region pixels need1280000 bytes, plus640000 grayscale, bounded
// region/grid/flood metadata. This retained-payload quota excludes allocation
// headers/heap bookkeeping. No QR chooses these sizes.
#define P4_QUIRC_ALLOCATION_LIMIT 2100000U
