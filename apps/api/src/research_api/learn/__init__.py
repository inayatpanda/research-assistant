"""Phase 5a — Learn hub.

Read-only reference content (stat tests, checklists, walkthroughs) served
directly from Markdown files on disk. No DB; loader is module-scoped and
caches parsed entries in memory.
"""
from .loader import (
    StatTestEntry,
    StatTestSummary,
    get_stat_test,
    list_stat_tests,
    load_all_stat_tests,
)

__all__ = [
    "StatTestEntry",
    "StatTestSummary",
    "get_stat_test",
    "list_stat_tests",
    "load_all_stat_tests",
]
