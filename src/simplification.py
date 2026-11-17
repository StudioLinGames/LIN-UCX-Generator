# SPDX-License-Identifier: GPL-3.0-or-later

import math
import bpy
from .geometry import validate_convex_geometry


MODIFIER_NAME = "LIN Collision Decimate"
ALLOWED = {'CONVEX_HULL','LOOSE_PARTS','MESH','SEGMENTED'}


class LIN_OT_simplify_collision(bpy.types.Operator):
    bl_idname = 'lin.simplify_collision'
    bl_label = 'Simplify Collision'
    bl_options = {'REGISTER','UNDO'}
    bl_description = 'Configure unapplied native Collapse Decimate; warn about export validity and reject unusable output'

    def execute(self,context):
        from .management import selected_assets, is_owned
        from .operators import associated_collisions
        targets = list(dict.fromkeys(c for asset in selected_assets(context) for c in associated_collisions(asset)
                                    if is_owned(c,asset) and c.get('lin_ucx_method') in ALLOWED))
        states = []
        try:
            for c in targets:
                modifier = get_simplification_modifier(c)
                if modifier and c.get('lin_ucx_decimate_owner') != c.get('lin_ucx_token'):
                    raise ValueError('Existing modifier has ambiguous ownership')
                states.append((c, modifier, {p:getattr(modifier,p) for p in ('ratio','decimate_type','use_collapse_triangulate','show_viewport','show_render')} if modifier else None))
                configure_decimate(c,context.scene.lin_ucx_settings.simplification_ratio)
            context.view_layer.update()
            for c,_modifier,_state in states:
                evaluated = c.evaluated_get(context.evaluated_depsgraph_get())
                mesh = evaluated.to_mesh()
                try:
                    verts = [v.co.copy() for v in mesh.vertices]
                    if len(verts)<4 or not mesh.polygons:
                        raise ValueError('Ratio produces an empty or unusable collision')
                    try:
                        validate_convex_geometry(verts,[tuple(f.vertices) for f in mesh.polygons])
                        c['lin_ucx_export_warning'] = ''
                    except (ValueError,RuntimeError) as warning:
                        c['lin_ucx_export_warning'] = str(warning)
                        self.report({'WARNING'},f'{c.name}: not export-ready: {warning}')
                finally:
                    evaluated.to_mesh_clear()
            for c,_m,_s in states:
                c['lin_ucx_decimate_owner'] = c['lin_ucx_token']
        except Exception as exc:
            for c,modifier,state in reversed(states):
                if state is None:
                    current = c.modifiers.get(MODIFIER_NAME)
                    if current: c.modifiers.remove(current)
                else:
                    for prop,value in state.items(): setattr(modifier,prop,value)
            context.view_layer.update()
            self.report({'WARNING'},str(exc))
            return {'CANCELLED'}
        self.report({'INFO'},f'Configured {len(targets)} collision modifiers; verify manually after further edits.')
        return {'FINISHED'} if targets else {'CANCELLED'}


def get_simplification_modifier(
    collision
):

    modifier = collision.modifiers.get(
        MODIFIER_NAME
    )

    if modifier is not None:

        if modifier.type != 'DECIMATE':

            raise RuntimeError(
                "Modifier name conflict."
            )

    return modifier


def configure_decimate(
    collision,
    ratio
):

    if collision.type != 'MESH':

        raise ValueError(
            "Collision must be a mesh."
        )

    ratio = float(ratio)

    if not math.isfinite(ratio):

        raise ValueError(
            "Invalid decimation ratio."
        )

    if not 0.0 <= ratio <= 1.0:

        raise ValueError(
            "Ratio must be between 0 and 1."
        )

    modifier = get_simplification_modifier(
        collision
    )

    if modifier is None:

        modifier = collision.modifiers.new(

            name=MODIFIER_NAME,

            type='DECIMATE'

        )

    modifier.decimate_type = 'COLLAPSE'

    modifier.ratio = ratio

    modifier.use_collapse_triangulate = False

    modifier.show_viewport = True
    modifier.show_render = True

    return modifier


def evaluated_geometry_statistics(
    obj,
    depsgraph
):

    evaluated = obj.evaluated_get(
        depsgraph
    )

    mesh = evaluated.to_mesh()

    try:

        if mesh is None:

            raise RuntimeError(
                "Unable to evaluate collision."
            )

        mesh.calc_loop_triangles()

        return {

            "vertices": len(mesh.vertices),

            "edges": len(mesh.edges),

            "faces": len(mesh.polygons),

            "triangles": len(
                mesh.loop_triangles
            )

        }

    finally:

        evaluated.to_mesh_clear()
