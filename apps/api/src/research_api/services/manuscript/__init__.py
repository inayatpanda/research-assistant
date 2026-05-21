"""Phase 4.5 — Manuscript-editor support services.

This subpackage hosts pure-function services that the manuscript editor's
"Insert ..." commands call into. They never touch the DB themselves; the
route layer loads + filters rows and hands them down.
"""
