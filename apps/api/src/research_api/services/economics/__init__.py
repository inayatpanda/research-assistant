"""Phase 18 (MP18) — Health economics module.

Public surface (modules):
  - ``qaly``: area-under-the-curve QALY computation per patient.
  - ``cost_qaly_regression``: bivariate bootstrap of (cost, qaly) ~ treatment.
  - ``icer``: ICER + dominance + NMB.
  - ``ceac``: CEAC curve construction.
  - ``charts``: PNG renderers (CE plane, CEAC curve, tornado).
  - ``utility_value_sets``: declarative EQ-5D-3L/5L/Y-Dutch/SF-6D catalogue.
  - ``sensitivity``: PSA / DSA / scenario analyses.
"""
