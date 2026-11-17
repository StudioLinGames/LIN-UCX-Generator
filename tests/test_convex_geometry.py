# SPDX-License-Identifier: GPL-3.0-or-later
"""Additional 1.1.0 tests; the original ten tests remain unchanged."""
import importlib
import itertools
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
addon = importlib.import_module('src')
from src import geometry, operators, panels


class ConvexTests(unittest.TestCase):
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
        self.settings.collision_type = 'CONVEX_HULL'
        for prop in ('parent_to_asset', 'match_asset_collection', 'wireframe_display', 'show_in_front', 'hide_from_render'):
            setattr(self.settings, prop, True)

    def points_asset(self, points, edges=(), faces=(), name='SM_Test'):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(points, edges, faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        bpy.context.view_layer.update()
        return obj

    def boxes(self, boxes, name='SM_Test'):
        bm = bmesh.new()
        try:
            for center, size in boxes:
                result = bmesh.ops.create_cube(bm, size=2)
                for v in result['verts']:
                    v.co = Vector(tuple(v.co[i]*size[i] + center[i] for i in range(3)))
            mesh = bpy.data.meshes.new(name)
            bm.to_mesh(mesh)
        finally:
            bm.free()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        bpy.context.view_layer.update()
        return obj

    def generate(self, obj):
        bpy.context.view_layer.update()
        return operators.create_collisions_for_object(bpy.context, obj, self.settings)

    def assert_hull(self, collision, source_points=()):
        # Independent surface/containment assertions, in normalized coordinates
        # so tests cover tiny/large geometry without absolute world tolerances.
        bm = bmesh.new()
        try:
            bm.from_mesh(collision.data)
            points = [v.co.copy() for v in bm.verts]
            low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
            high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
            span = max(high-low)
            center = (low+high)/2
            for v in bm.verts:
                v.co = (v.co-center)/span
            bm.normal_update()
            self.assertTrue(all(e.is_manifold and len(e.link_faces) == 2 for e in bm.edges))
            self.assertTrue(all(v.link_faces for v in bm.verts))
            self.assertEqual(len(bm.verts)-len(bm.edges)+len(bm.faces), 2)
            self.assertGreater(bm.calc_volume(signed=True), 0)
            tests = [v.co for v in bm.verts] + [(Vector(p)-center)/span for p in source_points]
            for f in bm.faces:
                for p in tests:
                    self.assertLessEqual(f.normal.dot(p-f.verts[0].co), 3e-6)
        finally:
            bm.free()

    def contains(self, collision, world_point):
        local = collision.matrix_world.inverted() @ Vector(world_point)
        return all(p.normal.dot(local-collision.data.vertices[p.vertices[0]].co) <= 1e-5 for p in collision.data.polygons)

    def test_primitives(self):
        for primitive in ('cube', 'uv_sphere', 'cylinder'):
            with self.subTest(primitive=primitive):
                getattr(bpy.ops.mesh, f'primitive_{primitive}_add')()
                obj = bpy.context.object
                collision = self.generate(obj)[0]
                self.assert_hull(collision, [v.co for v in obj.data.vertices])

    def test_irregular_interior_duplicate_and_loose_points(self):
        points = [(-1,-1,-1), (2,-1,-1), (0,3,-1), (0,0,4), (0,0,0), (0,0,0), (0.1,0,0)]
        obj = self.points_asset(points, edges=[(4,6)])
        collision = self.generate(obj)[0]
        self.assertEqual(len(collision.data.vertices), 4)
        self.assert_hull(collision, points)
        # Single hull includes loose input points; it never leaves loose output.
        boundary_points = list(itertools.product((-1,1), repeat=3)) + [(0,0,0), (1,0,0), (1,1,0)]
        obj = self.points_asset(boundary_points)
        self.assert_hull(self.generate(obj)[0], boundary_points)

    def test_scale_extremes(self):
        for scale in (1e-9, 1e-5, 1e5, 1e9):
            with self.subTest(scale=scale):
                points = [tuple(scale*x for x in p) for p in itertools.product((-1,1), repeat=3)]
                obj = self.points_asset(points)
                collision = self.generate(obj)[0]
                self.assert_hull(collision, points)

    def test_invalid_point_sets(self):
        cases = [[], [(0,0,0)]*8, [(0,0,0),(1,0,0),(0,1,0)],
                 [(0,0,0),(1,0,0),(0,1,0),(0,1,0)],
                 [(i,0,0) for i in range(5)],
                 [(x,y,0) for x,y in itertools.product((-1,1), repeat=2)],
                 [(0,0,0),(1,0,0),(0,1,0),(math.nan,0,1)],
                 [(0,0,0),(1,0,0),(0,1,0),(math.inf,0,1)]]
        for points in cases:
            with self.subTest(points=points), self.assertRaises(ValueError):
                geometry.create_convex_hull(points)

    def test_transforms_modifiers_and_source_unchanged(self):
        for method in ('CONVEX_HULL',):
            for scale in ((1,1,1), (2,2,2), (2,0.5,3), (-2,0.5,3)):
                with self.subTest(method=method, scale=scale):
                    self.settings.collision_type = method
                    obj = self.boxes([((3,2,1),(1,2,3))])
                    obj.location = (5,6,7)
                    obj.rotation_euler = (0.4,0.2,0.7)
                    obj.scale = scale
                    parent = bpy.data.objects.new('Parent', None)
                    bpy.context.scene.collection.objects.link(parent)
                    parent.scale = (1,2,3)
                    obj.parent = parent
                    mod = obj.modifiers.new('Bevel', 'BEVEL')
                    mod.width = 0.2
                    bpy.context.view_layer.update()
                    before = ([tuple(v.co) for v in obj.data.vertices], obj.matrix_world.copy())
                    collision = self.generate(obj)[0]
                    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
                    inverse = collision.matrix_world.inverted()
                    points = [inverse @ obj.matrix_world @ v.co for v in evaluated.data.vertices]
                    self.assert_hull(collision, points)
                    self.assertLess((collision.matrix_world.translation-obj.matrix_world.translation).length, 1e-5)
                    self.assertEqual(before, ([tuple(v.co) for v in obj.data.vertices], obj.matrix_world))








    def test_legacy_duplicate_and_similar_names(self):
        obj = self.boxes([((0,0,0),(1,1,1))], name='SM_Rock')
        similar = self.boxes([((0,0,0),(1,1,1))], name='SM_Rock_01')
        existing = bpy.data.objects.new('UCX_SM_Rock_01', None)
        bpy.context.scene.collection.objects.link(existing)
        self.assertFalse(operators.has_existing_collisions(obj))
        self.assertTrue(operators.has_existing_collisions(similar))
        existing.name = 'UCX_SM_Rock_00'
        self.assertTrue(operators.has_existing_collisions(obj))
        existing.name = 'UCX_SM_Rock_extra'
        self.assertFalse(operators.has_existing_collisions(obj))
        existing.name = 'UCX_SM_Rock'
        self.assertIsNone(self.generate(obj))



    def test_long_utf8_names_cleanup(self):
        obj = self.boxes([((0,0,0),(1,1,1))], name='é'*300)
        before = (len(bpy.data.objects), len(bpy.data.meshes))
        # Input is already at Blender's name capacity; the UCX prefix must fail.
        with self.assertRaises(ValueError):
            self.generate(obj)
        self.assertEqual(before, (len(bpy.data.objects), len(bpy.data.meshes)))

    def test_options_and_degenerate_transforms(self):
        collection = bpy.data.collections.new('ConvexAssets')
        bpy.context.scene.collection.children.link(collection)
        for method in ('CONVEX_HULL',):
            for enabled in (False, True):
                self.settings.collision_type = method
                obj = self.boxes([((0,0,0),(1,1,1))])
                bpy.context.scene.collection.objects.unlink(obj)
                collection.objects.link(obj)
                for prop in ('parent_to_asset','match_asset_collection','wireframe_display','show_in_front','hide_from_render'):
                    setattr(self.settings, prop, enabled)
                collision = self.generate(obj)[0]
                self.assertEqual(collision.parent, obj if enabled else None)
                self.assertEqual(tuple(collision.users_collection), (collection if enabled else bpy.context.collection,))
                self.assertEqual(collision.display_type, 'WIRE' if enabled else 'SOLID')
                self.assertEqual(collision.show_in_front, enabled)
                self.assertEqual(collision.hide_render, enabled)
                bad = self.boxes([((0,0,0),(1,1,1))])
                bad.scale.z = 0
                with self.assertRaises(ValueError):
                    self.generate(bad)





    def test_panel_label_and_dynamic_descriptions(self):
        # Exercise draw with a recording layout; visual UI inspection is separate.
        for method in ('BOX','CONVEX_HULL'):
            calls = []
            class Layout:
                def label(self, **kwargs): calls.append(('label',kwargs))
                def prop(self, *args, **kwargs): calls.append(('prop',kwargs))
                def column(self, **kwargs): return self
                def row(self): return self
                def operator(self, *args, **kwargs): return SimpleNamespace()
                def separator(self): pass
            self.settings.collision_type = method
            context = SimpleNamespace(scene=bpy.context.scene, selected_objects=[], region=SimpleNamespace(width=160), preferences=bpy.context.preferences)
            panels.LIN_PT_ucx_generator.draw(SimpleNamespace(layout=Layout()), context)
            self.assertIn(('label', {'text':'Collision Type'}), calls)
            self.assertIn(('prop', {'text':''}), calls)
            self.assertIn(('label', {'text':'Version 1.4.1'}), calls)
            self.assertTrue(any('Generate' in c[1].get('text','') for c in calls))



result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ConvexTests))
if not result.wasSuccessful():
    raise SystemExit(1)
