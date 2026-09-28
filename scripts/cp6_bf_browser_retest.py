"""Browser-only follow-up on unchanged fb8fb11 product; no native business PASS claimed.

The standard installer still verifies every BF function body and its predecessors.
Full native/race/HTTP evidence belongs to run36390618767. Only browser navigation
timing changed, so this repeat resolves that concrete remaining test limitation.
"""
INSTALL_BF=True

def cases(cur,today):return []
