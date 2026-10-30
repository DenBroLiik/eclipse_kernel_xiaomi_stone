# Network changes reverted at user request (2026-10-30)

The custom RMNET/IPA changes and Qualcomm WLAN scan/coexistence changes
have been restored byte-for-byte to commit 132e475606fb (NEW function).
The explicit NET_SCH_DEFAULT/DEFAULT_FQ selections have been removed from
stone_defconfig, restoring the baseline queue default after olddefconfig.
Existing BBR, compiled-in qdiscs, external adapters and filesystem support
from NEW function are retained. CPU, memory, display and GENI UART changes
are retained, as is the separate Android A2DP audio patch.

Regression tests and documentation requiring the reverted network changes
have been removed. Earlier commits remain in Git history for review.
This rollback changes build sources only. It does not flash the phone or
alter its active mobile-data, Wi-Fi, hotspot, APN, DNS or qdisc settings.
