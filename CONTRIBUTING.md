# Contributing

Contact Studio Lin Games at studiolingames@gmail.com. Report reproducible problems
using the issue templates once the public repository is available. Include Blender
version, operating system, collision method, transforms and exact messages.

Prefer a minimal **synthetic reproduction script**, not a proprietary model. Never
post private game assets, credentials, local configurations, private paths or production
scenes. Only submit material you have permission to share. Synthetic failures are
useful evidence and must not be silently removed or relabelled as passing.

Run the public synthetic tests in fresh Blender background processes; they clear
scene state. See docs/testing.md. Keep changes focused, preserve source assets and
validate closedness, volume, convexity, containment and cleanup. Document numerical
limits rather than relaxing tolerances to hide failures. Use Blender APIs and the
Python standard library; do not add dependencies or runtime network access casually.

Retain GPL-3.0-or-later notices and ensure your contributions can be distributed
under that license. Do not publish release artifacts on behalf of Studio Lin Games
without explicit authorization. Release algorithms/tolerances are currently frozen;
proposed changes require review and independent validation before adoption.
