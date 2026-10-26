# stone/moonstone daily profile

This remains Linux 5.4.304, using the existing device-specific Qualcomm/Xiaomi
sources. The experimental peripheral expansion from 132e475606fb is removed.
The imported RTL8821CU driver and its Kbuild integration are removed entirely.
HID/MIDI/mass-storage gadgets, network filesystems and container additions are
also disabled. Existing ADB/MTP, phone hardware drivers and built-in USB support
from the pre-expansion baseline are retained.

Keep the KernelSU branch-link hook fix, ARM64 mitigations, SELinux, thermal/BCL
protections, pstore, schedutil, CPU idle, ThinLTO and zram/writeback. Keep test
USB controllers, thermal emulation and Simple LMK disabled. Do not change CPU/GPU
frequencies, voltages, charging limits or thermal trip points without device data.

Disable ZRAM_MEMORY_TRACKING. In this source, this removes the per-slot ktime_t
and its timestamp update; the non-tracking zram_accessed() still clears ZRAM_IDLE.
With ARM64 and 4 KiB pages, the table uses 8 fewer bytes per logical page (about
2 MiB per GiB of configured zram). This is a source-level overhead reduction,
not evidence of measured battery life or application-speed gains.

## Linux 6.x status

No validated 6.x device port or compatible ROM/vendor integration was established
for this checkout. An announcement of SingkoKernel 6.1.167 dated April 1, 2026
was found, but its download points to a Telegram contact/message and does not
provide inspectable source code. Do not treat that announcement as port evidence.

A genuine move requires a maintained 6.x baseline and porting/auditing the SM6375
board DTs and vendor interfaces: display/touch, camera, audio, GPU, WLAN/BT,
modem/IPA, storage, charging, thermal and suspend/resume. The existing Android
vendor binaries, boot layout and KernelSU integration must be checked against
that port. GKI compatibility within an LTS does not provide cross-LTS driver
compatibility. Changing VERSION/PATCHLEVEL or FAKE_UNAME is not a port.
The pre-existing FAKE_UNAME compatibility setting is unchanged.

References checked during preparation:
- https://source.android.com/docs/core/architecture/kernel/android-common
- https://source.android.com/docs/core/architecture/kernel/generic-kernel-image
- https://t.me/s/PocoX5IDUpdates/726 (unverified announcement)
- https://t.me/singkokranul/2 (announcement download target)

## Validation boundary

Host configuration/build/package checks cannot establish phone stability.
Before promotion, test boot, root, calls/mobile data, Wi-Fi/BT, camera/audio,
charging, suspend/resume and standby/load consumption against the same ROM and
baseline. Preserve the known working boot/DTBO and recovery route. No device is
flashed by the build tools.
