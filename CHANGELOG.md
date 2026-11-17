# Changelog

## 1.4.1

- Improve shared hull robustness with double-precision supporting-plane measurements,
  separate convexity/containment diagnostics and validated reconstruction after native
  or regularized generation fails. Output tolerance remains 2e-6.
- Revalidate/repair affected stored convex pieces within the existing volume bound;
  never replace a failed segmentation with a single blocking hull.
- Approved as a stable-publication candidate with accepted synthetic precision limits.
  Original automated failure records remain failures; later manual results are separate.

## 1.4.0

- Add Select Asset + Collisions with metadata ownership checks, visibility diagnostics,
  atomic selection rollback and Undo.
- Retire Loose Parts generation, migrate saved choices to Convex Hull and retain
  management/simplification of verified legacy collision groups.

## 1.3.x

- Add native Mesh/Segmented methods, editable unapplied Decimate and evaluated statistics.
- Improve production-fixture robustness and conservative ownership/management safety.

Earlier private development history is intentionally not imported into this clean
public repository. This changelog summarizes features without private models or logs.
