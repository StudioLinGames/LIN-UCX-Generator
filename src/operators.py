# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Studio Lin Games
"""UCX generation, shared object setup and per-asset rollback."""
import math
import uuid
import bpy
from mathutils import Matrix, Vector
from .geometry import (generate_convex_geometry,
                       validate_convex_geometry, create_convex_hull)
from .primitives import create_sphere_geometry, create_capsule_geometry

PREFIXES = ('UCX_', 'UBX_', 'USP_', 'UCP_')

MIN_THICKNESS = 0.001
FACES = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
         (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))


def valid_assets(context):
    return [obj for obj in context.selected_objects
            if obj.type == 'MESH' and not obj.name.startswith(PREFIXES)]


def has_existing_collisions(obj):
    """Prefer source ID metadata; accept exact legacy names, never substrings.

    An untagged UCX_A_01 is assigned to mesh A_01 when it exists, rather than
    guessed to be part 01 of A. Parenting disambiguates legacy groups as well.
    """
    return bool(associated_collisions(obj))


def associated_collisions(obj):
    found = []
    for collision in bpy.data.objects:
        if collision.get('lin_ucx_source') == obj:
            found.append(collision)
            continue
        if 'lin_ucx_source' in collision:
            continue
        for prefix in PREFIXES:
            base = prefix + obj.name
            if collision.name == base:
                found.append(collision)
                break
            if not collision.name.startswith(base + '_'):
                continue
            suffix = collision.name[len(base)+1:]
            if len(suffix) < 2 or not suffix.isascii() or not suffix.isdecimal():
                continue
            exact_asset = bpy.data.objects.get(collision.name[4:])
            if collision.parent == obj or exact_asset is None or exact_asset.type != 'MESH':
                found.append(collision)
                break
    return found


def _box_geometry(context, obj):
    # Keep the 1.0.0 evaluated local bounding-box algorithm unchanged.
    evaluated = obj.evaluated_get(context.evaluated_depsgraph_get())
    if not evaluated.data.vertices:
        raise ValueError("Empty evaluated mesh")
    coords = [Vector(c) for c in evaluated.bound_box]
    if not all(math.isfinite(v) for c in coords for v in c):
        raise ValueError("Invalid evaluated bounds")
    low = Vector(tuple(min(c[i] for c in coords) for i in range(3)))
    high = Vector(tuple(max(c[i] for c in coords) for i in range(3)))
    center = (low + high) / 2
    size = Vector(tuple(max(high[i] - low[i], MIN_THICKNESS) for i in range(3)))
    corners = ((-1,-1,-1), (1,-1,-1), (1,1,-1), (-1,1,-1),
               (-1,-1,1), (1,-1,1), (1,1,1), (-1,1,1))
    return [center + Vector(tuple(c[i] * size[i] / 2 for i in range(3))) for c in corners], FACES


def _transform(obj):
    world = obj.matrix_world.copy()
    if not all(math.isfinite(v) for row in world for v in row):
        raise ValueError("Non-finite transform")
    linear = world.to_3x3()
    if any(linear.col[i].length == 0 for i in range(3)):
        raise ValueError("Degenerate transform (zero scale)")
    try:
        world.inverted()
    except ValueError as exc:
        raise ValueError("Degenerate transform") from exc
    location, rotation, _scale = world.decompose()
    collision_world = Matrix.LocRotScale(location, rotation, Vector((1, 1, 1)))
    baked = rotation.to_matrix().transposed() @ linear
    return world, collision_world, baked


def _create_object(name, vertices, faces, obj, settings, collection, world, collision_world):
    mesh = cube = None
    try:
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        cube = bpy.data.objects.new(name, mesh)
        if cube.name != name:
            raise ValueError("Exact UCX name cannot be represented by Blender")
        collection.objects.link(cube)
        cube.matrix_world = collision_world
        if settings.parent_to_asset:
            cube.parent = obj
            cube.matrix_parent_inverse = world.inverted()
            cube.matrix_world = collision_world
        cube.display_type = 'WIRE' if settings.wireframe_display else 'SOLID'
        cube.hide_render = settings.hide_from_render
        cube.show_in_front = settings.show_in_front
        cube['lin_ucx_source'] = obj
        cube['lin_ucx_method'] = settings.collision_type
        cube['lin_ucx_generated'] = True
        cube['lin_ucx_version'] = '1.4.1'
        cube['lin_ucx_token'] = uuid.uuid4().hex
        return cube
    except Exception:
        if cube is not None:
            bpy.data.objects.remove(cube, do_unlink=True)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
        raise


