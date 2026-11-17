import sys,math,random,json
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import src
from src import geometry,operators,management
src.register()
def metrics(vertices,faces,source):
 def sub(a,b):return tuple(a[i]-b[i] for i in range(3))
 def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
 def dot(a,b):return math.fsum(x*y for x,y in zip(a,b))
 result={'convexity':0,'containment':0,'float_convexity':0,'float_containment':0,'min_area':1e100,'tolerance':geometry.PLANE_TOLERANCE}
 bm=bmesh.new();vs=[bm.verts.new(v) for v in vertices]
 try:
  for f in faces:bm.faces.new([vs[i] for i in f])
  bm.normal_update();result.update(vertices=len(vs),faces=len(bm.faces),nonmanifold=sum(not e.is_manifold for e in bm.edges),volume=bm.calc_volume(signed=True),degenerate=sum(f.calc_area()==0 for f in bm.faces))
  for f in bm.faces:
   p=[tuple(v.co) for v in f.verts];o=p[0];normals=[cross(sub(p[i],o),sub(p[i+1],o)) for i in range(1,len(p)-1)];n=max(normals,key=lambda n:dot(n,n));length=math.sqrt(dot(n,n));result['min_area']=min(result['min_area'],length/2)
   if length==0:continue
   n=tuple(x/length for x in n)
   for label,pts in [('convexity',vertices),('containment',source)]:
    result[label]=max(result[label],max(dot(n,sub(v,o)) for v in pts))
    from mathutils import Vector
    result['float_'+label]=max(result['float_'+label],max(f.normal.dot(Vector(v)-f.verts[0].co) for v in pts))
 finally:bm.free()
 return result

results=[]
# Predeclared holdout seeds, not used during implementation.
datasets = [('final_holdout',range(3001,3011))] if '--holdout' in sys.argv else [('development',range(11,16)),('validation_used_during_debug',range(1001,1011))]
for phase,seeds in datasets:
 for seed in seeds:
  rng=random.Random(seed)
  for kind in ('box','triangular_prism','trapezoid','cone','cylinder','barrel','rock','thin','overlap','near_planar'):
   n=3 if kind=='triangular_prism' else (4 if kind in ('box','trapezoid') else 16)
   scale=(1e-4,1,1e4)[seed%3];offset=scale*(seed%7)*100
   points=[]
   for j in range(3 if kind=='barrel' else 2):
    for i in range(n):
     angle=2*math.pi*i/n;radius=(.8 if j!=1 else 1) if kind=='barrel' else 1
     if kind=='cone' and j==1:radius=0
     if kind=='rock':radius*=rng.uniform(.7,1.2)
     thickness=1e-3 if kind in ('thin','near_planar') else 1
     points.append((offset+scale*radius*math.cos(angle),scale*radius*math.sin(angle),scale*thickness*j))
   if kind in ('overlap','near_planar'):points+=points[:4]
   # Store as real Blender float coordinates, then compare resulting world geometry.
   mesh=bpy.data.meshes.new('Synthetic');mesh.from_pydata(points,[],[tuple(range(n)),tuple(range(n,len(points)))]);obj=bpy.data.objects.new('Synthetic',mesh);bpy.context.scene.collection.objects.link(obj)
   obj.scale=(-2,.7,1.3);obj.rotation_euler=(.1,.3,.5);obj.location=(2,-3,1);bpy.context.view_layer.update()
   source=[tuple(v.co) for v in mesh.vertices]
   lo=tuple(min(p[i] for p in source) for i in range(3));hi=tuple(max(p[i] for p in source) for i in range(3));span=max(hi[i]-lo[i] for i in range(3));center=tuple(lo[i]+(hi[i]-lo[i])/2 for i in range(3))
   original=[tuple(v.co) for v in mesh.vertices];matrix=obj.matrix_world.copy()
   for method in ('CONVEX_HULL','MESH'):
    src_settings=bpy.context.scene.lin_ucx_settings;src_settings.collision_type=method
    cs=[]
    try:
     cs=operators.create_collisions_for_object(bpy.context,obj,src_settings)
     c=cs[0]
     verts=[tuple(v.co) for v in c.data.vertices]
     lo2=tuple(min(p[i] for p in verts) for i in range(3));hi2=tuple(max(p[i] for p in verts) for i in range(3));span2=max(hi2[i]-lo2[i] for i in range(3));center2=tuple(lo2[i]+(hi2[i]-lo2[i])/2 for i in range(3))
     baked=operators._transform(obj)[2]
     ps2=[tuple(math.fsum(float(baked[i][j])*float(v.co[j]) for j in range(3)) for i in range(3)) for v in mesh.vertices]
     vs=[tuple((v[i]-center2[i])/span2 for i in range(3)) for v in verts];ps=[tuple((v[i]-center2[i])/span2 for i in range(3)) for v in ps2]
     metric=metrics(vs,[tuple(f.vertices) for f in c.data.polygons],ps)
     assert metric['volume']>0 and metric['nonmanifold']==0 and metric['degenerate']==0
     metric['storage_bound']=max(2e-6,16*(2**-24)*max(abs(x) for v in verts for x in v)/span2)
     assert metric['convexity']<=2e-6 and metric['containment']<=metric['storage_bound'],metric
     assert c.name=='UCX_'+obj.name
     results.append(dict(phase=phase,seed=seed,kind=kind,method=method,result='OK',metrics=metric))
    except Exception as exc:results.append(dict(phase=phase,seed=seed,kind=kind,method=method,error=str(exc)))
    finally:management.remove_objects(cs or [])
   assert original==[tuple(v.co) for v in mesh.vertices] and obj.matrix_world==matrix
   bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
for points in ([],[(0,0,0)]*8,[(i,0,0) for i in range(8)],[(0,0,0),(1,0,0),(0,1,0),(1,1,0)]):
 try:geometry.create_convex_hull(points)
 except ValueError:pass
 else:raise AssertionError('Degenerate source accepted')
(ROOT/'tests/results').mkdir(parents=True,exist_ok=True)
(ROOT/'tests/results'/('synthetic141_'+('holdout_' if '--holdout' in sys.argv else '')+str(bpy.app.version[:2])+'.json')).write_text(json.dumps(results,indent=2))
failures=[r for r in results if 'error' in r];print('SYNTHETIC',len(results),'FAILURES',len(failures),failures[:5])
if failures:raise SystemExit(1)

