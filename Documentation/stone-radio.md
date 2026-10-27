# stone/moonstone scan and coexistence corrections

These corrections address source-level request ordering and state handling.
They do not replace Qualcomm firmware or prove the reported audio and tethering
stalls fixed on hardware. No device settings are changed by the build.

## Final scan policy, not an intermediate helper result

`scm_req_update_concurrency_params()` previously set a client-preserving 2.4 GHz
dwell limit and then overwrote it with the SAP ACS default of 40 ms. The default
now precedes the limit. An AP without clients keeps its original ACS default.

The AP has a pre-existing CTS-to-self budget: 32 ms minus 4 ms for channel
switching, hence a 28 ms dwell ceiling. Previously generic active dwell was
capped for 5/6 GHz APs on DBS-capable hardware but not on non-DBS hardware.
Non-DBS APs with clients now receive the same ceiling for generic active dwell.
The NDI default is applied before AP constraints so that its 60 ms setting cannot
overwrite them. Existing per-band DBS exceptions remain: this does not blindly
cap scanning on an independent radio.

The existing Bluetooth passive-dwell limiter, used within active scans, now runs
after all AP/NDI defaults. Otherwise AP code could overwrite its 28 ms result.
The standalone helper test did not detect this overwrite; a new test executes
the entire concurrency-policy function. Explicit passive-scan flags, channel
lists, country/DFS restrictions and transmit power are not changed. The AP's
existing passive-dwell override can become shorter because it copies the newly
bounded active dwell; this is not a guarantee of unchanged scan detection rates.

Probe count is calculated after the final active dwell is selected. The
SSID-count x BSSID-count intermediate is now 32-bit; the old 8-bit variable
wrapped e.g. 16 x 16 to zero and selected the wrong probe timing row.

## Retryable BTC chain-mode commands

`__wlan_cfg80211_coex_set_btc_chain_mode()` previously committed the new mode to
the host cache before sending it to firmware. A send failure therefore left the
new cached mode behind and a repeated request returned -EALREADY. It could also
restart the first interface before a later send failed.

The routine now sends commands first, commits the host mode only after all
sends succeed, and then performs requested interface restarts. A failed send
leaves the old host mode so the request can be retried, and triggers no restarts.
This does not provide atomic firmware rollback: some interfaces may already
have accepted the command when another fails. Their state converges on a retry.
The existing same-mode -EALREADY behaviour after a successful update is retained.

## Verification

From the builder root:

```
python3 tests/test-wlan-concurrency.py
python3 tests/test-btc-chain-mode.py
python3 kernel/tools/testing/selftests/net/wlan-coex-regression.py
```

Tests compile actual decision functions with object-manager/firmware API stubs
and ASan/UBSan (the earlier small helper test uses UBSan). The full-policy test
covers 192 combinations of 2.4 GHz/non-DFS 5 GHz/DFS 5 GHz AP, DBS capability,
Bluetooth audio, client presence, request mode, NDI and explicit passive scans.
It verifies final dwell limits and probe accounting, not just helper values.
BTC tests inject send/get/set failures, retry the same requested mode and verify
that restarts occur only after command completion and host-state commit.

These tests do not validate firmware execution, regulatory scanning success,
object lifetime under concurrent kernel operations, RF packet loss or audio.
Existing live measurements on the previous phone kernel showed A2DP-associated
local tethering latency; repeat comparable tests after an authorized installation.
