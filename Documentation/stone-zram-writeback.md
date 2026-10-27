# Zram metadata and writeback allocation corrections

## Protected metadata snapshots

idle_store(), writeback_store() and the optional memory-tracking reader now take
their disksize/page-count snapshot after acquiring init_lock and validating the
initialized device. Previously a completed reset/reinitialization before lock
acquisition could leave a cached old page count paired with a smaller new table.
The table walk must use the geometry protected by the same read lock.

The backed-page read path snapshots its backing block number while holding the
slot lock, then unlocks and submits the read using that saved number. Previously
it read the slot element after unlock, allowing replacement metadata to supply
a different value. This change does not introduce a lifetime reference on the
backing block or claim to resolve every possible concurrent read/free issue.

## Next-fit backing block search

The old allocator restarted its free-bit search at block 1 for each page.
Sequentially filling a backing device repeatedly scanned an increasing occupied
prefix. A per-device next_free_block hint now starts the next search after the
last successful allocation and wraps to block 1 if required.

The hint is only a search-order optimization. READ_ONCE/WRITE_ONCE permit stale
hints, and test_and_set_bit remains the ownership operation; concurrent callers
cannot both claim the same occupied bit. Block zero remains reserved, full
bitmaps return failure, freed earlier blocks are found on wraparound, and new
backing-device setup/reset initializes the hint. No on-disk format is changed.
Cost: one unsigned long per zram device with writeback enabled.

Tests compile actual slot and allocator functions with deterministic metadata
interleavings and atomic bitmap/IO stubs under ASan/UBSan. The allocator test
uses four competing writers, then checks full/empty/tiny bitmaps, wraparound,
freed-block reuse and invalid hints. The slot test simulates a resize completed
before init_lock acquisition and slot replacement immediately after unlock.
It also checks decompression error cleanup. These do not run actual storage I/O,
kernel memory-pressure reclaim or a complete backing-block lifetime test.

An optional non-sanitized host benchmark compiles the real kernel find-bit
implementation and compares old/new allocation while filling 65,535 usable
blocks ten times per round, alternating order over five rounds. It measures
the allocator only on a synthetic bitmap, not zram throughput, flash latency,
battery consumption or Android application performance.

```
python3 tests/test-zram-block-allocator.py
python3 tests/test-zram-block-allocator.py --benchmark
python3 tests/test-zram-slots.py
```

The allocation optimization is exercised only when a backing device is configured
and writeback is requested. This stage does not enable writeback, change zstd,
alter zram size or write to the phone.
