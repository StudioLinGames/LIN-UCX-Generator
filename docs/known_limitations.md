# Known limitations — 1.4.1

The developer accepts the following safe limits for the stable-publication candidate.
No algorithm, tolerance or automated result was changed by that approval.

- Convex Hull and Mesh may fill holes/concavities. Source topology need not be closed
  to form a hull, but generated collision must be closed, convex and nondegenerate.
- Segmented needs suitable closed solids. Open/non-manifold or overly complex input
  may be rejected under the existing 32-piece, 16-depth, candidate/topology/time bounds.
  It is not a universal decomposition solver. No single hull/box hides a failed split.
- Very tiny or thin geometry, distant local origins, negative/nonuniform transforms
  and float32 storage can expose supporting-plane sensitivity. Original independent
  automation passed 198/200 cases and rejected Mesh barrel seeds 3006/3009 at deviations
  3.21350359e-06 and 8.53724939e-06 against normalized tolerance 2e-06.
- Those synthetic meshes span 3D as point clouds but have only two polygons, are open,
  and are not proper closed modeled barrels. A later owner manual test passed seed
  3006 while seed 3009 still rejected. The discrepancy has no confirmed explanation;
  original automated failures remain failures. This does not justify changing tolerance
  or requiring artists to repair every open source mesh.
- Decimate is an approximation. Nonconvex/invalid evaluated output warns; inspect and
  correct before export. Empty/unusable geometry is rejected. Manual modifier changes
  require renewed checking. Ratio 1 recovers the base modifier geometry.
- Duplicate ownership tokens, invalid references and manual/legacy ambiguous objects
  cannot authorize destructive management. Retired Loose Parts groups are not deleted
  automatically. Renaming a source does not automatically fix its exported UCX names.
- Native UBX/USP/UCP shapes have scale/shear restrictions and Unreal query limitations.
  Validate intended engine-side transforms and gameplay behavior.
- Native geometry extraction/validation are synchronous; dense models can pause the UI.
  Bounded processing and safe rejection are not a universal timing guarantee.

Verified only on Windows Blender 5.2.2 LTS and 5.3.0. Blender 4.2/Linux/macOS remain
unverified. The developer reports successful production Blender/Unreal tests, including
Native Box and player passage through a segmented arch; those are manual reports,
not automated engine coverage or a claim about every asset/query.
