# SPDX-License-Identifier: GPL-3.0-or-later
import sys
from pathlib import Path
import unittest
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import src
from src import management, operators


class ExportSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): src.register()

    @classmethod
    def tearDownClass(cls): src.unregister()

    def setUp(self):
        for obj in list(bpy.data.objects): bpy.data.objects.remove(obj,do_unlink=True)
        self.settings = bpy.context.scene.lin_ucx_settings
        self.settings.collision_type = 'BOX'
        self.settings.parent_to_asset = True

    def asset(self):
        bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.object
        cs = operators.create_collisions_for_object(bpy.context,obj,self.settings)
        return obj,cs

    def select(self,*objects):
        for obj in bpy.context.selected_objects: obj.select_set(False)
        for obj in objects: obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0] if objects else None

    def run_selection(self): return bpy.ops.lin.select_asset_collisions()

    def test_asset_child_multiple_and_unparented(self):
        a,ca=self.asset();self.settings.parent_to_asset=False;b,cb=self.asset()
        for initial,expected,active in [((a,),[a,*ca],a),((ca[0],),[a,*ca],a),((a,b),[a,b,*ca,*cb],a),((cb[0],),[b,*cb],b)]:
            self.select(*initial)
            self.assertEqual(self.run_selection(),{'FINISHED'})
            self.assertEqual(set(bpy.context.selected_objects),set(expected))
            self.assertEqual(bpy.context.view_layer.objects.active,active)

    def test_hidden_reveal_and_locked_rollback(self):
        a,cs=self.asset();c=cs[0]
        self.select(a);c.hide_set(True)
        self.assertEqual(self.run_selection(),{'FINISHED'});self.assertFalse(c.hide_get())
        self.select(a);c.hide_set(True);c.hide_select=True
        self.assertEqual(self.run_selection(),{'CANCELLED'})
        self.assertTrue(c.hide_get());self.assertEqual(list(bpy.context.selected_objects),[a])
        self.assertEqual(bpy.context.view_layer.objects.active,a)

    def test_excluded_collection_and_global_hidden(self):
        a,cs=self.asset();c=cs[0]
        collection=bpy.data.collections.new('Excluded');bpy.context.scene.collection.children.link(collection)
        for owner in list(c.users_collection):owner.objects.unlink(c)
        collection.objects.link(c)
        bpy.context.view_layer.layer_collection.children[collection.name].exclude=True
        self.select(a)
        self.assertEqual(self.run_selection(),{'CANCELLED'})
        self.assertEqual(list(bpy.context.selected_objects),[a])
        self.assertTrue(bpy.context.view_layer.layer_collection.children[collection.name].exclude)
        bpy.context.view_layer.layer_collection.children[collection.name].exclude=False;c.hide_viewport=True
        self.assertEqual(self.run_selection(),{'CANCELLED'})
        self.assertTrue(c.hide_viewport)

    def test_no_collisions_empty_manual_ambiguous(self):
        self.select();self.assertEqual(self.run_selection(),{'CANCELLED'})
        bpy.ops.mesh.primitive_cube_add();empty=bpy.context.object
        self.assertEqual(self.run_selection(),{'CANCELLED'})
        a,cs=self.asset();manual=bpy.data.objects.new('UCX_'+a.name+'_99',cs[0].data)
        bpy.context.scene.collection.objects.link(manual)
        self.select(a);self.assertEqual(self.run_selection(),{'FINISHED'})
        self.assertNotIn(manual,list(bpy.context.selected_objects))
        duplicate=cs[0].copy();bpy.context.scene.collection.objects.link(duplicate)
        self.select(a);self.assertEqual(self.run_selection(),{'CANCELLED'})
        self.assertEqual(list(bpy.context.selected_objects),[a])

    def test_retired_method_migration_and_legacy_management(self):
        from src.properties import sync_method, SIMPLE, DETAILED
        self.assertNotIn('LOOSE_PARTS',[item[0] for item in SIMPLE+DETAILED])
        self.settings['collision_type']=5
        self.settings['simple_type']=5
        sync_method(self.settings,None)
        self.assertEqual(self.settings.collision_type,'CONVEX_HULL')
        self.assertEqual(self.settings.simple_type,'CONVEX_HULL')
        for raw,expected in ((6,'MESH'),(7,'SEGMENTED')):
            self.settings['collision_type']=raw
            sync_method(self.settings,None)
            self.assertEqual(self.settings.collision_type,expected)
        self.settings.collision_type='BOX'
        a,cs=self.asset()
        cs[0]['lin_ucx_method']='LOOSE_PARTS'
        self.select(cs[0]);self.assertEqual(self.run_selection(),{'FINISHED'})
        self.assertIn('legacy',management.statistics(a)['methods'])
        self.assertTrue(management.is_owned(cs[0],a))

    def test_undo(self):
        a,cs=self.asset();self.select(a)
        bpy.context.preferences.edit.use_global_undo=True
        bpy.ops.ed.undo_push(message='Before export selection')
        self.run_selection();bpy.ops.ed.undo_push(message='After export selection')
        self.assertEqual(len(bpy.context.selected_objects),2)
        bpy.ops.ed.undo();self.assertEqual(len(bpy.context.selected_objects),1)



if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ExportSelectionTests))
    if not result.wasSuccessful():raise SystemExit(1)
