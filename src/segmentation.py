# SPDX-License-Identifier: GPL-3.0-or-later

import math
import time
import time
import bmesh

from mathutils import Vector


# Internal safety limits.
# These are not user-facing settings.

MAX_SEGMENTS = 32
MAX_CANDIDATES = 32
MAX_DEPTH = 16
_DEADLINE = 0

EPSILON = 1e-6
CONVEX_TOLERANCE = 1e-5
VOLUME_TOLERANCE = 1e-4


class SegmentationError(RuntimeError):
    pass


def make_bmesh(vertices, faces):

    bm = bmesh.new()

    try:

        verts = [
            bm.verts.new(Vector(co))
            for co in vertices
        ]

        for face in faces:

            bm.faces.new([
                verts[index]
                for index in face
            ])

        bm.normal_update()

        if bm.faces:

            bmesh.ops.recalc_face_normals(
                bm,
                faces=list(bm.faces)
            )

        bm.normal_update()

        return bm

    except Exception:

        bm.free()
        raise


def extract_geometry(bm, selected_faces=None):

    faces = (
        list(bm.faces)
        if selected_faces is None
        else list(selected_faces)
    )

    used = {
        vert
        for face in faces
        for vert in face.verts
    }

    ordered = [
        vert for vert in bm.verts
        if vert in used
    ]

    indices = {
        vert: index
        for index, vert in enumerate(ordered)
    }

    vertices = [
        tuple(vert.co)
        for vert in ordered
    ]

    polygons = [
        tuple(
            indices[vert]
            for vert in face.verts
        )
        for face in faces
    ]

    return vertices, polygons


def validate_closed_mesh(bm):

    if len(bm.verts) < 4 or not bm.faces:

        raise SegmentationError(
            "Invalid collision volume."
        )

    if any(
        not edge.is_manifold
        for edge in bm.edges
    ):

        raise SegmentationError(
            "Mesh is not closed and manifold."
        )

    if any(
        not vert.link_faces
        for vert in bm.verts
    ):

        raise SegmentationError(
            "Mesh contains isolated vertices."
        )

    volume = bm.calc_volume(
        signed=True
    )

    if volume < 0:

        bmesh.ops.reverse_faces(
            bm,
            faces=list(bm.faces)
        )

        bm.normal_update()

        volume = bm.calc_volume(
            signed=True
        )

    if (
        not math.isfinite(volume)
        or volume <= 1e-12
    ):

        raise SegmentationError(
            "Mesh has invalid volume."
        )

    return volume


def connected_components(bm):

    remaining = set(bm.faces)
    components = []

    for start in list(bm.faces):

        if start not in remaining:
            continue

        remaining.remove(start)

        stack = [start]
        group = []

        while stack:

            face = stack.pop()
            group.append(face)

            for edge in face.edges:

                for neighbour in edge.link_faces:

                    if neighbour in remaining:

                        remaining.remove(neighbour)
                        stack.append(neighbour)

        components.append(
            extract_geometry(
                bm,
                selected_faces=group
            )
        )

    return components


def convexity_error(bm):

    """
    Maximum distance of a vertex outside
    any outward-facing face plane.

    Input coordinates must be normalized.
    """

    bm.normal_update()

    points = [
        vert.co
        for vert in bm.verts
    ]

    maximum = 0.0

    for face in bm.faces:

        origin = face.verts[0].co
        normal = face.normal

        if normal.length_squared <= 1e-12:

            raise SegmentationError(
                "Degenerate face normal."
            )

        for point in points:

            distance = normal.dot(
                point - origin
            )

            maximum = max(
                maximum,
                distance
            )

    return maximum


def geometry_information(geometry):

    vertices, faces = geometry

    bm = make_bmesh(
        vertices,
        faces
    )

    try:

        bmesh.ops.triangulate(
            bm,
            faces=list(bm.faces)
        )

        bm.normal_update()

        volume = validate_closed_mesh(bm)

        error = convexity_error(bm)

        return {
            "volume": volume,
            "error": error,
            "convex": (
                error <= CONVEX_TOLERANCE
            )
        }

    finally:

        bm.free()


