"""Phase 18+20 — Reporting-guideline checklist catalogue.

Currently a stub holding the CHEERS 2022 checklist (Husereau et al. Value
Health 2022). MP20 will wire this catalogue to a UI surface; for now we
just persist the JSON definition so the CHEERS report DOCX/PDF can carry
the checklist items as an appendix table.
"""
from .catalogue import CHECKLISTS

__all__ = ["CHECKLISTS"]
