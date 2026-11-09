#include "device.h"

#include "ff.h"

#include "diskio_sdmmc.h"
#include "driver/sdmmc_host.h"
#include "esp_memory_utils.h"
#include "esp_vfs_fat.h"
#include "sd_pwr_ctrl_by_on_chip_ldo.h"
#include <stdio.h>
#include <string.h>

#if !FF_FS_TINY || FF_USE_DYN_BUFFER
#error Share files require the single explicit, non-dynamic FatFs sector window
#endif

/* Same physical slot 0 / LDO4 as the Waveshare BSP. This owner also releases
 * the LDO on a failed mount; the BSP convenience function does not retain it. */
static share_file_result transfer(bool save, const uint8_t *input, size_t length, uint8_t *output,
                                  size_t capacity, size_t *written) {
    sd_pwr_ctrl_handle_t power = NULL;
    sdmmc_card_t *card = NULL;
    FATFS *filesystem = NULL;
    FIL file = {0};
    uint8_t check[64] = {0};
    bool opened = false, created = false;
    share_file_result result = SHARE_FILE_UNAVAILABLE;
    sd_pwr_ctrl_ldo_config_t ldo = {.ldo_chan_id = 4};
    if (sd_pwr_ctrl_new_on_chip_ldo(&ldo, &power) != ESP_OK)
        return result;
    sdmmc_host_t host = SDMMC_HOST_DEFAULT();
    host.slot = SDMMC_HOST_SLOT_0;
    host.pwr_ctrl_handle = power;
    sdmmc_slot_config_t slot = SDMMC_SLOT_CONFIG_DEFAULT();
    slot.width = 4;
    const esp_vfs_fat_mount_config_t mount = {
        .format_if_mount_failed = false, .max_files = 1, .disk_status_check_enable = true};
    if (esp_vfs_fat_sdmmc_mount("/share", &host, &slot, &mount, &card) != ESP_OK)
        goto cleanup;
    BYTE drive = ff_diskio_get_pdrv_card(card);
    if (drive > 9) {
        result = SHARE_FILE_IO;
        goto cleanup;
    }
    char path[] = "0:/NSEALR.NSR";
    path[0] = (char)('0' + drive);
    FRESULT status = f_open(&file, path, save ? FA_CREATE_NEW | FA_WRITE | FA_READ : FA_READ);
    if (status != FR_OK) {
        result = status == FR_EXIST     ? SHARE_FILE_EXISTS
                 : status == FR_NO_FILE ? SHARE_FILE_MISSING
                                        : SHARE_FILE_IO;
        goto cleanup;
    }
    opened = true;
    created = save;
    filesystem = file.obj.fs;
    result = SHARE_FILE_IO;
    /* Default malloc may fall back to PSRAM. Refuse before private I/O. */
    if (!esp_ptr_internal(filesystem->win) || !esp_ptr_internal(filesystem->win + FF_MAX_SS - 1))
        goto cleanup;
    UINT count;
    if (save) {
        if (f_write(&file, input, (UINT)length, &count) != FR_OK || count != length ||
            f_sync(&file) != FR_OK)
            goto cleanup;
        platform_wipe(filesystem->win, FF_MAX_SS);
        filesystem->winsect = (LBA_t)-1;
        if (f_lseek(&file, 0) != FR_OK)
            goto cleanup;
        unsigned difference = 0;
        for (size_t offset = 0; offset < length;) {
            UINT chunk = (UINT)(length - offset < sizeof(check) ? length - offset : sizeof(check));
            if (f_read(&file, check, chunk, &count) != FR_OK || count != chunk)
                goto cleanup;
            for (UINT i = 0; i < count; i++)
                difference |= check[i] ^ input[offset + i];
            offset += count;
            platform_wipe(check, sizeof(check));
        }
        if (difference)
            goto cleanup;
    } else {
        length = (size_t)f_size(&file);
        if (!length || length > capacity || length > NS_THRESHOLD_MAX_BACKUP) {
            result = SHARE_FILE_INVALID;
            goto cleanup;
        }
        if (f_read(&file, output, (UINT)length, &count) != FR_OK || count != length)
            goto cleanup;
        *written = length;
    }
    result = SHARE_FILE_OK;
cleanup:
    if (opened && f_close(&file) != FR_OK)
        result = SHARE_FILE_IO;
    if (created && result != SHARE_FILE_OK)
        (void)f_unlink(path);
    platform_wipe(check, sizeof(check));
    platform_wipe(&file, sizeof(file));
    /* No other owner uses this mounted volume. Close has already synchronized
     * it; unmount does not need cached file data, including after an I/O error. */
    if (filesystem)
        platform_wipe(filesystem->win, FF_MAX_SS);
    if (card && esp_vfs_fat_sdcard_unmount("/share", card) != ESP_OK)
        platform_fail();
    if (sd_pwr_ctrl_del_on_chip_ldo(power) != ESP_OK)
        platform_fail();
    return result;
}

share_file_result platform_share_save(const uint8_t *bytes, size_t len) {
    if (!bytes || !len || len > NS_THRESHOLD_MAX_BACKUP)
        return SHARE_FILE_INVALID;
    return transfer(true, bytes, len, NULL, 0, NULL);
}
share_file_result platform_share_load(uint8_t *bytes, size_t capacity, size_t *written) {
    *written = 0;
    platform_wipe(bytes, capacity);
    share_file_result result = transfer(false, NULL, 0, bytes, capacity, written);
    if (result != SHARE_FILE_OK) {
        platform_wipe(bytes, capacity);
        *written = 0;
    }
    return result;
}