def candidate_planes(bm):

    """
    Prioritize planes associated with
    concave edges.

    Additional axis-aligned planes provide
    conservative fallback candidates.
    """

    candidates = []
    seen = set()

    axes = (
        Vector((1, 0, 0)),
        Vector((0, 1, 0)),
        Vector((0, 0, 1))
    )

    def add_plane(origin, normal):

        normal = Vector(normal)

        if normal.length_squared <= 1e-12:
            return

        normal.normalize()

        # Canonical direction.
        for value in normal:

            if abs(value) > EPSILON:

                if value < 0:
                    normal.negate()

                break

        origin = Vector(origin)

        distance = normal.dot(origin)

        key = (
            round(normal.x, 5),
            round(normal.y, 5),
            round(normal.z, 5),
            round(distance, 5)
        )

        if key in seen:
            return

        seen.add(key)

        candidates.append((
            origin.copy(),
            normal.copy()
        ))

    concave_edges = []

    for edge in bm.edges:

        if not edge.is_manifold:
            continue

        angle = edge.calc_face_angle_signed()

        if angle < -1e-4:

            concave_edges.append((
                abs(angle),
                edge
            ))

    concave_edges.sort(
        key=lambda item: item[0],
        reverse=True
    )

    for angle, edge in concave_edges:

        origin = (
            edge.verts[0].co
            + edge.verts[1].co
        ) * 0.5

        face_a, face_b = edge.link_faces

        normal_a = face_a.normal
        normal_b = face_b.normal

        add_plane(origin, normal_a)
        add_plane(origin, normal_b)

        add_plane(
            origin,
            normal_a + normal_b
        )

        add_plane(
            origin,
            normal_a - normal_b
        )

        for axis in axes:

            add_plane(origin, axis)

        if len(candidates) >= (
            MAX_CANDIDATES - 6
        ):

            break

    center = sum(
        (vert.co for vert in bm.verts),
        Vector((0, 0, 0))
    ) / len(bm.verts)

    for axis in axes:

        add_plane(center, axis)

    return candidates[:MAX_CANDIDATES]


