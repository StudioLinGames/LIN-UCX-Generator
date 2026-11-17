# LIN UCX Generator

**Less time creating collisions. More time creating games.**

Automatic collision generation for Blender and Unreal Engine. Free, lightweight
and open source. Developed by **Studio Lin Games**. Version **1.4.1**, approved by
the developer as a stable-publication candidate with documented limitations.

## Features

Seven collision methods, evaluated modifiers, multiple selected assets, exact
Unreal collision naming, configurable parenting/collections/display, editable
collision meshes, native Undo, safe collision management and evaluated statistics.
No external dependencies, telemetry, runtime downloads or integrated FBX exporter.

## Installation

Install the approved `lin_ucx_generator-1.4.1.zip` without extracting it:
**Edit > Preferences > Get Extensions > menu > Install from Disk**. Enable the
extension, enter Object Mode and open **3D Viewport > Sidebar (N) > LIN Tools**.
Save your work before replacing an older installation. Existing collisions and
supported scene settings are retained. No public download link is provided here
before the release is actually published.

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

Verified on **Windows x64, Blender 5.2.2 LTS and 5.3.0**. The minimum remains 5.2.2;
Blender 4.2, Linux and macOS are unverified. No binary platform restriction is set.

Convex envelopes can fill holes. Segmented requires suitable closed solids and may
reject open, non-manifold, overly complex or numerically difficult inputs. Very tiny
open synthetic models with complex transforms can be safely rejected. Original
independent automation recorded **198/200 passes**, with seeds 3006/3009 rejected;
the developer later observed manual success for 3006 and continued rejection for
3009. This discrepancy is unresolved and documented, not relabelled as an automated
pass. Review all generated and simplified collision before export. See
[known limitations](docs/known_limitations.md) and [testing](docs/testing.md).

The developer reports successful real Blender/Unreal testing, including Native Box
and player passage through a segmented arch. These are manual reports, not automated
Unreal tests. No claim is made that every geometry or gameplay query is supported.

## License, contributing and contact

**GPL-3.0-or-later**. See [LICENSE](LICENSE) and [CONTRIBUTING.md](CONTRIBUTING.md).
Copyright (C) 2026 Studio Lin Games. Provided without warranty.

Contact: [studiolingames@gmail.com](mailto:studiolingames@gmail.com).

Release preparation targets `StudioLinGames/LIN-UCX-Generator`; repository creation,
push and release publication require the owner's separate approval. No Blender
Extensions listing, screenshots, videos or download URLs are invented.
