# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Studio Lin Games
"""Bounding primitives, based on Studio Lin Games' radial-profile proposal."""
import math
from mathutils import Vector


def get_bounds(points):
    points = [Vector(p) for p in points]
    if not points or any(not math.isfinite(c) for p in points for c in p):
        raise ValueError("Empty geometry or non-finite coordinates")
    minimum = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    maximum = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    return (minimum + maximum) * 0.5, maximum - minimum


def create_revolved_geometry(profiles, segments=16):
    if segments < 8 or len(profiles) < 3:
        raise ValueError("At least eight segments and three profiles are required")
    vertices, faces, rings = [], [], []
    for radius, z in profiles:
        if radius < 0 or not math.isfinite(radius + z):
            raise ValueError("Invalid radial profile")
        ring = []
        # Only explicit poles collapse; avoid an absolute tolerance on tiny assets.
        for j in range(1 if radius == 0 else segments):
            angle = 2 * math.pi * j / segments
            ring.append(len(vertices))
            vertices.append((radius * math.cos(angle), radius * math.sin(angle), z))
        rings.append(ring)
    for lower, upper in zip(rings, rings[1:]):
        if len(lower) == len(upper) == 1:
            raise ValueError("Adjacent poles produce degenerate geometry")
        for j in range(segments):
            n = (j + 1) % segments
            if len(lower) == 1:
                faces.append((lower[0], upper[n], upper[j]))
            elif len(upper) == 1:
                faces.append((lower[j], lower[n], upper[0]))
            else:
                faces.append((lower[j], lower[n], upper[n], upper[j]))
    return vertices, faces


def create_sphere_geometry(points, segments=16, latitude_steps=8):
    points = [Vector(p) for p in points]
    center, _dimensions = get_bounds(points)
    radius = max((p-center).length for p in points)
    if radius <= 0:
        raise ValueError("Sphere radius is zero")
    latitude_steps = max(4, int(latitude_steps))
    profiles = []
    for i in range(latitude_steps+1):
        angle = -math.pi/2 + math.pi*i/latitude_steps
        profiles.append((0 if i in (0,latitude_steps) else radius*math.cos(angle), radius*math.sin(angle)))
    vertices, faces = create_revolved_geometry(profiles, segments)
    return [tuple(Vector(v)+center) for v in vertices], faces


def create_capsule_geometry(points, segments=16, hemisphere_steps=6):
    points = [Vector(p) for p in points]
    center, dimensions = get_bounds(points)
    axis_index = max(range(3), key=lambda i: dimensions[i])
    axis = Vector((0,0,0))
    axis[axis_index] = 1
    local = [p-center for p in points]
    radial_squared = [max(0.0, (p-axis*p.dot(axis)).length_squared) for p in local]
    radius = math.sqrt(max(radial_squared))
    if radius <= 0:
        raise ValueError("Capsule radius is zero")
    # |z| <= segment_half + sqrt(r²-radial_distance²), for every input point.
    half_cylinder = max(0.0, max(abs(p.dot(axis))-math.sqrt(max(0.0,radius*radius-r2)) for p,r2 in zip(local,radial_squared)))
    steps = max(3, int(hemisphere_steps))
    profiles = []
    for i in range(steps+1):
        angle = -math.pi/2 + math.pi*i/(2*steps)
        profiles.append((0 if i == 0 else radius*math.cos(angle), -half_cylinder+radius*math.sin(angle)))
    for i in range(steps+1):
        if half_cylinder == 0 and i == 0:
            continue
        angle = math.pi*i/(2*steps)
        profiles.append((0 if i == steps else radius*math.cos(angle), half_cylinder+radius*math.sin(angle)))
    vertices, faces = create_revolved_geometry(profiles, segments)
    rotation = Vector((0,0,1)).rotation_difference(axis)
    return [tuple(rotation @ Vector(v)+center) for v in vertices], faces