def close_cut_boundaries(
    bm,
    origin,
    normal
):

    boundaries = [
        edge for edge in bm.edges
        if edge.is_boundary
    ]

    if not boundaries:
        return

    for edge in boundaries:

        for vert in edge.verts:

            distance = abs(
                normal.dot(
                    vert.co - origin
                )
            )

            if distance > EPSILON * 8:

                raise SegmentationError(
                    "Unexpected open boundary."
                )

    # Every boundary vertex must belong
    # to exactly two cut-boundary edges.

    degree = {}

    for edge in boundaries:

        for vert in edge.verts:

            degree[vert] = (
                degree.get(vert, 0) + 1
            )

    if any(
        count != 2
        for count in degree.values()
    ):

        raise SegmentationError(
            "Invalid cut boundary."
        )

    # IMPORTANT:
    # Before filling, reject nested or
    # intersecting boundary loops unless
    # a hole-aware planar cap is implemented.
    #
    # This helper must be completed and
    # tested during integration.

    # Project boundary loops and reject intersections/nesting before holes_fill.
    from mathutils.geometry import intersect_line_line_2d
    basis = normal.orthogonal().normalized()
    other = normal.cross(basis).normalized()
    remaining = set(boundaries)
    loops = []
    while remaining:
        edge = next(iter(remaining))
        start, current = edge.verts
        remaining.remove(edge)
        loop = [start,current]
        while current != start:
            choices = [e for e in current.link_edges if e in remaining]
            if len(choices) != 1:
                raise SegmentationError('Ambiguous cut loop')
            edge = choices[0]
            remaining.remove(edge)
            current = edge.other_vert(current)
            loop.append(current)
        loops.append([(basis.dot(v.co-origin),other.dot(v.co-origin)) for v in loop[:-1]])
    def inside(point, polygon):
        x,y = point
        hit = False
        for a,b in zip(polygon,polygon[1:]+polygon[:1]):
            if (a[1]>y) != (b[1]>y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
                hit = not hit
        return hit
    segments = [(k,i,a,b) for k,loop in enumerate(loops) for i,(a,b) in enumerate(zip(loop,loop[1:]+loop[:1]))]
    for k,i,a,b in segments:
        for l,j,c,d in segments:
            if (k,i)>=(l,j) or (k==l and (abs(i-j)==1 or abs(i-j)==len(loops[k])-1)):
                continue
            if intersect_line_line_2d(Vector(a),Vector(b),Vector(c),Vector(d)) is not None:
                raise SegmentationError('Intersecting cut contours')
    for i,loop in enumerate(loops):
        if any(inside(loop[0],other_loop) for j,other_loop in enumerate(loops) if i!=j):
            raise SegmentationError('Nested cut contours are not supported')

    result = bmesh.ops.holes_fill(
        bm,
        edges=boundaries,
        sides=0
    )

    if not result.get("faces"):

        raise SegmentationError(
            "Unable to close cut."
        )

    bmesh.ops.recalc_face_normals(
        bm,
        faces=list(bm.faces)
    )

    bm.normal_update()


def cut_half(
    source,
    origin,
    normal,
    keep_positive
):

    bm = source.copy()

    try:

        geometry = (
            list(bm.verts)
            + list(bm.edges)
            + list(bm.faces)
        )

        bmesh.ops.bisect_plane(

            bm,

            geom=geometry,

            dist=EPSILON,

            plane_co=origin,

            plane_no=normal,

            clear_inner=keep_positive,

            clear_outer=not keep_positive

        )

        if not bm.faces:

            raise SegmentationError(
                "Empty cut result."
            )

        loose = [
            vert for vert in bm.verts
            if not vert.link_faces
        ]

        if loose:

            bmesh.ops.delete(
                bm,
                geom=loose,
                context='VERTS'
            )

        close_cut_boundaries(
            bm,
            origin,
            normal
        )

        validate_closed_mesh(bm)

        return connected_components(bm)

    finally:

        bm.free()


def try_split(
    bm,
    origin,
    normal
):

    distances = [
        normal.dot(
            vert.co - origin
        )
        for vert in bm.verts
    ]

    if (
        min(distances) >= -EPSILON
        or max(distances) <= EPSILON
    ):

        return None

    try:

        negative = cut_half(
            bm,
            origin,
            normal,
            keep_positive=False
        )

        positive = cut_half(
            bm,
            origin,
            normal,
            keep_positive=True
        )

        return negative + positive

    except (
        ValueError,
        RuntimeError,
        SegmentationError
    ):

        return None


def find_best_split(geometry):

    vertices, faces = geometry

    bm = make_bmesh(
        vertices,
        faces
    )

    try:

        bmesh.ops.triangulate(
            bm,
            faces=list(bm.faces)
        )

        bm.normal_update()

        source_volume = validate_closed_mesh(
            bm
        )

        best = None
        best_score = None

        for origin, normal in candidate_planes(bm):
            if time.monotonic()>_DEADLINE:
                raise SegmentationError("Segmentation time budget exceeded")
            if time.monotonic() > _DEADLINE:
                raise SegmentationError("Segmentation exceeded its 15 second time budget")

            pieces = try_split(
                bm,
                origin,
                normal
            )

            if not pieces or len(pieces) < 2:
                continue

            try:

                information = [
                    geometry_information(piece)
                    for piece in pieces
                ]

            except SegmentationError:

                continue

            if any(item["volume"] >= source_volume*(1-1e-6) for item in information):
                continue
            total_volume = sum(
                item["volume"]
                for item in information
            )

            relative_error = abs(
                total_volume - source_volume
            ) / source_volume

            if (
                relative_error
                > VOLUME_TOLERANCE
            ):

                continue

            # Favor valid convex pieces,
            # low remaining concavity and
            # a low number of segments.

            remaining_error = sum(

                item["error"]
                * item["volume"]

                for item in information

            ) / source_volume

            nonconvex_count = sum(
                not item["convex"]
                for item in information
            )

            score = (

                remaining_error,

                nonconvex_count,

                len(pieces),

                relative_error

            )

            if (
                best_score is None
                or score < best_score
            ):

                best_score = score
                best = pieces

        return best

    finally:

        bm.free()


def simplify_coplanar_geometry(geometry, rebuild=False):

    vertices, faces = geometry
    from .geometry import create_convex_hull
    if rebuild:
        try:
            vertices, faces = create_convex_hull(vertices)
        except ValueError:
            # Optimization must not invalidate an already validated convex segment.
            pass

    bm = make_bmesh(
        vertices,
        faces
    )

    try:

        original_volume = validate_closed_mesh(
            bm
        )

        bmesh.ops.dissolve_limit(

            bm,

            angle_limit=1e-3,

            verts=list(bm.verts),

            edges=list(bm.edges),

            use_dissolve_boundaries=False

        )

        bm.normal_update()

        new_volume = validate_closed_mesh(
            bm
        )

        error = abs(
            new_volume - original_volume
        ) / original_volume

        if error > VOLUME_TOLERANCE:

            return geometry

        result = extract_geometry(bm)

        information = geometry_information(
            result
        )

        if not information["convex"]:

            return geometry

        return result

    except (
        ValueError,
        RuntimeError,
        SegmentationError
    ) as exc:

        return geometry

    finally:

        bm.free()


def generate_segmented_geometry(
    vertices,
    faces
):

    global _DEADLINE
    _DEADLINE = time.monotonic()+15
    if len(vertices)>10000 or len(faces)>10000:
        raise SegmentationError("Source exceeds safe topology limit")
    if not vertices or not faces:

        raise SegmentationError(
            "Source mesh is empty."
        )

    points = [
        Vector(co)
        for co in vertices
    ]

    if not all(
        math.isfinite(value)
        for point in points
        for value in point
    ):

        raise SegmentationError(
            "Invalid vertex coordinates."
        )

    minimum = Vector((
        min(p.x for p in points),
        min(p.y for p in points),
        min(p.z for p in points)
    ))

    maximum = Vector((
        max(p.x for p in points),
        max(p.y for p in points),
        max(p.z for p in points)
    ))

    center = (
        minimum + maximum
    ) * 0.5

    extent = max(
        maximum - minimum
    )

    if extent <= 0:

        raise SegmentationError(
            "Degenerate source geometry."
        )

    # Normalize coordinates to keep
    # geometric tolerances scale-independent.

    normalized = [

        tuple(
            (point - center) / extent
        )

        for point in points

    ]

    source = make_bmesh(
        normalized,
        faces
    )

    try:

        bmesh.ops.triangulate(
            source,
            faces=list(source.faces)
        )

        source.normal_update()

        source_parts = connected_components(
            source
        )

    finally:

        source.free()

    pending = [
        (part, 0)
        for part in source_parts
    ]

    completed = []

    while pending:
        if time.monotonic()>_DEADLINE:
            raise SegmentationError("Segmentation time budget exceeded")

        if (
            len(completed)
            + len(pending)
            > MAX_SEGMENTS
        ):

            raise SegmentationError(
                "Safe segment limit exceeded."
            )

        geometry, depth = pending.pop(0)

        information = geometry_information(
            geometry
        )

        if information["convex"]:

            completed.append(

                simplify_coplanar_geometry(
                    geometry, rebuild=True
                )

            )

            continue

        if depth >= MAX_DEPTH:

            raise SegmentationError(
                "Unable to complete segmentation."
            )

        pieces = find_best_split(
            geometry
        )

        if not pieces:

            raise SegmentationError(
                "No safe convex cut found."
            )

        for piece in pieces:

            pending.append((
                piece,
                depth + 1
            ))

    # Merge only when the convex union has the same volume as both disjoint cuts.
    from .geometry import create_convex_hull
    changed = True
    while changed and time.monotonic()<_DEADLINE:
        changed = False
        for i in range(len(completed)):
            for j in range(i+1,len(completed)):
                try:
                    merged = create_convex_hull(completed[i][0]+completed[j][0])
                    volume = geometry_information(merged)['volume']
                except (ValueError, RuntimeError):
                    continue
                expected = geometry_information(completed[i])['volume']+geometry_information(completed[j])['volume']
                if abs(volume-expected)/expected<1e-5:
                    completed[i] = simplify_coplanar_geometry(merged)
                    completed.pop(j)
                    changed = True
                    break
            if changed: break

    result = []

    for part_vertices, part_faces in completed:

        restored = [

            tuple(
                Vector(co) * extent
                + center
            )

            for co in part_vertices

        ]

        result.append((
            restored,
            part_faces
        ))

    return result
