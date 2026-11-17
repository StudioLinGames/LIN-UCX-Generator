# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Studio Lin Games
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty

SIMPLE = [('BOX','Box','Generate a simple convex bounding box.'),
          ('NATIVE_BOX','Native Box','Generate a native Unreal Engine box collision using the UBX prefix.'),
          ('SPHERE','Sphere','Generate a native Unreal Engine sphere collision using the USP prefix.'),
          ('CAPSULE','Capsule','Generate a native Unreal Engine capsule collision using the UCP prefix.'),
          ('CONVEX_HULL','Convex Hull','Generate a convex envelope around the source geometry.')]
DETAILED = [('MESH','Mesh Collision','Preserve valid convex source geometry or generate a single exterior convex hull. Recommended for irregular solid assets.'),('SEGMENTED','Segmented Collision','Divide closed concave geometry into independent convex segments while attempting to preserve openings.')]
# Preserve the numeric IDs used in saved scenes; reserve retired value 5.
SIMPLE = [(*item,index) for index,item in enumerate(SIMPLE)]
DETAILED = [(*item,index+6) for index,item in enumerate(DETAILED)]



def select_simple(self, context):
    if not self.get('_lin_sync',False):
        self.collision_type = self.simple_type


def select_detailed(self, context):
    if not self.get('_lin_sync',False):
        self.collision_type = self.detailed_type


def select_category(self, context):
    if not self.get('_lin_sync',False):
        self.collision_type = self.simple_type if self.collision_category == 'SIMPLE' else self.detailed_type


def sync_method(self,context):
    if self.get('_lin_sync',False):
        return
    self['_lin_sync'] = True
    try:
        if self.get('collision_type') in (5,'LOOSE_PARTS'):
            self.collision_type = 'CONVEX_HULL'
        if self.get('simple_type') in (5,'LOOSE_PARTS'):
            self.simple_type = 'CONVEX_HULL'
        if self.collision_type in {item[0] for item in SIMPLE}:
            self.collision_category = 'SIMPLE'
            self.simple_type = self.collision_type
        else:
            self.collision_category = 'DETAILED'
            self.detailed_type = self.collision_type
    finally:
        self['_lin_sync'] = False


class LIN_PG_settings(bpy.types.PropertyGroup):
    collision_type: EnumProperty(
        name="Collision Type", description="Choose how convex UCX collisions are generated from evaluated mesh geometry",
        items=SIMPLE+DETAILED,
        default='BOX', update=sync_method)
    collision_category: EnumProperty(name="Collision Category", items=[('SIMPLE','Simple','Primitive or single convex collision'),('DETAILED','Detailed','Multiple simple convex collision hulls')], default='SIMPLE', update=select_category)
    simple_type: EnumProperty(name="Collision Type", items=SIMPLE, default='BOX', update=select_simple)
    detailed_type: EnumProperty(name="Collision Type", items=DETAILED, default='MESH', update=select_detailed)
    simplification_ratio: FloatProperty(name='Ratio', description='Ratio of collision geometry to retain; changes apply only when Simplify Collision is pressed',default=1.0,min=0.0,max=1.0,precision=4)
    parent_to_asset: BoolProperty(name="Parent to Asset", description="Parent each collision to its asset while preserving its world transform", default=True)
    match_asset_collection: BoolProperty(name="Match Asset Collection", description="Link the collision only to the asset's first collection; otherwise use the active collection", default=True)
    wireframe_display: BoolProperty(name="Wireframe Display", description="Display generated collisions as wireframes", default=True)
    show_in_front: BoolProperty(name="Show in Front", description="Display collisions in front of other viewport objects", default=True)
    hide_from_render: BoolProperty(name="Hide from Render", description="Exclude generated collisions from rendering", default=True)
