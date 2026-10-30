# stone/moonstone daily profile

This remains Linux 5.4.304, using the existing device-specific Qualcomm/Xiaomi
sources. At the user's request on 2026-10-27, restore the peripheral expansion
from `132e475606fb` (NEW function), including RTL8821CU and its Kbuild integration,
external USB Wi-Fi/Bluetooth/serial/modem support, HID/MIDI/mass-storage gadgets,
network filesystems and PID/IPC namespaces. MEMCG and USER_NS remain disabled.
The earlier daily profile remains available in commit `e2d657bc18de`.

Keep the KernelSU branch-link hook fix, ARM64 mitigations, SELinux, thermal/BCL
protections, pstore, schedutil, CPU idle, ThinLTO and zram/writeback. Keep test
USB controllers, thermal emulation and Simple LMK disabled. Do not change CPU/GPU
frequencies, voltages, charging limits or thermal trip points without device data.

Disable ZRAM_MEMORY_TRACKING. In this source, this removes the per-slot ktime_t
and its timestamp update; the non-tracking zram_accessed() still clears ZRAM_IDLE.
With ARM64 and 4 KiB pages, the table uses 8 fewer bytes per logical page (about
2 MiB per GiB of configured zram). This is a source-level overhead reduction,
not evidence of measured battery life or application-speed gains.

## CPU frequency corrections (2026-10-27)

- Cache the resolved frequency separately from the committed request. Previously
  a directionally rate-limited request poisoned the raw-frequency cache: a later
  identical utilization request returned the old committed frequency indefinitely.
  This affected both ramp-up and ramp-down, including idle requests with raw zero.
- Retain need_freq_update until commit, bypass directional delays for policy-limit
  changes, and resolve the first request after governor start. The fast limits
  callback marks its immediate request forced as well.
  A forced update deferred by a shared-policy CONTINUE callback remains eligible
  at the next callback instead of being blocked by the minimum interval.
- Resolve the lower frequency-table step again when the local <20% rounding rule
  selects it. Qualcomm fast switch consumes policy->cached_resolved_idx, so merely
  returning the lower frequency previously left it using the higher table index.
- Preserve iowait_boost_enable on governor exit/reinit. Restore rate delays in
  nanoseconds consistently (start also initializes them before callbacks run).
  Default rates, boost settings, frequencies and voltages are unchanged.
- Pass display->drm_conn to the dimlayer sysfs backlight callback instead of
  evaluating an uninitialized local connector pointer. The current backlight
  implementation does not dereference that argument; this removes undefined
  input and its compiler warning without changing brightness policy.

Host regressions compile the actual decision functions against small API stubs:

```
python3 tools/testing/selftests/cpufreq/sugov-regression.py
```

These do not test scheduler concurrency or device boot.

## Linux 6.x status

### Selected 6.18 memory-management backports (2026-10-27)

The daily 5.4 tree now adapts two narrowly scoped behaviours from ACK 6.18.33
(`182172ddb27b1e99ab3f2e3a511fa14643e9c6a7`):

- Page-sized zstd workspaces, following `drivers/block/zram/backend_zstd.c`.
  Zram still exposes algorithm `zstd` and uses compression level 3. Internally,
  its Crypto API transform is `zstd-zram`, configured with
  `zstd_get_params(3, PAGE_SIZE)`. General `zstd` and its scomp interface retain
  unknown-size parameters and accept arbitrary input lengths. The zram profile
  accepts only a full page and rejects decoded lengths different from PAGE_SIZE.
  Parameters are cached at context initialization, not recomputed per operation.
  Compression/decompression do not allocate new memory after initialization.
- Per-pool compaction admission, following `mm/zsmalloc.c`. An atomic flag skips
  duplicate concurrent full-pool compactions while allowing different pools to
  compact independently. The existing 5.4 migration and class-lock implementation
  is retained; the 6.18 allocator is not copied wholesale.

This tree already has zstd 1.5.8, while the reference has 1.5.7; no codec downgrade
or wholesale replacement was made. Tests compile this tree's actual 1.5.8 codec
and Crypto API helper bodies on the host with allocator/platform stubs, ASan and
UBSan. At 4 KiB PAGE_SIZE, compression workspace bounds are 1,303,568 bytes for
unknown-size level 3 and 90,128 bytes for page-sized level 3: 1,213,440 bytes less
per stream (~9.26 MiB for eight streams). These are workspace bounds, not a
measurement of free RAM on the phone. Decompression workspace is unchanged.

Tests cover cross-profile decoding, malformed/truncated/wrong-size frames,
initialization allocation failures, registration unwind, no hot-path allocation,
and actual zs_compact admission with concurrent host threads and C11 atomics.
Host tests cannot validate kernel reclaim concurrency, phone latency, memory
pressure behaviour or battery consumption.

```
python3 ../tests/test-zstd-zram.py
python3 ../tests/test-zsmalloc-compaction.py
```

MGLRU, folio-based MM, DAMON and modern memcg are not enabled by pretending they
are configuration toggles. This tree's incomplete memcg integration and vendor
MM dependencies require a separate audited port before those can be considered.

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
