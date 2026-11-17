# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Studio Lin Games
"""Convex geometry based on the Studio Lin Games 1.1.0 reference module.

Hull construction and validation use centered unit-span coordinates so tolerances
are relative to each component, independent of the asset's units or location.
"""
import math
import bmesh
from mathutils import Vector

MERGE_TOLERANCE = 1e-7
PLANE_TOLERANCE = 2e-6


def _normalized(points):
    points = [tuple(p) for p in points]
    if not points:
        raise ValueError("Empty evaluated mesh")
    if any(len(p) != 3 or not all(math.isfinite(c) for c in p) for p in points):
        raise ValueError("Non-finite or invalid vertex coordinates")
    low = tuple(min(p[i] for p in points) for i in range(3))
    high = tuple(max(p[i] for p in points) for i in range(3))
    span = max(high[i] - low[i] for i in range(3))
    if not math.isfinite(span) or span <= 0:
        raise ValueError("Coincident points cannot form a convex volume")
    center = tuple(low[i] + (high[i] - low[i]) / 2 for i in range(3))
    return [Vector(tuple((p[i] - center[i]) / span for i in range(3))) for p in points], center, span


def _check_dimension(points):
    if len(points) < 4:
        raise ValueError("At least four unique points are required")
    origin = points[0]
    direction = max((p - origin for p in points), key=lambda p: p.length_squared)
    normal = max((direction.cross(p - origin) for p in points), key=lambda p: p.length_squared)
    if normal.length <= MERGE_TOLERANCE * direction.length:
        raise ValueError("Cannot generate a convex hull from collinear geometry")
    normal.normalize()
    if max(abs(normal.dot(p - origin)) for p in points) <= MERGE_TOLERANCE:
        raise ValueError("Cannot generate a convex hull from coplanar geometry")


def _validate_surface(bm, contained_points=None):
    if (not bm.faces or not bm.edges or
            any(not edge.is_manifold for edge in bm.edges) or
            any(not vertex.link_faces for vertex in bm.verts)):
        raise ValueError("Convex hull is not a closed manifold volume")
    # A manifold check alone would allow multiple disconnected closed shells.
    pending = [next(iter(bm.faces))]
    visited = set(pending)
    while pending:
        face = pending.pop()
        for edge in face.edges:
            for neighbour in edge.link_faces:
                if neighbour not in visited:
                    visited.add(neighbour)
                    pending.append(neighbour)
    if len(visited) != len(bm.faces):
        raise ValueError("Convex hull contains disconnected surfaces")
    bm.normal_update()
    volume = bm.calc_volume(signed=True)
    if not math.isfinite(volume) or volume <= 1e-10:
        raise ValueError("Convex hull has zero or numerically degenerate volume")
    vertices = [tuple(v.co) for v in bm.verts]
    convexity, containment = surface_deviations(vertices, [tuple(tuple(v.co) for v in f.verts) for f in bm.faces], contained_points)
    if convexity > PLANE_TOLERANCE:
        raise ValueError(f'Hull convexity validation failed (deviation={convexity:.9g}, tolerance={PLANE_TOLERANCE})')
    if containment > PLANE_TOLERANCE:
        raise ValueError(f'Source containment validation failed (deviation={containment:.9g}, tolerance={PLANE_TOLERANCE})')


