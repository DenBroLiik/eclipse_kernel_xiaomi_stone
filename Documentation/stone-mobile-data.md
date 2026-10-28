# Mobile data: RMNET uplink aggregation corrections

The stone build links `techpack/datarmnet/core/rmnet_map_data.o` and the
Qualcomm IPA driver. These changes target that existing path; the unrelated
upstream RMNET driver is not enabled as a substitute.

## Recycled aggregation pages

The recycling cursor previously used `list_next_entry()` even on the final
page. That yields the embedded list sentinel, not an `rmnet_agg_page`, and the
next call can read unrelated memory as a page pointer. Wrap to the first real
entry at the end of the list, including a single-page pool. Keep the six-page
search bound, but stop after a complete circuit of a smaller pool. Busy pages
remain owned by their current users; fallback allocation and its failure
behavior are unchanged. Recycling must be enabled by the existing vendor
configuration for this correction to affect traffic.

## Aggregation intervals

Use `ktime_get_ts64()` for both last-packet and aggregation-start timestamps,
matching the existing CLOCK_MONOTONIC flush timer. Wall-clock synchronization
or manual date changes must not change sparse-traffic bypass decisions or
packet-age checks. Aggregation size, packet-count limits, flush timer values,
priority bypass, modem power management, APNs and radio settings are unchanged.

## Validation and limits

`python3 tests/test-rmnet-aggregation.py` in the builder repository compiles the
actual modified functions with host page, packet, lock and clock stubs. It
covers empty/single/multiple pools, repeated wraparound, busy pages, a
last-to-first reuse, allocation failure, bounded searches, sparse bypass,
wall-clock rollback/advance and ordinary age-based flushing. These are logic
tests, not real concurrency, modem or throughput measurements.

Run the full ARM64 build through `tools/build-stone.sh` and verify SOURCE-ID
and SHA256SUMS before packaging. Device boot, calls, mobile-data speed,
latency, handovers and battery impact still need physical-device validation.
These fixes do not change modem firmware, RF calibration, bands or transmit
power and do not guarantee a higher operator link rate.
