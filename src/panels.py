# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Studio Lin Games
import bpy
import textwrap
from .operators import valid_assets


class LIN_PT_ucx_generator(bpy.types.Panel):
    bl_label = "LIN UCX Generator"
    bl_idname = "LIN_PT_ucx_generator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "LIN Tools"

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.lin_ucx_settings
        layout.label(text="Collision Settings")
        layout.prop(settings, "collision_category", expand=True)
        layout.label(text="Collision Type")
        layout.prop(settings, "simple_type" if settings.collision_category == 'SIMPLE' else "detailed_type", text="")
        from .properties import SIMPLE, DETAILED
        descriptions = {key:description for key,label,description,*_ in SIMPLE+DETAILED}
        # Split at word boundaries using the sidebar width, including UI scale.
        scale = context.preferences.system.ui_scale or 1.0
        width = max(10, int(context.region.width / (7 * scale)) - 3)
        for line in textwrap.wrap(descriptions[settings.collision_type], width=width):
            layout.label(text=line)
        layout.label(text="Options")
        col = layout.column(align=True)
        for prop in ("parent_to_asset", "match_asset_collection", "wireframe_display", "show_in_front", "hide_from_render"):
            col.prop(settings, prop)
        layout.label(text="Actions")
        if not valid_assets(context):
            layout.label(text="Select a mesh asset.", icon='INFO')
        row = layout.row()
        row.enabled = bool(valid_assets(context))
        row.operator("lin.generate_ucx_collision", icon='MESH_CUBE')
        if settings.collision_type in ('CONVEX_HULL','MESH','SEGMENTED'):
            layout.label(text='Collision Simplification')
            layout.prop(settings,'simplification_ratio',text='Ratio',slider=False)
            layout.operator('lin.simplify_collision',icon='MOD_DECIM')
        layout.label(text="Collision Management")
        layout.operator('lin.select_collisions',icon='RESTRICT_SELECT_OFF')
        layout.operator('lin.select_asset_collisions',icon='RESTRICT_SELECT_OFF')
        row = layout.row()
        row.operator('lin.collision_visibility',text='Show').hide = False
        row.operator('lin.collision_visibility',text='Hide').hide = True
        layout.operator('lin.regenerate_collision',icon='FILE_REFRESH')
        layout.operator('lin.remove_generated_collisions',icon='TRASH')
        if getattr(context,'view_layer',None):
            from .management import source_asset, statistics
            stats = statistics(source_asset(context.view_layer.objects.active))
            layout.label(text="Collision Statistics")
            for label,key in (('Source Vertices','source_vertices'),('Source Faces','source_faces'),('Source Triangles','source_triangles'),('Collision Objects','objects'),('Total Vertices','vertices'),('Total Faces','faces'),('Total Triangles','triangles'),('Collision Method','methods')):
                for line in textwrap.wrap(f'{label}: {stats[key]}',width=width):
                    layout.label(text=line)
        layout.separator()
        col = layout.column(align=True)
        col.label(text="Studio Lin Games")
        col.label(text="Version 1.4.1")
