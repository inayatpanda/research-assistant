from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

EffectMetric = Literal["md", "smd", "or", "rr", "hr", "r"]
PoolingModel = Literal["fixed", "random"]
MetaStatus = Literal["draft", "running", "completed", "failed"]


class MetaInputBase(BaseModel):
    study_label: str | None = None
    # Continuous (MD / SMD)
    mean_a: float | None = None
    sd_a: float | None = None
    n_a: int | None = None
    mean_b: float | None = None
    sd_b: float | None = None
    n_b: int | None = None
    # Binary (OR / RR)
    events_a: int | None = None
    n_a_total: int | None = None
    events_b: int | None = None
    n_b_total: int | None = None
    # Time-to-event (HR)
    log_hr: float | None = None
    se_log_hr: float | None = None
    hr: float | None = None
    hr_ci_low: float | None = None
    hr_ci_high: float | None = None
    # Correlation (r)
    r: float | None = None
    n_r: int | None = None


class MetaInputCreate(MetaInputBase):
    article_id: str


class MetaInputUpdate(MetaInputBase):
    pass


class MetaInputRead(MetaInputBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meta_id: str
    article_id: str
    subgroup: str | None
    created_at: datetime
    updated_at: datetime


class MetaAnalysisCreate(BaseModel):
    title: str | None = None
    effect_metric: EffectMetric
    model: PoolingModel
    subgroup_variable: str | None = None
    inputs: list[MetaInputCreate] = Field(min_length=2)


class MetaAnalysisUpdate(BaseModel):
    title: str | None = None
    effect_metric: EffectMetric | None = None
    model: PoolingModel | None = None
    subgroup_variable: str | None = None


class MetaAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    review_id: str
    title: str | None
    effect_metric: EffectMetric
    model: PoolingModel
    subgroup_variable: str | None
    pooled_estimate: float | None
    pooled_se: float | None
    ci_low: float | None
    ci_high: float | None
    z_value: float | None
    p_value: float | None
    q_value: float | None
    q_df: int | None
    q_p: float | None
    i2: float | None
    tau2: float | None
    subgroup_summary: dict[str, Any] | None
    ai_interpretation: str | None
    status: MetaStatus
    inputs: list[MetaInputRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class MetaInterpretRequest(BaseModel):
    pass


class MetaInterpretResponse(BaseModel):
    ai_interpretation: str


class MetaPushRequest(BaseModel):
    pass
