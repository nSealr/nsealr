# Source provenance

Board pin constants and the revised ST7789 command table come from
Xinyuan-LilyGO/T-Display-S3 commit
`1cc41eb1c76b2f3215130a3dd64e7138ce00b482`,
`examples/tft/pin_config.h` and `examples/tft/tft.ino`.
The original MIT notice is retained in `LICENSE-LilyGO`.
The pins describe the vendor source, not a measurement of the sample.

The build uses that same repository's TFT_eSPI 2.5.43 with Setup206.
Its license (FreeBSD, plus original font notices) stays in the selected external
source closure and the flash packet. No floating library-manager replacement
is admitted. Use the source-selection manifest captured by the initial vendor
build under the S3 probe root.
