# External ZFS disk and monitor work

## ZFS

The builder's opt-in `KERNEL_PROFILE=zfs` enables MODULES, MODULE_UNLOAD and
MODVERSIONS, with the distinct release suffix `-Eclipse-ZFS-EXPERIMENTAL`.
The ordinary daily profile remains unchanged. ZFS is an external OpenZFS
module, not copied into the GPL kernel binary. OpenZFS 2.4.4 upstream commit
71a9f9578616a90c3c14bb59629fb4d31bfd68d1 declares Linux 4.18 through 7.2;
that range is not proof of compatibility with the vendor-patched 5.4 tree.

An actual usable Android port also needs matching ARM64 zpool/zfs utilities,
their runtime libraries, /dev/zfs access and a root/SELinux/mount integration.
Module compilation alone does not provide a working Android filesystem.
The current daily AnyKernel installer has do.modules=0 and rejects this
experimental profile. No automatic module loading or disk import is added.

For an existing disk, do not format it, enable pool features, run zpool upgrade,
or import it read/write as a compatibility experiment. First identify all pool
members and enabled features. A later first-device check must explicitly use
readonly=on, cachefile=none, no automatic mounting and an alternate root;
never force-import a pool still active on another host. No such import is
performed by the build tools.

## Independent monitor

The connected ROM exposes freeform-window and secondary-display features,
but the current DRM inventory contains only the internal DSI connector.
That observation alone cannot prove board wiring or add a video transmitter.
The shared SoC device tree's USB3/DP names are not evidence that the phone
has the corresponding connector lanes routed.

An ordinary USB-C hub's HDMI port generally uses DP Alternate Mode. It does
not become a USB graphics adapter by enabling desktop-mode settings. Exact
hub identification and board video-output capability remain necessary.

Synaptics supports DisplayLink USB graphics on Android over USB 2.0/3.0 with
USB host/OTG and its Android app. This is a separate hardware path, and a
powered hub may be necessary. It does not guarantee an independent desktop
rather than mirroring; Android composer/desktop integration must be checked
with the real adapter. The in-tree UDL driver covers older DisplayLink chips,
not every DisplayLink device, and is not enabled speculatively.

Sources:
- https://github.com/openzfs/zfs/tree/zfs-2.4.4
- https://openzfs.github.io/openzfs-docs/License.html
- https://www.synaptics.com/products/displaylink-graphics/downloads/android
- https://support.displaylink.com/knowledgebase/articles/1915774-android-phone-is-not-cloning-to-a-displaylink-scre

No device writes, desktop setting changes, module insertion or disk writes
are performed by this work. Hardware behavior is unverified.
