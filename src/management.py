# SPDX-License-Identifier: GPL-3.0-or-later
"""Conservative ownership and transactional collision replacement."""
import uuid
import bpy
from .operators import associated_collisions, valid_assets, create_collisions_for_object
from .properties import SIMPLE, DETAILED


def source_asset(obj):
    if obj is None:
        return None
    source = obj.get('lin_ucx_source')
    return source if isinstance(source,bpy.types.Object) else obj


def is_owned(collision, asset=None):
    source = collision.get('lin_ucx_source')
    token = collision.get('lin_ucx_token')
    if (not collision.get('lin_ucx_generated',False) or not token or
        collision.library or not isinstance(source,bpy.types.Object) or
        (asset is not None and source != asset)):
        return False
    if collision.parent is not None and collision.parent != source:
        return False
    # Copies inherit custom properties: ambiguous duplicate tokens are never deleted.
    return sum(o.get('lin_ucx_token') == token for o in bpy.data.objects) == 1


def remove_objects(objects):
    for obj in objects:
        mesh = obj.data if obj.type == 'MESH' else None
        bpy.data.objects.remove(obj,do_unlink=True)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def replace_for_asset(context, obj, settings, geometries=None, seconds=0):
    old = associated_collisions(obj)
    if any(not is_owned(c,obj) for c in old):
        raise ValueError('Manual, legacy or ambiguous collisions are protected; remove them explicitly before regenerating')
    staged = create_collisions_for_object(context,obj,settings,geometries=geometries,staging=True)
    old_names = [(c,c.name) for c in old]
    try:
        old_set = set(old)
        for collision in staged:
            reserved = bpy.data.objects.get(collision['lin_ucx_final_name'])
            if reserved is not None and reserved not in old_set:
                raise ValueError('Output name is reserved by another object')
        for collision,_name in old_names:
            collision.name = 'LIN_OLD_'+uuid.uuid4().hex
        for collision in staged:
            name = collision['lin_ucx_final_name']
            collision.name = name
            if collision.name != name:
                raise ValueError('Exact output name could not be assigned')
            del collision['lin_ucx_final_name']
            collision['lin_ucx_seconds'] = seconds
    except Exception:
        remove_objects(staged)
        for collision,name in old_names:
            collision.name = name
        raise
    remove_objects(old)
    return staged


def statistics(asset):
    collisions = associated_collisions(asset) if asset else []
    meshes = [c for c in collisions if c.type == 'MESH']
    labels = {item[0]:item[1] for item in SIMPLE+DETAILED}
    labels['LOOSE_PARTS'] = 'Convex by Loose Parts (legacy)'
    from .simplification import evaluated_geometry_statistics
    dg = bpy.context.evaluated_depsgraph_get()
    totals = [evaluated_geometry_statistics(c,dg) for c in meshes]
    source = evaluated_geometry_statistics(asset,dg) if asset and asset.type == 'MESH' else dict(vertices=0,faces=0,triangles=0)
    return dict(objects=len(collisions), vertices=sum(t['vertices'] for t in totals), faces=sum(t['faces'] for t in totals), triangles=sum(t['triangles'] for t in totals), source_vertices=source['vertices'],source_faces=source['faces'],source_triangles=source['triangles'],methods=', '.join(sorted({labels.get(c.get('lin_ucx_method'),'Legacy/manual') for c in collisions})) or 'None')



def selected_assets(context):
    assets = list(valid_assets(context))
    for collision in context.selected_objects:
        source = collision.get('lin_ucx_source')
        if isinstance(source,bpy.types.Object) and source not in assets:
            assets.append(source)
    return assets


class LIN_OT_select_collisions(bpy.types.Operator):
    bl_idname = 'lin.select_collisions'
    bl_label = 'Select Collisions'
    bl_description = 'Select only collisions associated with the active asset'
    bl_options = {'REGISTER','UNDO'}

    def execute(self,context):
        source = source_asset(context.view_layer.objects.active)
        if not source:
            return {'CANCELLED'}
        collisions = associated_collisions(source)
        for obj in context.selected_objects:
            obj.select_set(False)
        visible = [c for c in collisions if context.view_layer.objects.get(c.name) == c and not c.hide_get()]
        for collision in visible:
            collision.select_set(True)
        if visible:
            context.view_layer.objects.active = visible[0]
        self.report({'INFO'},f'Selected {len(visible)} collision objects.')
        return {'FINISHED'}



def select_asset_collision_groups(context, groups):
    """Atomic selection: reveal only target objects; restore everything on failure."""
    layer = context.view_layer
    groups = [(source,tuple(collisions)) for source,collisions in groups]
    targets = list(dict.fromkeys(obj for source, collisions in groups for obj in (source,*collisions)))
    previous = list(context.selected_objects)
    active = layer.objects.active
    changes = []
    failed = []
    try:
        for obj in targets:
            if layer.objects.get(obj.name) != obj:
                failed.append(f'{obj.name}: not in current View Layer')
                continue
            hidden = obj.hide_get(view_layer=layer)
            if hidden:
                changes.append((obj,hidden))
                obj.hide_set(False,view_layer=layer)
            if obj.hide_select:
                failed.append(f'{obj.name}: selection disabled')
            elif not obj.visible_get(view_layer=layer):
                failed.append(f'{obj.name}: hidden by object or collection restrictions')
        if failed:
            raise RuntimeError('Incomplete selection')
        for obj in previous: obj.select_set(False,view_layer=layer)
        for obj in targets:
            obj.select_set(True,view_layer=layer)
            if not obj.select_get(view_layer=layer):
                failed.append(f'{obj.name}: selection rejected')
        if failed:
            raise RuntimeError('Incomplete selection')
        layer.objects.active = groups[0][0]
        return dict(selected=len(targets),failed=[],active=groups[0][0])
    except Exception as exc:
        if not failed: failed.append(str(exc))
        for obj in list(context.selected_objects): obj.select_set(False,view_layer=layer)
        for obj,hidden in changes: obj.hide_set(hidden,view_layer=layer)
        for obj in previous:
            if layer.objects.get(obj.name) == obj: obj.select_set(True,view_layer=layer)
        layer.objects.active = active
        return dict(selected=0,failed=failed,active=None)


