# Public synthetic tests

Public-copy verification on 2026-11-18 produced the same results on Windows Blender
5.2.2 LTS and 5.3.0:

| Check | Result on each version |
| --- | --- |
| Original Box regression tests | 10/10 |
| Shared convex geometry tests | 9/9 |
| Synthetic selection, migration and Undo tests | 6/6 |
| Synthetic segmentation/simplification script | Pass; arch has 8 pieces |
| Development/generalization cases | 300/300 |
| Independent holdout rerun | 198/200; known Mesh barrel seeds 3006/3009 reject |
| Approved ZIP, official extension validator | Pass |

Only generated synthetic geometry is used. No private .blend/FBX, fixture loader,
private results or historical Git objects are included. Run each script in a fresh
background Blender process; scripts clear disposable scene state.

From the repository root, replace `blender` with your installed executable:

```sh
blender --background --factory-startup --python-exit-code 1 --python tests/test_ucx_generator.py
blender --background --factory-startup --python-exit-code 1 --python tests/test_convex_geometry.py
blender --background --factory-startup --python-exit-code 1 --python tests/test_export_selection.py
blender --background --factory-startup --python-exit-code 1 --python tests/test_synthetic_segmentation.py
blender --background --factory-startup --python-exit-code 1 --python tests/test_generalization141.py
blender --background --factory-startup --python-exit-code 1 --python tests/test_generalization141.py -- --holdout
```

The holdout command intentionally reports failures and exits nonzero for the two
documented Mesh cases. Do not treat that result as a fully passing suite or change
the original expectations to conceal it. JSON output goes to ignored `tests/results/`.

The final holdout intentionally preserves the original known failure evidence. Its
historical result is 198/200 with two Mesh barrel rejections, so the script exits
nonzero when they reproduce. This is **not** a fully green test suite; do not suppress
or relabel those failures. See known_limitations.md. Other synthetic regressions
passed on Windows Blender 5.2.2 LTS / 5.3.0; production and manual Unreal evidence is
summarized publicly without shipping the private models.

The public copy of the selection tests excludes the private-fixture test; shared
synthetic selection/migration/Undo cases remain. The generalization script creates
an ignored tests/results directory locally for numeric reports. Synthetic segmentation
includes generated door/window/arch and disconnected-component fixtures.

Build/validate source using official Blender Extensions tools:

```powershell
blender --command extension build --source-dir src --output-dir dist
blender --command extension validate dist/lin_ucx_generator-1.4.1.zip
```

Only the already approved ZIP is intended for the initial v1.4.1 release asset.
A developer rebuild is not automatically the approved artifact; compare content/hash
and obtain release approval before substituting it.
