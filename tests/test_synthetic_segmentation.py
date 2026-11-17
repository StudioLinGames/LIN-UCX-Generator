import sys, math, itertools
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import src
from src import operators,geometry,management
from src.segmentation import generate_segmented_geometry
src.register()
def mesh_object(vertices, faces, name='Test'):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices,[],faces)
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(mesh)
    finally:
        bm.free()
    obj = bpy.data.objects.new(name,mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    return obj


def voxel_asset(cells, name='VoxelAsset'):
    # Shared indexed vertices and removal of internal faces: truly connected solid.
    corners = [(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]
    boundary = {}
    for cell in cells:
        verts = [tuple(cell[i]+c[i] for i in range(3)) for c in corners]
        for face in operators.FACES:
            coords = tuple(verts[i] for i in face)
            key = tuple(sorted(coords))
            if key in boundary:
                del boundary[key]
            else:
                boundary[key] = coords
    vertices, lookup, faces = [], {}, []
    for coords in boundary.values():
        face = []
        for p in coords:
            if p not in lookup:
                lookup[p] = len(vertices)
                vertices.append(p)
            face.append(lookup[p])
        faces.append(face)
    return mesh_object(vertices,faces,name)



def contains(c,p):
 p=c.matrix_world.inverted() @ Vector(p)
 return all(f.normal.dot(p-c.data.vertices[f.vertices[0]].co)<1e-5 for f in c.data.polygons)
settings=bpy.context.scene.lin_ucx_settings
for name,cells in {'Door':[(x,0,z) for x in range(5) for z in range(5) if x in (0,4) or z==4], 'Window':[(x,0,z) for x in range(5) for z in range(5) if x in (0,4) or z in (0,4)], 'L':[(0,0,0),(0,0,1),(1,0,0)],'U':[(x,0,z) for x in range(3) for z in range(3) if x in (0,2) or z==0],'Stairs':[(x,0,z) for x in range(3) for z in range(x+1)],'Components':[(0,0,0),(4,0,0)]}.items():
 obj=voxel_asset(cells,name)
 settings.collision_type='SEGMENTED'
 cs=operators.create_collisions_for_object(bpy.context,obj,settings)
 for c in cs: geometry.validate_convex_geometry([v.co for v in c.data.vertices],[tuple(f.vertices) for f in c.data.polygons])
 if name in ('Door','Window'):
  for p in itertools.product((1.25,2.5,3.75),(0.1,0.5,0.9),(1.25,2.5,3.75)):
   assert not any(contains(c,p) for c in cs)
 for x,y,z in cells: assert any(contains(c,(x+.5,y+.5,z+.5)) for c in cs)
 print('SEGMENTS',name,len(cs),sum(len(c.data.vertices) for c in cs),sum(len(c.data.polygons) for c in cs),flush=True)
# 36-vertex semicircular solid arch, one connected source.
outline=[(3*math.cos(i*math.pi/8),3*math.sin(i*math.pi/8)) for i in range(9)]+[(2*math.cos(i*math.pi/8),2*math.sin(i*math.pi/8)) for i in reversed(range(9))]
n=len(outline);v=[(x,y,z) for y in (0,1) for x,z in outline];f=[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
obj=mesh_object(v,f,'Arch36');cs=operators.create_collisions_for_object(bpy.context,obj,settings)
for x,y,z in itertools.product((-1.0,-.5,0,.5,1),(.1,.5,.9),(.2,.6,1)):
 assert not any(contains(c,(x,y,z)) for c in cs)
print('ARCH',len(cs),sum(len(c.data.vertices) for c in cs),sum(len(c.data.polygons) for c in cs),flush=True)
for c in bpy.context.selected_objects:c.select_set(False)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3);obj=bpy.context.object;settings.collision_type='MESH';cs=operators.create_collisions_for_object(bpy.context,obj,settings)
base=[tuple(v.co) for v in obj.data.vertices]
for ratio in (1,.75,.5,.25,.1,0,1):
 settings.simplification_ratio=ratio
 result=bpy.ops.lin.simplify_collision()
 assert [tuple(v.co) for v in obj.data.vertices]==base
 assert len(cs[0].modifiers)<=1
 print('SIMPLIFY',ratio,result,management.statistics(obj),flush=True)
src.unregister();src.register();src.unregister()
print('PASS')
