# stone/moonstone CPU and memory iteration

## Low-power control

With CONFIG_DRM_PANEL=y the previous lpm-levels code initialized sleep_disabled
to true and exposed the parameter as read-only (0444). Its panel notifier was
static and never registered anywhere in the translation unit, so it could not
restore idle on a display notification. On the inspected phone the boot command
line also explicitly specified lpm_levels.sleep_disabled=1; C1/C2 usage was zero.

Restore the existing non-panel behaviour: a normal boolean module parameter with
0664 permissions, no unregistered panel callback and no DRM dependency. Explicit
boot arguments still apply. This permits the privileged vendor post-boot/power
policy to write N; it does not ignore the boot prohibition or force a power state.
The reference sm6375-common post-boot script contains that write. Its exact
installed path/execution on this ROM has not been established.

Idle governor selection, deadlines, QoS and PSCI implementation are unchanged.
Whether deep idle is enabled after boot still depends on userspace policy.
Suspend/resume and actual power consumption need device validation after install.

## Less parameter setup in zstd zram compression

The page-sized zstd profile already caches level-3 parameters and workspaces.
Previously zstd_compress_cctx() nevertheless reset all parameters and set every
constant option again for each page. The page-sized transform now uses that full
path for its first successful compression and a new reuse wrapper thereafter.

The wrapper resets only the session and sets the source-size pledge, then emits
a new independent frame. It preserves parameters, not previous page history.
If compression fails, the crypto profile invalidates the ready flag so the next
request performs full configuration again. Non-page general-purpose zstd keeps
its prior path. Buffers, algorithm, level, dictionary behaviour and input-size
validation remain as in the preceding iteration; there is no hot-path allocation.

Host tests compile the actual kernel zstd sources with ASan/UBSan and verify
decoding with freshly initialized decoders, cross-profile round trips, malformed
input, small output, recovery after failure and allocation cleanup. They do not
replace ARM64 execution or memory-pressure testing on the phone.

A separate non-sanitized host benchmark compares full setup with session reuse
for 100,000 independent 4 KiB pages over a fixed synthetic corpus per run.
Five runs alternate order. The measured reduction was 3.21-5.40% of compression
time, not of application latency or total phone CPU use. The corpus is not a
capture of real phone RAM and cannot establish a battery or compression-ratio
improvement. Run from the builder root:

```
python3 tests/test-lpm-control.py
python3 tests/test-zstd-zram.py
python3 tests/test-zstd-zram.py --benchmark
```

No frequency, voltage, charging, thermal, active network, audio codec or Dolby
setting is changed by these source edits or the build.
