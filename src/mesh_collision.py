# SPDX-License-Identifier: GPL-3.0-or-later

import math

from .geometry import create_convex_hull


def get_evaluated_geometry(
    obj,
    depsgraph
):

    evaluated = obj.evaluated_get(
        depsgraph
    )

    mesh = evaluated.to_mesh()

    try:

        if mesh is None:

            raise ValueError(
                "Unable to evaluate mesh."
            )

        faces = [
            tuple(poly.vertices)
            for poly in mesh.polygons
        ]

        if not faces:

            raise ValueError(
                "Source mesh has no faces."
            )

        used = sorted({

            index

            for face in faces
            for index in face

        })

        remap = {

            old: new

            for new, old in enumerate(used)

        }

        vertices = [

            tuple(mesh.vertices[index].co)

            for index in used

        ]

        if not all(

            math.isfinite(value)

            for vertex in vertices
            for value in vertex

        ):

            raise ValueError(
                "Invalid source coordinates."
            )

        polygons = [

            tuple(
                remap[index]
                for index in face
            )

            for face in faces

        ]

        return vertices, polygons

    finally:

        evaluated.to_mesh_clear()


def generate_mesh_collision(
    obj,
    depsgraph
):

    vertices, faces = get_evaluated_geometry(
        obj,
        depsgraph
    )

    # Reuse the existing convexity validator.
    #
    # If the original geometry is already one
    # valid, closed, convex component,
    # preserve its existing geometry.
    #
    # Otherwise generate its convex envelope.

    from .geometry import validate_convex_geometry
    from .segmentation import simplify_coplanar_geometry
    try:
        validate_convex_geometry(vertices,faces)
        return simplify_coplanar_geometry((vertices,faces))
    except (ValueError,RuntimeError):
        return simplify_coplanar_geometry(create_convex_hull(vertices))


def generate_segmented_collision(
    obj,
    depsgraph
):

    from .segmentation import (
        generate_segmented_geometry
    )

    vertices, faces = get_evaluated_geometry(
        obj,
        depsgraph
    )

    return generate_segmented_geometry(
        vertices,
        faces
    )
