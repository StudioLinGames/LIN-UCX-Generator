<div align="center">

# LIN UCX Generator

**Less time creating collisions. More time creating games.**

Automatic collision generation for Blender and Unreal Engine.

Free · Lightweight · Open Source

Developed by **Studio Lin Games**.

![Version 1.4.1](https://img.shields.io/badge/Version-1.4.1-blue)
![GPL-3.0-or-later](https://img.shields.io/badge/License-GPL--3.0--or--later-blue)
![Blender](https://img.shields.io/badge/Blender-5.2.2%20%7C%205.3.0-orange)
![Unreal Engine](https://img.shields.io/badge/Unreal%20Engine-Collision-313131)
![No external dependencies](https://img.shields.io/badge/External%20dependencies-None-brightgreen)

**7 collision methods · 35.4 KiB package · Zero external dependencies**

Version 1.4.1 — First public release, with documented limitations.

</div>

## Features

- **Mesh Collision** — preserve valid convex geometry or generate one exterior hull for irregular solid assets.
- **Segmented Collision** — generate independent convex pieces from suitable closed concave geometry while attempting to preserve openings.
- **Non-destructive Collision Simplification** — control complexity with an editable, unapplied native Decimate modifier.
- **Select Asset + Collisions** — prepare the source and its complete collision group for FBX export.
- **Multiple asset support** — generate and manage collision for several selected meshes.
- **Native Unreal Engine collision naming** — UCX, UBX, USP and UCP names matching the source asset.
- **Zero external dependencies** — no runtime downloads, telemetry or network connection required by the extension.

Includes evaluated modifiers and statistics, configurable parenting, collections and
display, editable collision meshes, native Undo and safe collision management.

## Download and installation

> **[Download LIN UCX Generator v1.4.1](https://github.com/StudioLinGames/LIN-UCX-Generator/releases/download/v1.4.1/lin_ucx_generator-1.4.1.zip)** — 35.4 KiB.
> [Official release notes and assets](https://github.com/StudioLinGames/LIN-UCX-Generator/releases/tag/v1.4.1).

Install `lin_ucx_generator-1.4.1.zip` without extracting it:
**Edit > Preferences > Get Extensions > menu > Install from Disk**. Enable the
extension, enter Object Mode and open **3D Viewport > Sidebar (N) > LIN Tools**.
Save your work before replacing an older installation. Existing collisions and
supported scene settings are retained.

## Collision methods

| Category | Method | Recommended use | Naming |
| --- | --- | --- | --- |
| Simple | Box (default) | Rectangular assets; convex bounding box | UCX_Asset |
| Simple | Native Box | Native Unreal box; no shear | UBX_Asset |
| Simple | Sphere | Spherical assets; uniform scale | USP_Asset |
| Simple | Capsule | Capsule-shaped assets; uniform scale | UCP_Asset |
| Simple | Convex Hull | One convex envelope around evaluated vertices | UCX_Asset |
| Detailed | Mesh Collision (default) | Preserve valid convex geometry or create one exterior hull | UCX_Asset |
| Detailed | Segmented Collision | Divide suitable closed concave solids into convex pieces | UCX_Asset_00, _01, ... |

Select source meshes, choose a method and click **Generate UCX Collision**. The
five general options control parenting, matching the source's first collection,
wireframe display, display in front and hiding from render. They default on.

## Collision Simplification

Choose **Ratio** and click **Simplify Collision** to add/update one unapplied native
Collapse Decimate modifier on eligible owned convex/mesh/segmented collisions.
Ratio 1 restores the base geometry. The source mesh is unchanged and statistics
use evaluated geometry. Invalid/nonconvex approximations warn before export; empty
or unusable results are rejected. Native boxes, spheres and capsules are protected.

## Select Asset + Collisions

Use this button from a source or verified generated child, including multiple assets.
It selects the originals and their associated owned collisions and makes an original
active. It can reveal relevant hidden objects. Blocked or excluded pieces cancel
selection and restore its previous state. Manual/ambiguous objects are not silently
included. Other tools select collisions, show/hide, safely regenerate and remove
only verified generated objects, with confirmation for removal.

## Blender to Unreal Engine

Select a source, generate and inspect its collision, then click **Select Asset +
Collisions**. Open **File > Export > FBX**, enable **Selected Objects**, include Mesh
objects, and enable **Apply Modifiers** for evaluated Decimate geometry. Export each
source together with all its named collision objects; use separate files for controlled
independent-asset tests. Inspect imported Simple Collision in Unreal's Static Mesh
Editor. Where available, enable **One Convex Hull per UCX** and disable automatic
collision generation when testing custom collision. UCX is not **Use Complex
Collision As Simple**. See [the user guide](docs/user_guide.md).

## Verified compatibility and limitations

Verified on **Windows x64 with Blender 5.2.2 LTS and 5.3.0**.

Convex envelopes can fill holes and concavities. Segmented Collision requires
suitable closed solids and may reject open, non-manifold, overly complex or
numerically difficult geometry. Extremely small or thin inputs and complex
transforms can also cause safe rejection. Simplified geometry may need correction
before export; always inspect the generated and evaluated collision.

The independent synthetic validation recorded **198/200 passes**, with two known
safe rejections. Full results, seeds 3006/3009 and the unresolved difference between
manual and automated results remain in [testing](docs/testing.md) and
[known limitations](docs/known_limitations.md).

Studio Lin Games reports successful manual Blender/Unreal testing, including Native
Box and player passage through a segmented arch. These are manual results, not
automated Unreal tests or a guarantee for every geometry and gameplay query.

## License, contributing and contact

**GPL-3.0-or-later**. See [LICENSE](LICENSE) and [CONTRIBUTING.md](CONTRIBUTING.md).
Copyright (C) 2026 Studio Lin Games. Provided without warranty.

Contact: [studiolingames@gmail.com](mailto:studiolingames@gmail.com).
