# Domain notes: Tennessee Eastman Process (TEP)

## The plant
- Continuous plant at steady state: two-phase stirred reactor (gas feeds, non-volatile
  catalyst in the liquid), condenser, vapor/liquid separator, recycle compressor,
  stripper. Streams 1–11.
- Four irreversible, exothermic gas-phase reactions; products condense:
  A + C + D → G (product), A + C + E → H (product), A + E → F, 3D → 2F (byproducts).
- Reactor heat is removed by cooling water (XMV 10). Several faults hit that loop.
- Open loop the plant is unstable: reactor pressure runs up to the shutdown limit
  (3000 kPa). All data comes with a control scheme on top.

## Signals
- XMEAS 1–22 are continuous (pressures, temperatures, levels, flows).
  XMEAS 23–41 come from analyzers sampled every 6–15 min, with dead time.
- XMV 1–11 are used; XMV 12 (agitator) is fixed. Datasets use 52 signals
  (41 + 11), sampled every 3 minutes.
- The product analyzer (XMEAS 37–41) does not measure B.

## Inert B
- B is an inert gas. Its only exit is the purge (stream 9).
- B in reactor feed (stream 6) = XMEAS 24; B in purge = XMEAS 30.
- Levels measure liquid inventory; B is non-condensable, so levels are not the
  first place a B fault shows up.

## Diagnosis in closed loop
- Controllers mask faults. Diagnose from compositions plus valve (XMV) movements,
  not only from the variable that deviates.
- Faults 3, 9 and 15 are known to be nearly indistinguishable from normal operation.
- In the reference decentralized control code (temain_mod), XMEAS 30 cascades to the
  purge flow loop (XMEAS 10 -> XMV 6), separator pressure (XMEAS 13) overrides the
  purge, and XMV 4 (A + C feed) follows reactor level (XMEAS 8).
  Verify against our dataset before relying on it.
- Hypothesis to check first (IDV 2, step in B in stream 4): XMEAS 24 and 30 rise;
  purge opens (XMV 6 and XMEAS 10 up); pressures (XMEAS 7, 13) move little if
  control holds them.
