from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentTriageRequest(BaseModel):
    query: str = Field(..., min_length=1, examples=["I take Humira, earn $35000, household of 1 in PA, uninsured"])
    annual_income: float | None = Field(None, ge=0, examples=[35000])
    household_size: int | None = Field(None, ge=1, le=20, examples=[1])
    state: str = Field("PA", min_length=2, max_length=32)
    is_uninsured: bool = True
    is_medicare: bool = False


class AgentTriageResponse(BaseModel):
    action_plan: str
    medication_query: str = ""
    visited_nodes: list[str] = Field(default_factory=list)
    savings: dict[str, Any] | None = None
    fpl: dict[str, Any] | None = None
