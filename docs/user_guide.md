# User guide

## Generate

In Object Mode select source meshes, open N > LIN Tools, choose Simple or Detailed,
select the method and click Generate UCX Collision. Box is the Simple default;
Mesh Collision is the Detailed default. Options apply to newly created objects.
The source geometry and transforms remain unchanged. Existing matching collisions
cause a skip, even if you change method. The whole asset's new group is cleaned up
if generation fails.

Box gives an enclosing box. Native Box/Sphere/Capsule use Unreal's UBX/USP/UCP names;
no shear is allowed, and spheres/capsules require uniform scale magnitude. Convex
Hull wraps all evaluated points. Mesh preserves valid convex source geometry where
possible, otherwise producing one exterior hull. Segmented cuts suitable closed
concave solids into numbered convex pieces; it may fail safely. Hulls/Mesh can fill
openings. Inspect every result before export.

## Simplification and management

Enter the native numeric Ratio (default 1.0000), then press Simplify Collision.
The unapplied Collapse Decimate remains editable; Ratio 1 restores the base. Stats
show evaluated source/collision vertices, faces and triangles. Nonconvex/invalid
approximations warn and must not be assumed export-ready; unusable output is rejected.
Native primitives are protected. Manual/ambiguous ownership is protected as well.

Select Collisions selects associated objects only. Select Asset + Collisions also
includes the source(s), resolves generated child inputs by metadata and makes a
source active. It reveals only relevant per-object hidden targets. Excluded/hidden
collections, global viewport restrictions and selection locks are unchanged; missing
pieces cancel preparation and restore the previous selection. Review warnings.

Show/Hide affects associated collisions. Regenerate stages new validated objects
before replacing owned ones. Remove Generated Collisions asks for confirmation and
supports Undo. Legacy generated Loose Parts collisions can still be managed, but
that generation method is retired and old choices migrate to Convex Hull. Metadata
associations survive source renaming; exported names must still be checked.

## Blender to Unreal Engine

1. Select your source mesh.
2. Choose a collision method.
3. Click Generate UCX Collision.
4. Adjust and inspect the collision geometry if necessary.
5. Click Select Asset + Collisions and check for incomplete-selection warnings.
6. Open File > Export > FBX.
7. Enable Selected Objects.
8. Include Mesh objects.
9. Enable Apply Modifiers when exporting evaluated Decimate geometry.
10. Export the source and its complete collision group to the same FBX.
11. Import the FBX into Unreal Engine.
12. Verify imported simple collision in Static Mesh Editor and in gameplay.

Use one source per file for controlled tests. Individual hulls are UCX_Asset; numbered
pieces are UCX_Asset_00, _01, etc. UBX/USP/UCP identify native primitives. Names must
match the exported source. Where exposed, One Convex Hull per UCX preserves each
convex volume; disable automatic collision generation when verifying custom collision.
Use complexity settings that exercise simple collision. Use Complex Collision As
Simple is a different triangle-mesh workflow and is not what this extension generates.

Do not omit numbered pieces from segmented exports. Native spheres/boxes can have
engine-side nonuniform-scale/query limitations; test your intended traces, physics
and player capsule. Read known_limitations.md before relying on an approximation.
