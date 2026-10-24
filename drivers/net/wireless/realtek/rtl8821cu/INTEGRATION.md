# Stone kernel integration

Source: https://github.com/paralin/8821cu

Pinned revision: `bd2400d313d6209fa2100f1575bfb2c67bb57367`.
Driver version: Realtek v5.12.0.4 with upstream community changes.
License: GPL version 2, see [LICENSE](LICENSE).

Imported source directories: core, hal, include, os_dep and platform, plus
the upstream Makefile, Kconfig, chipset makefiles, README and USB ID list.
No DKMS/install scripts are run or needed for this in-tree build.

Local integration changes:

- Add Kconfig dependencies on USB and cfg80211, and select WEXT_PRIV.
- Register the directory in the parent Realtek Kconfig and Makefile.
- Enable CONFIG_RTL8821CU=y in stone_defconfig.
- Resolve source include paths through $(srctree) for separate output builds.
- Disable build-host platform autodetection; use the enclosing kernel's
  architecture/toolchain and target endianness, with cfg80211 enabled.
- Use compiled-in PHY tables instead of optional files under /lib/firmware.
  Chip firmware is included in hal/rtl8821c/hal8821c_fw.c.
- Namespace the vendor aes_encrypt helper through a driver-local compiler
  definition to avoid colliding with the kernel AES implementation when built in.
- Correct an upstream #elseif typo to #elif in rtw_mlme_ext.h.
- Remove unused packet conversion helpers that used an uninitialized pointer.
- Reject ADDBA requests without a station and initialize their sequence field.
- Initialize scan-back channel settings from the current operating channel.
- Return a zero measurement on TXGAPK failure and abort calibration while
  restoring backed-up registers instead of using an uninitialized measurement.
- Use LED_CTL_POWER_OFF in the LED control API and remove redundant comparisons.

The chipset driver's support claim is distinct from successful compilation,
full kernel linking, boot testing and Android framework integration.
