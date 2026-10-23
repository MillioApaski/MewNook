# Hair-protected eyelid skin repair

V9's full-eye repair polygons crossed fine strands and face-framing hair. V10 excludes the original front-hair mattes (including all antialiased pixels and a one-pixel guard) from skin interpolation and boundary sampling. Every eyelid frame restores protected pixels exactly from the neutral slot.

Exporter assertions verify all protected hair pixels match neutral across all nine frames, and skin repair has zero overlap with hair. The two eye slots protect 2,205 pixels. Original closed lashes and tiny sleepy mouth are retained.

Rebuild: `python scripts/prepare-v4-blink-source.py`, then `python scripts/build-mewnook-v4-source-rig.py`. See the PNG stages, protected-hair masks, manifest and editable ORA. Runtime cache revision: source-art-20261022-hairguard. Visual acceptance is pending.
