"""Phase 14 (MP14) — GRADE certainty Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

StartingCertainty = Literal["high", "low"]
DowngradeLevel = Literal["not_serious", "serious", "very_serious"]
UpgradeLevel = Literal["none", "present", "large"]
LargeEffectUpgrade = Literal["none", "present", "large"]
SmallUpgrade = Literal["none", "present"]
Certainty = Literal["high", "moderate", "low", "very_low"]


class GradeAssessmentBase(BaseModel):
    outcome_label: str = Field(min_length=1, max_length=255)
    starting_certainty: StartingCertainty = "high"
    domain_risk_of_bias: DowngradeLevel = "not_serious"
    domain_inconsistency: DowngradeLevel = "not_serious"
    domain_indirectness: DowngradeLevel = "not_serious"
    domain_imprecision: DowngradeLevel = "not_serious"
    domain_publication_bias: DowngradeLevel = "not_serious"
    upgrade_large_effect: LargeEffectUpgrade = "none"
    upgrade_dose_response: SmallUpgrade = "none"
    upgrade_confounders_against: SmallUpgrade = "none"
    notes: str | None = None
    meta_id: str | None = None


class GradeAssessmentCreate(GradeAssessmentBase):
    """Upsert payload — keyed by ``outcome_label`` within a review."""


class GradeAssessmentUpdate(BaseModel):
    outcome_label: str | None = Field(default=None, max_length=255)
    starting_certainty: StartingCertainty | None = None
    domain_risk_of_bias: DowngradeLevel | None = None
    domain_inconsistency: DowngradeLevel | None = None
    domain_indirectness: DowngradeLevel | None = None
    domain_imprecision: DowngradeLevel | None = None
    domain_publication_bias: DowngradeLevel | None = None
    upgrade_large_effect: LargeEffectUpgrade | None = None
    upgrade_dose_response: SmallUpgrade | None = None
    upgrade_confounders_against: SmallUpgrade | None = None
    notes: str | None = None
    meta_id: str | None = None


class GradeAssessmentRead(GradeAssessmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    review_id: str
    certainty: Certainty
    created_at: datetime
    updated_at: datetime