def create_collisions_for_object(context, obj, settings, geometries=None, staging=False):
    """Return all new meshes, or None if existing collisions reserve this asset.

    Prepare every hull and transformed mesh before committing any object. On
    creation/link/setup failure, roll back all new objects for this asset only.
    """
    if not staging and has_existing_collisions(obj):
        return None
    world, collision_world, baked = _transform(obj)
    method = settings.collision_type
    depsgraph = context.evaluated_depsgraph_get()
    if method in ('NATIVE_BOX', 'SPHERE', 'CAPSULE'):
        cols = [baked.col[i] for i in range(3)]
        lengths = [c.length for c in cols]
        if any(abs(cols[i].dot(cols[j])) > lengths[i]*lengths[j]*1e-5 for i in range(3) for j in range(i)):
            raise ValueError("Shear is incompatible with native primitives; use UCX Box or Convex Hull")
        if method in ('SPHERE','CAPSULE') and max(lengths)-min(lengths) > max(lengths)*1e-5:
            raise ValueError("Nonuniform scale is incompatible with USP/UCP; use Convex Hull UCX")
    if method in ('BOX','NATIVE_BOX'):
        geometries = [_box_geometry(context, obj)]
    elif method in ('SPHERE','CAPSULE'):
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            points = [v.co.copy() for v in mesh.vertices] if mesh else []
            function = create_sphere_geometry if method == 'SPHERE' else create_capsule_geometry
            geometries = [function(points)]
        finally:
            evaluated.to_mesh_clear()
    elif method == 'CONVEX_HULL':
        geometries = [generate_convex_geometry(obj, depsgraph)]
    elif method in ('MESH','SEGMENTED'):
        from .mesh_collision import generate_mesh_collision, generate_segmented_collision
        geometries = ([generate_mesh_collision(obj,depsgraph)] if method == 'MESH' else generate_segmented_collision(obj,depsgraph))
    else:
        raise ValueError("Unsupported collision type")
    prefix = {'NATIVE_BOX':'UBX_', 'SPHERE':'USP_', 'CAPSULE':'UCP_'}.get(method,'UCX_')
    base = prefix + obj.name
    names = [f'{base}_{i:02d}' if method == 'SEGMENTED' else base for i in range(len(geometries))]
    # Blender 4.2 uses a 63-byte ID name limit. Query the installed RNA limit
    # where provided, but always verify the actual result after object creation.
    name_limit = bpy.types.ID.bl_rna.properties['name'].length_max
    for name in names:
        if name_limit and len(name.encode('utf-8')) > name_limit:
            raise ValueError("Exact UCX name exceeds Blender's name length limit")
        if not staging and bpy.data.objects.get(name) is not None:
            return None
    prepared = []
    for vertices, faces in geometries:
        vertices = [baked @ Vector(v) for v in vertices]
        if baked.determinant() < 0:
            faces = [tuple(reversed(f)) for f in faces]
        if method != 'BOX':
            try:
                validate_convex_geometry(vertices, faces)
            except ValueError:
                if method not in ('SEGMENTED','MESH','CONVEX_HULL'):
                    raise
                # A segment classified convex before float32 storage may have
                # unstable supporting planes afterwards. Repair this piece only,
                # preserving its volume; never replace the asset's decomposition.
                import bmesh
                from .geometry import _double_hull
                bm = bmesh.new()
                try:
                    vs = [bm.verts.new(v) for v in vertices]
                    for face in faces: bm.faces.new([vs[i] for i in face])
                    before = abs(bm.calc_volume())
                    repaired, repaired_faces = _double_hull([tuple(v) for v in vertices])
                    bm.clear()
                    vs = [bm.verts.new(v) for v in repaired]
                    for face in repaired_faces: bm.faces.new([vs[i] for i in face])
                    after = abs(bm.calc_volume())
                    if before <= 0 or abs(after-before)/before > 1e-4:
                        raise ValueError('Hull storage repair exceeds volume-preservation bound')
                    vertices, faces = repaired, repaired_faces
                finally:
                    bm.free()
                validate_convex_geometry(vertices,faces)
        prepared.append((vertices, faces))
    collection = (obj.users_collection[0] if settings.match_asset_collection and obj.users_collection else context.collection)
    created = []
    try:
        for name, (vertices, faces) in zip(names, prepared):
            collision = _create_object('LIN_STAGE_'+uuid.uuid4().hex if staging else name, vertices, faces, obj, settings, collection, world, collision_world)
            created.append(collision)
            if staging:
                collision['lin_ucx_final_name'] = name
        return created
    except Exception:
        for collision in reversed(created):
            mesh = collision.data
            bpy.data.objects.remove(collision, do_unlink=True)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        raise


def create_ucx_for_object(context, obj, settings):
    """Retain the 1.0.0 single-object helper for Box callers and regression tests."""
    collisions = create_collisions_for_object(context, obj, settings)
    return collisions[0] if collisions else None


class LIN_OT_generate_ucx_collision(bpy.types.Operator):
    bl_idname = "lin.generate_ucx_collision"
    bl_label = "Generate UCX Collision"
    bl_description = "Generate UCX collisions for selected mesh assets using the chosen method"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        assets = valid_assets(context)
        if not assets:
            self.report({'WARNING'}, "Select at least one mesh asset (excluding UCX_ objects).")
            return {'CANCELLED'}
        created, skipped, failed, processed = [], 0, 0, 0
        for obj in assets:
            try:
                collisions = create_collisions_for_object(context, obj, context.scene.lin_ucx_settings)
                if collisions is None:
                    skipped += 1
                else:
                    created.extend(collisions)
                    for warning in {c.get("lin_ucx_warning","") for c in collisions}:
                        if warning: self.report({'WARNING'},warning)
                    processed += 1
            except Exception as exc:
                failed += 1
                self.report({'WARNING'}, f"{obj.name}: {exc}")
        if created:
            for obj in context.selected_objects:
                obj.select_set(False)
            for obj in assets + created:
                # An asset can also belong to an excluded first collection.
                if context.view_layer.objects.get(obj.name) is obj:
                    obj.select_set(True)
            context.view_layer.objects.active = assets[0]
        self.report({'WARNING'} if failed else {'INFO'},
                    f"Generated {len(created)} UCX collision meshes. Assets: {processed} processed, "
                    f"{skipped} skipped (existing collisions), {failed} failed.")
        return {'FINISHED'} if created else {'CANCELLED'}

