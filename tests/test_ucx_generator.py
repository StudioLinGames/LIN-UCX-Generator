# SPDX-License-Identifier: GPL-3.0-or-later
"""Run with blender --background --factory-startup --python-exit-code 1 --python tests/test_ucx_generator.py."""
import importlib
import itertools
from pathlib import Path
import sys
import unittest

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
addon = importlib.import_module('src')
from src.operators import create_ucx_for_object, MIN_THICKNESS


class GeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        addon.register()

    @classmethod
    def tearDownClass(cls):
        addon.unregister()

    def setUp(self):
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        self.settings = bpy.context.scene.lin_ucx_settings
        for prop in ('parent_to_asset', 'match_asset_collection', 'wireframe_display', 'show_in_front', 'hide_from_render'):
            setattr(self.settings, prop, True)

    def asset(self, name='SM_Test', flat=False, empty=False):
        mesh = bpy.data.meshes.new(name)
        if not empty:
            mesh.from_pydata(list(itertools.product((-1, 3), (-2, 4), (0,) if flat else (-3, 5))), [], [])
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        bpy.context.view_layer.update()
        return obj

    def assert_fit(self, obj, collision):
        bpy.context.view_layer.update()
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        bounds = [Vector(c) for c in evaluated.bound_box]
        lo = Vector(tuple(min(v[i] for v in bounds) for i in range(3)))
        hi = Vector(tuple(max(v[i] for v in bounds) for i in range(3)))
        center = (lo + hi) / 2
        size = Vector(tuple(max(hi[i] - lo[i], MIN_THICKNESS) for i in range(3)))
        expected = [obj.matrix_world @ (center + Vector(tuple(s[i]*size[i]/2 for i in range(3)))) for s in itertools.product((-1, 1), repeat=3)]
        actual = [collision.matrix_world @ v.co for v in collision.data.vertices]
        self.assertEqual(len(actual), 8)
        for point in expected:
            self.assertLess(min((point-v).length for v in actual), 0.0001)
        self.assertLess((collision.matrix_world.translation - obj.matrix_world.translation).length, 0.0001)
        self.assertEqual(len(collision.data.polygons), 6)
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(collision.data)
        self.assertTrue(all(e.is_manifold for e in bm.edges))
        self.assertGreater(bm.calc_volume(signed=True), 0)
        bm.free()

    def test_geometry_transforms(self):
        for scale, rotation, flat in [((1,1,1),(0,0,0),False), ((2,2,2),(0,0,0),False), ((2,3,0.5),(0.4,0.7,0.1),False), ((-2,3,0.5),(0.4,0.7,0.1),False), ((-2,-3,-0.5),(0,0,0),False), ((1,1,1),(0,0,0),True)]:
            with self.subTest(scale=scale, rotation=rotation, flat=flat):
                obj = self.asset('SM_Geometry', flat=flat)
                obj.location = (7,-4,2)
                obj.rotation_euler = rotation
                obj.scale = scale
                bpy.context.view_layer.update()
                original = [v.co.copy() for v in obj.data.vertices]
                collision = create_ucx_for_object(bpy.context, obj, self.settings)
                self.assert_fit(obj, collision)
                self.assertEqual(original, [v.co for v in obj.data.vertices])
                self.assertEqual(collision.name, 'UCX_' + obj.name)
                self.assertEqual(collision.parent, obj)

    def test_cube_and_modifier(self):
        bpy.ops.mesh.primitive_cube_add(size=2)
        obj = bpy.context.object
        modifier = obj.modifiers.new('Expand', 'SOLIDIFY')
        modifier.thickness = 0.7
        bpy.context.view_layer.update()
        self.assert_fit(obj, create_ucx_for_object(bpy.context, obj, self.settings))

    def test_shear_and_parent_follow(self):
        obj = self.asset()
        parent = self.asset('Parent')
        parent.scale = (2,3,1)
        obj.parent = parent
        obj.rotation_euler = (0.2,0.3,0.5)
        bpy.context.view_layer.update()
        collision = create_ucx_for_object(bpy.context, obj, self.settings)
        self.assert_fit(obj, collision)
        obj.location.x += 3
        self.assert_fit(obj, collision)

    def test_options_collections(self):
        collection = bpy.data.collections.new('AssetCollection')
        bpy.context.scene.collection.children.link(collection)
        for parent in (False, True):
            for match in (False, True):
                obj = self.asset('SM_Options')
                bpy.context.scene.collection.objects.unlink(obj)
                collection.objects.link(obj)
                self.settings.parent_to_asset = parent
                self.settings.match_asset_collection = match
                self.settings.wireframe_display = False
                self.settings.hide_from_render = False
                self.settings.show_in_front = False
                collision = create_ucx_for_object(bpy.context, obj, self.settings)
                self.assertEqual(collision.parent, obj if parent else None)
                self.assertEqual(tuple(collision.users_collection), (collection if match else bpy.context.collection,))
                self.assertEqual(collision.display_type, 'SOLID')
                self.assertFalse(collision.hide_render)
                self.assertFalse(collision.show_in_front)
                self.assert_fit(obj, collision)

    def test_duplicate_operator_selection(self):
        assets = [self.asset('SM_A'), self.asset('SM_B')]
        existing = create_ucx_for_object(bpy.context, assets[0], self.settings)
        for obj in assets + [existing]:
            obj.select_set(True)
        light = bpy.data.objects.new('Light', bpy.data.lights.new('Light', 'POINT'))
        bpy.context.scene.collection.objects.link(light)
        light.select_set(True)
        self.assertEqual(bpy.ops.lin.generate_ucx_collision(), {'FINISHED'})
        self.assertEqual(len([o for o in bpy.data.objects if o.name.startswith('UCX_')]), 2)
        self.assertEqual(bpy.ops.lin.generate_ucx_collision(), {'CANCELLED'})
        self.assertEqual(bpy.context.view_layer.objects.active, assets[0])
        self.assertTrue(existing.display_type == 'WIRE' and existing.hide_render and existing.show_in_front)

    def test_empty_and_degenerate_cleanup(self):
        for obj in (self.asset('Empty', empty=True), self.asset('ZeroScale')):
            if obj.name == 'ZeroScale':
                obj.scale.z = 0
                bpy.context.view_layer.update()
            before = (len(bpy.data.objects), len(bpy.data.meshes))
            with self.assertRaises(ValueError):
                create_ucx_for_object(bpy.context, obj, self.settings)
            self.assertEqual(before, (len(bpy.data.objects), len(bpy.data.meshes)))

    def test_link_failure_cleanup(self):
        obj = self.asset()
        class BrokenLinks:
            def link(self, unused):
                raise RuntimeError('Simulated collection link failure')
        class BrokenCollection:
            objects = BrokenLinks()
        class Context:
            collection = BrokenCollection()
            evaluated_depsgraph_get = bpy.context.evaluated_depsgraph_get
        self.settings.match_asset_collection = False
        before = (len(bpy.data.objects), len(bpy.data.meshes))
        with self.assertRaises(RuntimeError):
            create_ucx_for_object(Context(), obj, self.settings)
        self.assertEqual(before, (len(bpy.data.objects), len(bpy.data.meshes)))

    def test_no_valid_selection(self):
        self.assertEqual(bpy.ops.lin.generate_ucx_collision(), {'CANCELLED'})
        obj = self.asset('UCX_Accidental')
        obj.select_set(True)
        self.assertEqual(bpy.ops.lin.generate_ucx_collision(), {'CANCELLED'})

    def test_registration_cycle(self):
        addon.unregister()
        self.assertFalse(hasattr(bpy.types.Scene, 'lin_ucx_settings'))
        addon.register()
        self.assertTrue(bpy.context.scene.lin_ucx_settings.parent_to_asset)

    def test_undo(self):
        obj = self.asset()
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.context.preferences.edit.use_global_undo = True
        bpy.ops.ed.undo_push(message='Before UCX')
        bpy.ops.lin.generate_ucx_collision()
        bpy.ops.ed.undo_push(message='After UCX')
        self.assertIn('UCX_SM_Test', bpy.data.objects)
        bpy.ops.ed.undo()
        self.assertNotIn('UCX_SM_Test', bpy.data.objects)
        bpy.ops.ed.redo()
        self.assertIn('UCX_SM_Test', bpy.data.objects)


suite = unittest.defaultTestLoader.loadTestsFromTestCase(GeneratorTests)
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
