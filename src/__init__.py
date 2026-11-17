# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Studio Lin Games
import bpy
from .properties import LIN_PG_settings
from .operators import LIN_OT_generate_ucx_collision
from .panels import LIN_PT_ucx_generator
from .simplification import LIN_OT_simplify_collision
from .management import CLASSES as MANAGEMENT_CLASSES

CLASSES = (LIN_PG_settings, LIN_OT_generate_ucx_collision, *MANAGEMENT_CLASSES, LIN_OT_simplify_collision, LIN_PT_ucx_generator)


@bpy.app.handlers.persistent
def sync_loaded_settings(_unused):
    from .properties import sync_method
    for scene in getattr(bpy.data,'scenes',()):
        sync_method(scene.lin_ucx_settings,None)


def sync_deferred():
    sync_loaded_settings(None)
    return None


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.lin_ucx_settings = bpy.props.PointerProperty(type=LIN_PG_settings)
    sync_loaded_settings(None)
    bpy.app.timers.register(sync_deferred,first_interval=0.1)
    bpy.app.handlers.load_post.append(sync_loaded_settings)


def unregister():
    if bpy.app.timers.is_registered(sync_deferred):
        bpy.app.timers.unregister(sync_deferred)
    if sync_loaded_settings in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(sync_loaded_settings)
    del bpy.types.Scene.lin_ucx_settings
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
