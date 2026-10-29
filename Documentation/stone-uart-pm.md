# GENI UART error handling and runtime power references

The stone board enables the GENI high-speed UART and Bluetooth power driver.
Saved phone logs show Qualcomm's userspace Bluetooth HAL handling in-band
sleep/wake commands. The changes below fix generic GENI driver error paths;
the reported audio dropouts have not been attributed to these paths.

## Propagate a failed manual resume

msm_geni_serial_power_on can invoke the runtime-resume callback manually when
runtime PM is disabled and the port is suspended. Previously it logged a
negative callback result, restored the mutex/disable-depth state, then returned
zero. Callers which check the result could consequently proceed as if the
UART resources were available.

Preserve a negative result at the common return. Keep successful positive
pm_runtime_get_sync results normalized to zero. The existing enabled-PM
failure cleanup and the manual resume's lock/PM bookkeeping are unchanged.
This does not alter callers which ignore the helper return value.

## Balance a TX power vote when DMA setup fails

start_tx obtains a runtime-PM reference for non-console transmission. It used
to release the reference on -EPERM from prep_dma_tx, but not on errors such
as failed DMA mapping. With no DMA in flight there would be no successful
completion to release that reference. Handle every failed preparation through
the existing power-off exit.

The DMA completion handler also prepares the next queued transfer. If that
preparation fails, release the preceding transfer's reference just as when
the queue is empty. A successfully prepared next DMA retains the reference.
Pending bytes remain in the circular buffer, and only completed bytes are
counted/advanced. Existing DMA cancellation, hardware-idle checks, autosuspend
timers, power-off implementation and retry mechanisms are unchanged.

This balances references owned by these TX paths; it does not zero the usage
counter or release references belonging to other port users. It does not force
suspend or remove protections against suspending active hardware.

Runtime PM reference semantics are documented in:
https://www.kernel.org/doc/html/v5.19/power/runtime_pm.html

## Validation and limits

From the builder repository:

```
python3 tests/test-geni-uart-pm.py
```

The test compiles the actual power_on, power_off, start_tx and DMA completion
functions with ASan/UBSan. PM, DMA and MMIO are simulated. It covers failed
manual resumes with an acquired or pre-held mutex, successful enabled/disabled
PM, positive PM success return values, failed DMA setup at start/completion,
other users' references, pending-byte retention and ring wrap, successful DMA
chaining, an empty queue, asynchronous resume, FIFO and suspended console.

Independent baseline runs reproduce the swallowed resume error and both TX
reference leaks. These are fault-injected source tests, not induced failures
on the phone. Full ARM64 compilation is also required. No measured change to
battery life, UART throughput or audible Bluetooth stability is established.
No device, codec, swap, radio, CPU-frequency or thermal setting is modified.
