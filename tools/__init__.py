"""
tools/
CSE Life: Compile & Conquer — asset tooling

Everything in this package is AUTHORING tooling, not game code: the
level editor and the drawing helpers it is built from. pygame is
allowed here, the same way it is allowed in assemble_sprite_sheet.py
(Build Plan §0.7).

LAYER RULE: tools/ may import content/, ui/, tools/, the stdlib and
pygame. It may NOT import engine/, core/ or academic/. The editor
must never be able to reach game state -- if it could, authoring a
level and playing one would stop being separable. Enforced by
tests/test_layer_purity.py.
"""