def _sub(a,b): return tuple(a[i]-b[i] for i in range(3))
def _cross(a,b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def _dot(a,b): return math.fsum(x*y for x,y in zip(a,b))


def surface_deviations(vertices, polygons, source=None):
    """Supporting planes computed in Python double precision, in normalized space."""
    convexity = containment = 0.0
    for p in polygons:
        o = p[0]
        n = max((_cross(_sub(p[i],o),_sub(p[i+1],o)) for i in range(1,len(p)-1)),key=lambda n:_dot(n,n))
        length = math.sqrt(_dot(n,n))
        if not math.isfinite(length) or length == 0:
            raise ValueError('Degenerate geometry: zero-area hull face')
        n = tuple(x/length for x in n)
        convexity = max(convexity,max(_dot(n,_sub(v,o)) for v in vertices))
        if source is not None:
            containment = max(containment,max(_dot(n,_sub(v,o)) for v in source))
    return convexity,containment


def _double_hull(points):
    """Incremental supporting-plane hull, used only after the native route fails.

    Arithmetic remains double until the resulting local vertices are stored.
    No grid snapping, source-specific constants, tolerance inflation or fallback box.
    """
    low = tuple(min(p[i] for p in points) for i in range(3))
    high = tuple(max(p[i] for p in points) for i in range(3))
    span = max(high[i]-low[i] for i in range(3))
    center = tuple(low[i]+(high[i]-low[i])/2 for i in range(3))
    ps = [tuple((p[i]-center[i])/span for i in range(3)) for p in points]
    a = 0
    b = max(range(len(ps)),key=lambda i:_dot(_sub(ps[i],ps[a]),_sub(ps[i],ps[a])))
    c = max(range(len(ps)),key=lambda i:_dot(_cross(_sub(ps[b],ps[a]),_sub(ps[i],ps[a])),_cross(_sub(ps[b],ps[a]),_sub(ps[i],ps[a]))))
    normal = _cross(_sub(ps[b],ps[a]),_sub(ps[c],ps[a]))
    d = max(range(len(ps)),key=lambda i:abs(_dot(normal,_sub(ps[i],ps[a]))))
    if len({a,b,c,d})<4 or abs(_dot(normal,_sub(ps[d],ps[a])))<=1e-14:
        raise ValueError('Insufficient three-dimensional geometry')
    inside = tuple(sum(ps[j][i] for j in (a,b,c,d))/4 for i in range(3))
    def oriented(face):
        x,y,z = (ps[i] for i in face)
        return tuple(reversed(face)) if _dot(_cross(_sub(y,x),_sub(z,x)),_sub(inside,x))>0 else face
    faces = [oriented(f) for f in ((a,b,c),(a,d,b),(b,d,c),(c,d,a))]
    for index,p in enumerate(ps):
        visible = []
        for face in faces:
            x,y,z = (ps[i] for i in face)
            n = _cross(_sub(y,x),_sub(z,x))
            if _dot(n,_sub(p,x)) > 1e-12*math.sqrt(_dot(n,n)):
                visible.append(face)
        if not visible: continue
        horizon = {}
        for face in visible:
            for x,y in zip(face,face[1:]+face[:1]):
                key = tuple(sorted((x,y)))
                if key in horizon: del horizon[key]
                else: horizon[key]=(x,y)
        faces = [f for f in faces if f not in visible]
        faces.extend(oriented((x,y,index)) for x,y in horizon.values())
    used = sorted({i for f in faces for i in f})
    lookup = {v:i for i,v in enumerate(used)}
    vertices = [points[i] for i in used]
    faces = [tuple(lookup[i] for i in f) for f in faces]
    try:
        validate_convex_geometry(vertices,faces)
    except ValueError:
        vertices,faces = _create_convex_hull(vertices)
    # Independent source containment in a common normalization frame.
    check = [tuple((v[i]-center[i])/span for i in range(3)) for v in vertices]
    convexity,containment = surface_deviations(check,[[check[i] for i in f] for f in faces],ps)
    if max(convexity,containment)>PLANE_TOLERANCE:
        raise ValueError(f'Hull reconstruction validation failed ({convexity}, {containment})')
    return vertices,faces


def validate_convex_geometry(vertices, faces):
    """Check transformed output at its own scale, without repairing its winding."""
    points, _center, _span = _normalized(vertices)
    bm = bmesh.new()
    try:
        verts = [bm.verts.new(p) for p in points]
        for face in faces:
            bm.faces.new([verts[i] for i in face])
        _validate_surface(bm)
    finally:
        bm.free()


def _create_convex_hull(points):
    """Return local vertices/faces of a closed, outward, convex hull."""
    normalized, center, span = _normalized(points)
    if len(normalized) < 4:
        raise ValueError("At least four points are required")
    bm = bmesh.new()
    try:
        for point in normalized:
            bm.verts.new(point)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=MERGE_TOLERANCE)
        _check_dimension([v.co for v in bm.verts])
        result = bmesh.ops.convex_hull(bm, input=list(bm.verts), use_existing_faces=False)
        # Both result slots can contain interior input vertices. Start from the
        # actual output faces, then discard every element not used by that shell.
        hull_faces = {f for f in result['geom'] if isinstance(f, bmesh.types.BMFace)}
        extra_faces = [f for f in bm.faces if f not in hull_faces]
        if extra_faces:
            bmesh.ops.delete(bm, geom=extra_faces, context='FACES_ONLY')
        unused = {v for key in ('geom_unused', 'geom_interior')
                  for v in result.get(key, [])
                  if isinstance(v, bmesh.types.BMVert) and v.is_valid and not v.link_faces}
        unused.update(v for v in bm.verts if not v.link_faces)
        if unused:
            bmesh.ops.delete(bm, geom=list(unused), context='VERTS')
        loose_edges = [e for e in bm.edges if not e.link_faces]
        if loose_edges:
            bmesh.ops.delete(bm, geom=loose_edges, context='EDGES')
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        if bm.calc_volume(signed=True) < 0:
            bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
        _validate_surface(bm, normalized)
        bm.verts.index_update()
        vertices = [tuple(v.co[i] * span + center[i] for i in range(3)) for v in bm.verts]
        faces = [tuple(v.index for v in face.verts) for face in bm.faces]
        return vertices, faces
    finally:
        bm.free()


def create_convex_hull(points):
    points = [tuple(p) for p in points]
    try:
        return _create_convex_hull(points)
    except ValueError as original:
        normalized, center, span = _normalized(points)
        for step in (1e-7, 1e-6):
            snapped = [tuple(round(c/step)*step for c in p) for p in normalized]
            try:
                vertices, faces = _create_convex_hull(snapped)
                bm = bmesh.new()
                try:
                    verts = [bm.verts.new(v) for v in vertices]
                    for f in faces: bm.faces.new([verts[i] for i in f])
                    _validate_surface(bm,normalized)
                finally: bm.free()
                return [tuple(v[i]*span+center[i] for i in range(3)) for v in vertices],faces
            except ValueError:
                continue
        return _double_hull(points)


def get_connected_components(mesh):
    """Find edge-connected components in stable vertex-index order."""
    adjacency = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].append(b)
        adjacency[b].append(a)
    visited = set()
    components = []
    for vertex in mesh.vertices:
        start = vertex.index
        if start in visited:
            continue
        stack = [start]
        visited.add(start)
        component = []
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbour in adjacency[current]:
                if neighbour not in visited:
                    visited.add(neighbour)
                    stack.append(neighbour)
        components.append(component)
    return components


def generate_convex_geometry(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        if mesh is None:
            raise ValueError("No evaluated mesh")
        return create_convex_hull([v.co.copy() for v in mesh.vertices])
    finally:
        evaluated.to_mesh_clear()


