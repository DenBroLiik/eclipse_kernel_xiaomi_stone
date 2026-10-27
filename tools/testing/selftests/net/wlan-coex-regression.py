#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Host decision tests using actual WLAN functions, without radio access.

Optional argument: kernel source root (for comparison against a baseline).
The harness stubs object access and policy queries, not the tested logic.
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[4]
staging = root / "drivers/staging"


def function(path, name):
    code = path.read_text()
    match = re.search(r"^(?:static\s+)?void\s+" + name + r"\([^;{}]*\)\n\{", code, re.M)
    if not match:
        raise RuntimeError("Function missing: " + name)
    end = code.index("{", match.start()) + 1
    depth = 1
    while depth:
        depth += (code[end] == "{") - (code[end] == "}")
        end += 1
    return code[match.start():end]


prefix = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
struct wlan_objmgr_psoc { bool bt, sta2g, sap2g, dbs; };
struct wlan_objmgr_vdev { struct wlan_objmgr_psoc *psoc; };
struct scan_start_request { struct { unsigned int dwell_time_passive; } scan_req; };
struct hdd_context { struct wlan_objmgr_psoc *psoc; bool bt_a2dp_active, bt_vo_active; };
typedef struct hdd_context *hdd_handle_t;
enum { WLAN_COEX_EVENT_BT_A2DP_PROFILE_ADD, WLAN_COEX_EVENT_BT_A2DP_PROFILE_REMOVE,
       WLAN_COEX_EVENT_BT_VOICE_PROFILE_ADD, WLAN_COEX_EVENT_BT_VOICE_PROFILE_REMOVE };
#define QDF_MIN(a, b) ((a) < (b) ? (a) : (b))
#define hdd_debug(...) ((void)0)
#define hdd_handle_to_context(h) (h)
#define wlan_hdd_validate_context(h) (!(h))
#define wlan_vdev_get_psoc(v) ((v)->psoc)
#define policy_mgr_is_sta_connected_2g(p) ((p)->sta2g)
#define policy_mgr_is_sap_go_on_2g(p) ((p)->sap2g)
#define policy_mgr_is_hw_dbs_capable(p) ((p)->dbs)
#define ucfg_scan_get_bt_activity(p) ((p)->bt)
#define ucfg_scan_set_bt_activity(p, b) ((p)->bt = (b))
'''
header = (staging / "qca-wifi-host-cmn/umac/scan/core/src/wlan_scan_main.h").read_text()
prefix += re.search(r"^#define PASSIVE_DWELL_TIME_BT_A2DP_ENABLED\s+\d+", header, re.M).group() + "\n"
prefix += function(staging / "qcacld-3.0/core/hdd/src/wlan_hdd_cfg80211.c", "hdd_bt_activity_cb")
prefix += function(staging / "qca-wifi-host-cmn/umac/scan/core/src/wlan_scan_manager.c", "scm_update_passive_dwell_time")
tests = r'''
int main(void)
{
    struct wlan_objmgr_psoc p = {0};
    struct wlan_objmgr_vdev v = {&p};
    struct hdd_context h = {.psoc = &p};
    struct scan_start_request r;
    unsigned int failures = 0;
#define CHECK(expr) do { if (!(expr)) { fprintf(stderr, "FAIL: %s\n", #expr); failures++; } } while (0)
    hdd_bt_activity_cb(&h, WLAN_COEX_EVENT_BT_VOICE_PROFILE_ADD);
    CHECK(p.bt);
    hdd_bt_activity_cb(&h, WLAN_COEX_EVENT_BT_A2DP_PROFILE_ADD);
    hdd_bt_activity_cb(&h, WLAN_COEX_EVENT_BT_A2DP_PROFILE_REMOVE);
    CHECK(p.bt); /* Music ending must not remove protection for ongoing voice. */
    hdd_bt_activity_cb(&h, WLAN_COEX_EVENT_BT_VOICE_PROFILE_REMOVE);
    CHECK(!p.bt);
    hdd_bt_activity_cb(&h, WLAN_COEX_EVENT_BT_A2DP_PROFILE_ADD);
    hdd_bt_activity_cb(&h, WLAN_COEX_EVENT_BT_VOICE_PROFILE_ADD);
    hdd_bt_activity_cb(&h, WLAN_COEX_EVENT_BT_VOICE_PROFILE_REMOVE);
    CHECK(p.bt);
    hdd_bt_activity_cb(&h, 999);
    CHECK(p.bt);
    /* Full matrix: 2.4 GHz STA/AP, DBS capable radio and audio on/off. */
    for (int sta = 0; sta < 2; sta++)
    for (int sap = 0; sap < 2; sap++)
    for (int dbs = 0; dbs < 2; dbs++)
    for (int bt = 0; bt < 2; bt++) {
        p.sta2g = sta; p.sap2g = sap; p.dbs = dbs; p.bt = bt;
        r.scan_req.dwell_time_passive = 110;
        scm_update_passive_dwell_time(&v, &r);
        CHECK(r.scan_req.dwell_time_passive == ((sta || sap) && !dbs && bt ? 28U : 110U));
        r.scan_req.dwell_time_passive = 10;
        scm_update_passive_dwell_time(&v, &r);
        CHECK(r.scan_req.dwell_time_passive == 10);
    }
    v.psoc = NULL; r.scan_req.dwell_time_passive = 110;
    scm_update_passive_dwell_time(&v, &r);
    CHECK(r.scan_req.dwell_time_passive == 110);
    hdd_bt_activity_cb(NULL, WLAN_COEX_EVENT_BT_VOICE_PROFILE_ADD);
    if (failures) { fprintf(stderr, "%u failed assertions\n", failures); return 1; }
    puts("PASS: Bluetooth profile transitions and scan policy matrix");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="coex-test-") as work:
    cfile = Path(work) / "test.c"
    binary = Path(work) / "test"
    cfile.write_text(prefix + tests)
    subprocess.run([os.environ.get("HOSTCC", "cc"), "-std=gnu11", "-Wall", "-Wextra",
                    "-Werror", "-fsanitize=undefined", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