class LIN_OT_select_asset_collisions(bpy.types.Operator):
    bl_idname = 'lin.select_asset_collisions'
    bl_label = 'Select Asset + Collisions'
    bl_description = 'Select source meshes and all unambiguously owned collisions for Selected Objects FBX export'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls,context):
        return context.mode == 'OBJECT'

    def execute(self,context):
        assets, excluded = [], []
        selected = list(context.selected_objects)
        active = context.view_layer.objects.active
        if active in selected:
            selected.remove(active)
            selected.insert(0,active)
        for obj in selected:
            if 'lin_ucx_source' in obj:
                if not is_owned(obj):
                    excluded.append(obj.name)
                    continue
                source = source_asset(obj)
            elif obj.type == 'MESH' and obj in valid_assets(context):
                source = obj
            else:
                continue
            if source.type == 'MESH' and source not in assets: assets.append(source)
        if not assets:
            self.report({'WARNING'},'Select a mesh asset or an unambiguously generated collision.')
            return {'CANCELLED'}
        groups = []
        for asset in assets:
            associated = associated_collisions(asset)
            owned = [c for c in associated if c.type == 'MESH' and is_owned(c,asset)]
            ambiguous = [c.name for c in associated if c.get('lin_ucx_generated',False) and c not in owned]
            if ambiguous:
                self.report({'WARNING'},'Selection unchanged: ambiguous generated pieces: '+', '.join(ambiguous))
                return {'CANCELLED'}
            excluded.extend(c.name for c in associated if c not in owned)
            if not owned:
                self.report({'WARNING'},f'{asset.name}: no unambiguously generated collisions; selection unchanged.')
                return {'CANCELLED'}
            groups.append((asset,owned))
        result = select_asset_collision_groups(context,groups)
        if result['failed']:
            self.report({'WARNING'},'Selection unchanged: '+'; '.join(result['failed']))
            return {'CANCELLED'}
        if excluded:
            self.report({'WARNING'},'Excluded manual or ambiguous objects: '+', '.join(sorted(set(excluded))))
        asset_count = len(groups)
        collision_count = sum(len(c) for _,c in groups)
        self.report({'INFO'},f"Selected {asset_count} asset{'s' if asset_count != 1 else ''} and {collision_count} collision object{'s' if collision_count != 1 else ''}.")
        return {'FINISHED'}

class LIN_OT_visibility(bpy.types.Operator):
    bl_idname = 'lin.collision_visibility'
    bl_label = 'Show / Hide Collisions'
    bl_description = 'Show or hide associated collisions without hiding source assets'
    bl_options = {'REGISTER','UNDO'}
    hide: bpy.props.BoolProperty(default=True)

    def execute(self,context):
        for asset in selected_assets(context):
            for collision in associated_collisions(asset):
                if context.view_layer.objects.get(collision.name) == collision:
                    collision.hide_set(self.hide)
        return {'FINISHED'}


class LIN_OT_remove_collisions(bpy.types.Operator):
    bl_idname = 'lin.remove_generated_collisions'
    bl_label = 'Remove Generated Collisions'
    bl_description = 'Delete only unambiguously owned LIN collisions; manual and legacy objects are protected'
    bl_options = {'REGISTER','UNDO'}

    def invoke(self,context,event):
        return context.window_manager.invoke_confirm(self,event)

    def execute(self,context):
        owned = set()
        for asset in selected_assets(context):
            owned.update(c for c in associated_collisions(asset) if is_owned(c,asset))
        remove_objects(owned)
        self.report({'INFO'},f'Removed {len(owned)} generated collisions. Manual, legacy and ambiguous objects preserved.')
        return {'FINISHED'} if owned else {'CANCELLED'}


class LIN_OT_regenerate(bpy.types.Operator):
    bl_idname = 'lin.regenerate_collision'
    bl_label = 'Regenerate Collision'
    bl_description = 'Replace owned collisions only after all new geometry is valid; legacy/manual collisions are protected'
    bl_options = {'REGISTER','UNDO'}

    def execute(self,context):
        settings = context.scene.lin_ucx_settings
        made = 0
        for obj in selected_assets(context):
            try:
                made += len(replace_for_asset(context,obj,settings))
            except Exception as exc:
                self.report({'WARNING'},f'{obj.name}: {exc}')
        return {'FINISHED'} if made else {'CANCELLED'}



CLASSES = (LIN_OT_select_collisions, LIN_OT_select_asset_collisions, LIN_OT_visibility, LIN_OT_remove_collisions, LIN_OT_regenerate)
