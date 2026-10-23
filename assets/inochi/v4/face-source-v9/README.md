# Full eye footprint repair

The previous skin repair retained the pale original upper-eye crease. This version uses explicit complete eye footprints, reconstructing skin from surrounding source pixels with harmonic interpolation. The opaque eye slots now include the full old contour. Edge blending is confined to the repair boundary; the approved painted closed lashes and tiny sleepy mouth are retained.

Rebuild with `python scripts/prepare-v4-blink-source.py` and `python scripts/build-mewnook-v4-source-rig.py`. The editable ORA, nine PNG frames per eye and opening/closing comparison are included. Runtime resource revision: `source-art-20261022-eyecontour`.

Validation: 28 unit tests pass; exported comparison inspected. Full WebGL regression runs in CI; visual acceptance remains pending.
