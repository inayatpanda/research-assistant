"""Phase 8.6 — Ingest services subtree.

Five thin parser/lookup modules + one dedup group-finder. Each returns the
uniform `schemas.ingest.ArticleMetadata` shape so the import route can stay
agnostic of the source.
"""
