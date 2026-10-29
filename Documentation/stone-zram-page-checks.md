# Zram page checks: bounded fast rejection and decode validation

## Repeated-word detection

Before scanning every word, compare the first and last words of the page.
If they differ, the page cannot use zram's repeated-word representation and
can proceed directly to compression. Otherwise inspect every interior word,
preserving detection of repeated nonzero words as well as zero pages. The
output element is still written only on success. This follows the approach
in the Android common kernel's page_same_filled implementation:

https://android.googlesource.com/kernel/common/+/40d1642f435a391bef01ea4dfbeec373efeab293/drivers/block/zram/zram_drv.c

This particularly helps pages with a long matching prefix but different tail.
It does not change page contents, compressor choice, compression level,
swap limits, allocation, locking or writeback policy.

## Full-page decode validation

The Crypto API returns both a status and the number of bytes decompressed.
LZ4 and other general-purpose decompressors can legitimately report success
for a stream which expands to fewer than PAGE_SIZE bytes. For a zram slot,
however, the original object is a full page. Ignoring the output length would
accept an incompletely restored destination as a successful read.

After a successful backend call, require dst_len == PAGE_SIZE and return
-EIO otherwise. Preserve existing backend errors. This uses the existing
zram read error path and performs no additional allocation or copying.
The page-specific zstd backend already rejects non-page results; this adds
the invariant for other codecs at the shared zcomp boundary as well.
It is not a checksum and cannot detect every form of memory corruption.

## Host validation and limits

From the builder repository:

```
python3 tests/test-zram-page-checks.py
```

The test compiles the actual changed functions with ASan/UBSan and checks
4 KiB, 16 KiB and 64 KiB page sizes, several repeated-word patterns, every
mismatch word position, untouched output on mismatch, full/short/oversized
decode lengths and unchanged propagation of backend errors. Decode fault
injection uses a stub backend, not a fault induced in the phone's RAM.
The unmodified zcomp function fails the short-decode test.

An optional host benchmark compares the actual old and new page-check bodies:

```
git -C kernel show 89c960d46530:drivers/block/zram/zram_drv.c > validation/zram-page-baseline.c
python3 tests/test-zram-page-checks.py --benchmark --baseline validation/zram-page-baseline.c
```

On one x86 host, five alternating runs over synthetic 4 KiB pages measured
about 145-178 ns versus 1.7-2.0 ns per check for matching-prefix/different-tail
pages. Early mismatches were about 1.7-2.0 ns with either implementation;
uniform pages were about 146-150 ns with either implementation. These are
microbenchmarks of one predicate, not swap throughput, app latency, ARM64
performance or battery-life results. The frequency of such pages on the phone
has not been measured.

The inspected phone on 2026-10-29 selected LZ4 and showed no zram read/write
errors at the baseline snapshot. No active swap, codec, audio, radio, CPU,
thermal or partition setting was changed. Build and regression validation
do not substitute for boot, suspend or memory-pressure testing on the device.
