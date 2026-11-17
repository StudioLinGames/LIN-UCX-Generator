# Release checklist — v1.4.1

## Completed

- Developer approval as a stable-publication candidate with accepted limitations.
- Frozen 1.4.1 source matches every entry of the approved release ZIP.
- Seven methods, native Decimate and export selection documented.
- Public synthetic tests run on Windows Blender 5.2.2 LTS and 5.3.0.
- Two independent synthetic rejections retained; later manual discrepancy documented.
- Owner-reported Blender/Unreal tests, Native Box and player arch passage recorded
  as manual evidence.
- Official package validation passes on both verified Blender versions.
- Private assets, results, local settings and development history excluded.
- GPL-3.0-or-later license, contact, contributing guide and issue templates included.

## Owner actions before publication

- Review the prepared public files and release notes.
- Confirm organization permissions and authorize repository creation/publication.
- Create the public repository, commit the reviewed files and create tag `v1.4.1`.
- Attach the approved ZIP unchanged; verify its SHA-256 against the release notes.
- Configure repository description and license presentation; verify public visibility
  and the published attachment after publication.
- Review Blender Extensions submission requirements separately if submitting there.

## Known scope limits

- The independent holdout remains 198/200; safe rejections are accepted, not fixed.
- Blender 4.2, Linux and macOS remain unverified.
- No public repository, tag, release, download URL or Blender Extensions listing is
  created by this preparation. A platform publication review is still required.
