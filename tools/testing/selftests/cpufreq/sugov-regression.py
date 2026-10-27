#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Host-only schedutil regressions; compile actual functions with CPUFreq stubs.

Run directly with Python 3 and a host C compiler. Optional argument: alternate
cpufreq_schedutil.c (e.g. the baseline). No sysfs or device access is performed.
This checks decision logic, not scheduler concurrency or hardware behaviour.
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[4]
source = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "kernel/sched/cpufreq_schedutil.c"
code = source.read_text()


def function(name):
    match = re.search(r"^static [^;{}]*\b" + name + r"\([^;{}]*\)\n\{", code, re.M)
    if not match:
        raise RuntimeError("Function missing: " + name)
    start = code.index("{", match.start())
    depth = 1
    end = start + 1
    while depth:
        depth += (code[end] == "{") - (code[end] == "}")
        end += 1
    return code[match.start():end]


def structure(name):
    return re.search(r"struct " + name + r" \{.*?\n\};", code, re.S).group()


prefix = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
typedef uint64_t u64;
typedef int64_t s64;
typedef int raw_spinlock_t;
struct gov_attr_set { int unused; };
struct list_head { int unused; };
struct irq_work { int unused; };
struct kthread_work { int unused; };
struct mutex { int unused; };
struct kthread_worker { int unused; };
struct cpufreq_frequency_table { unsigned int frequency; };
struct cpufreq_policy {
    struct { unsigned int max_freq; } cpuinfo;
    unsigned int cpu, cur, min, max, related_cpus;
    int cached_resolved_idx;
    struct cpufreq_frequency_table *freq_table;
    void *governor_data;
};
#define unlikely(x) (x)
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x, y) ((x) = (y))
#define smp_mb() ((void)0)
#define min(a, b) ((a) < (b) ? (a) : (b))
#define clamp(x, lo, hi) ((x) < (lo) ? (lo) : ((x) > (hi) ? (hi) : (x)))
#define mult_frac(x, n, d) ((unsigned long)(x) * (n) / (d))
#define NSEC_PER_USEC 1000L
#define GFP_KERNEL 0
#define kzalloc(size, flags) calloc(1, size)
#define per_cpu(array, cpu) ((array)[cpu])
#define for_each_cpu(cpu, mask) for ((cpu) = 0; (cpu) < 8; (cpu)++) if ((mask) & (1U << (cpu)))
#define DEFINE_MUTEX(name) int name
#define mutex_lock(x) ((void)(x))
#define mutex_unlock(x) ((void)(x))
#define CPUFREQ_RELATION_H 1
#define trace_android_vh_map_util_freq(...) ((void)0)
#define trace_sugov_next_freq(...) ((void)0)
static bool can_update = true;
static bool cpufreq_this_cpu_can_update(struct cpufreq_policy *p) { (void)p; return can_update; }
static bool arch_scale_freq_invariant(void) { return true; }
static bool have_governor_per_policy(void) { return true; }
/* Deterministic utilization mapping; the tested code does the table rounding. */
static unsigned int map_util_freq(unsigned long u, unsigned int f, unsigned long m) { return u * f / m; }
static int cpufreq_frequency_table_target(struct cpufreq_policy *p, unsigned int f, int relation)
{
    int i = 0;
    (void)relation;
    while (i < 3 && p->freq_table[i + 1].frequency <= f) i++;
    return i;
}
static unsigned int cpufreq_driver_resolve_freq(struct cpufreq_policy *p, unsigned int f)
{
    int i = 0;
    f = clamp(f, p->min, p->max);
    while (i < 3 && p->freq_table[i].frequency < f) i++;
    p->cached_resolved_idx = i;
    return p->freq_table[i].frequency;
}
'''

tests = r'''
static unsigned int failures;
#define CHECK(expr) do { if (!(expr)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #expr); failures++; } } while (0)
int main(void)
{
    struct cpufreq_frequency_table table[] = {{300}, {600}, {900}, {1200}};
    struct cpufreq_policy p = { .cpuinfo = {1200}, .cur = 600, .min = 300, .max = 1200,
                                .related_cpus = 3, .freq_table = table };
    struct sugov_tunables t = {0};
    struct sugov_policy s = { .policy = &p, .tunables = &t, .next_freq = 600,
                             .last_freq_update_time = 1000, .up_rate_delay_ns = 1000,
                             .down_rate_delay_ns = 1000, .min_rate_limit_ns = 0 };
    p.governor_data = &s;
    /* A rejected up request must be retried even if utilization stays constant. */
    CHECK(!sugov_update_next_freq(&s, 1100, get_next_freq(&s, 900, 1200)));
    CHECK(sugov_update_next_freq(&s, 2100, get_next_freq(&s, 900, 1200)));
    CHECK(s.next_freq == 900);
    /* Same regression for down requests, including raw zero (idle). */
    s.next_freq = 900; s.last_freq_update_time = 3000;
    CHECK(!sugov_update_next_freq(&s, 3100, get_next_freq(&s, 0, 1200)));
    CHECK(sugov_update_next_freq(&s, 4100, get_next_freq(&s, 0, 1200)));
    CHECK(s.next_freq == 300);
    CHECK(!sugov_update_next_freq(&s, 5100, get_next_freq(&s, 0, 1200)));
    /* New thermal ceiling and minimum must override both directional delays. */
    s.next_freq = 1200; s.last_freq_update_time = 6000;
    p.max = 600; s.limits_changed = true;
    CHECK(sugov_should_update_freq(&s, 6100));
    CHECK(sugov_update_next_freq(&s, 6100, get_next_freq(&s, 1200, 1200)));
    CHECK(s.next_freq == 600 && !s.need_freq_update);
    p.max = 1200; p.min = 900; s.limits_changed = true;
    CHECK(sugov_should_update_freq(&s, 6200));
    CHECK(sugov_update_next_freq(&s, 6200, get_next_freq(&s, 0, 1200)));
    CHECK(s.next_freq == 900 && !s.need_freq_update);
    /* Ordinary requests still obey the minimum interval and CPU locality. */
    s.min_rate_limit_ns = 1000;
    CHECK(!sugov_should_update_freq(&s, 6300));
    /* A CONTINUE callback may leave a forced update pending for the next CPU. */
    s.need_freq_update = true;
    CHECK(sugov_should_update_freq(&s, 6300));
    s.need_freq_update = false;
    can_update = false; s.limits_changed = true;
    CHECK(!sugov_should_update_freq(&s, 9000) && s.limits_changed);
    can_update = true;
    /* Qualcomm fast switch consumes cached_resolved_idx, not the argument. */
    p.min = 300; s.need_freq_update = true;
    CHECK(get_next_freq(&s, 630, 1200) == 600);
    CHECK(table[p.cached_resolved_idx].frequency == 600);
    s.need_freq_update = true;
    CHECK(get_next_freq(&s, 660, 1200) == 900);
    CHECK(table[p.cached_resolved_idx].frequency == 900);
    /* Preserve both settings of I/O boost across governor exit/reinit. */
    for (unsigned int enabled = 0; enabled < 2; enabled++) {
        t.iowait_boost_enable = enabled;
        t.up_rate_limit_us = 1234; t.down_rate_limit_us = 5678;
        sugov_tunables_save(&p, &t);
        t.iowait_boost_enable = !enabled;
        t.up_rate_limit_us = t.down_rate_limit_us = 0;
        sugov_tunables_restore(&p);
        CHECK(t.iowait_boost_enable == enabled);
        CHECK(t.up_rate_limit_us == 1234 && t.down_rate_limit_us == 5678);
        CHECK(s.up_rate_delay_ns == 1234000 && s.down_rate_delay_ns == 5678000);
    }
    free(cached_tunables[0]);
    if (failures) { fprintf(stderr, "%u failed assertions\n", failures); return 1; }
    puts("PASS: schedutil retry, idle, policy limits, driver index and tunable restore");
    return 0;
}
'''

harness = prefix + structure("sugov_tunables") + structure("sugov_policy")
harness += "\nstatic struct sugov_tunables *cached_tunables[8];\n"
for name in ("sugov_should_update_freq", "sugov_up_down_rate_limit",
             "sugov_update_next_freq", "get_next_freq", "update_min_rate_limit_ns",
             "sugov_tunables_save", "sugov_tunables_restore"):
    if name == "update_min_rate_limit_ns":
        harness += "\nstatic DEFINE_MUTEX(min_rate_lock);\n"
    harness += "\n" + function(name) + "\n"
harness += tests
with tempfile.TemporaryDirectory(prefix="sugov-test-") as work:
    cfile = Path(work) / "test.c"
    binary = Path(work) / "test"
    cfile.write_text(harness)
    subprocess.run([os.environ.get("HOSTCC", "cc"), "-std=gnu11", "-Wall", "-Wextra",
                    "-Werror", "-fsanitize=undefined", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
