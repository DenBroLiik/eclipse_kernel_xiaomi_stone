# Network queue default: FQ with the existing BBR profile

The stone defconfig now selects NET_SCH_DEFAULT and DEFAULT_FQ. After
olddefconfig, DEFAULT_NET_SCH must be "fq", NET_SCH_FQ must be built in,
and the existing DEFAULT_TCP_CONG remains "bbr". The builder verifies this
combination in the final configuration. No traffic-control parameters,
modem limits, radio settings, MTU, receive windows or transmit power are
hardcoded for a particular operator or connection speed.

Previously FQ was compiled in but was not selected as the default, so the
kernel default remained pfifo_fast unless userspace changed it. FQ separates
flows and supports socket pacing / TCP earliest-departure timestamps. This
is a candidate improvement for concurrent locally generated traffic when a
transmit queue builds up. It is not an assertion that BBR cannot work with
pfifo_fast: TCP has fallback pacing in this kernel generation.

The default applies to eligible newly attached queues on all interfaces,
including leaves of mq; it is not limited to the mobile interface. Noqueue
devices and explicitly configured qdiscs are not replaced. Android/vendor
userspace may override the default or replace individual queues; inspect
`tc -s qdisc show` and net.core.default_qdisc on the running target to confirm.
No active phone queues are changed by the build tools.

FQ is not FQ-CoDel/CAKE active queue management and does not control queues
inside the modem, base station, operator network or remote download server.
BBR on the phone governs its own TCP sending, not the remote sender's
congestion algorithm or QUIC/UDP. Downlink speed and unloaded ping are not
guaranteed to improve. FQ has extra per-flow state and pacing overhead
relative to FIFO, and its scheduling differs from FIFO's three priority
bands. Hardware testing is required for CPU/memory, throughput and latency
tradeoffs under load. No universal bandwidth cap is imposed on variable LTE.

Validation: compare final .config against the saved baseline, pass the
configuration regression gates, and build complete ARM64 Image/DT artifacts.
These host checks are not phone performance measurements. Before calling
the behavior improved, boot the matching candidate and compare idle/loaded
RTT, loss, uplink/downlink throughput and call concurrency in repeatable
conditions with the previous build.

References:
- net/sched/Kconfig, sch_api.c, sch_generic.c, sch_fq.c in this tree
- https://github.com/google/bbr/blob/master/Documentation/bbr-quick-start.md
- https://www.kernel.org/doc/html/latest/admin-guide/sysctl/net.html

Rollback: remove NET_SCH_DEFAULT and DEFAULT_FQ from stone_defconfig and
rebuild the ordinary profile. Do not flash an unrelated ZFS/module build.
