"""Pydantic models for Formula E Gen3 Evo Telemetry Evaluation service."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class TelemetryEvaluationRequest(BaseModel):
    """Input payload for evaluating lap telemetry against Gen3 Evo limits."""

    driver_name: Optional[str] = Field(default="Driver", description="Driver name")
    lap_number: Optional[int] = Field(default=1, description="Lap number")
    turn_3_peak_regen_kw: Optional[float] = Field(
        default=None, description="Peak regenerative braking power in Turn 3 (kW)"
    )
    turn_8_peak_regen_kw: Optional[float] = Field(
        default=None, description="Peak regenerative braking power in Turn 8 (kW)"
    )
    turn_13_peak_regen_kw: Optional[float] = Field(
        default=None, description="Peak regenerative braking power in Turn 13 (kW)"
    )
    peak_regen_kw: Optional[float] = Field(
        default=None, description="Overall peak regenerative braking power (kW)"
    )
    lift_and_coast_distance_m: Optional[float] = Field(
        default=None, description="Lift-and-coast distance before braking zones (meters)"
    )

    @model_validator(mode="before")
    @classmethod
    def harmonize_telemetry_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        d = dict(data)

        # Harmonize Turn 3 aliases
        if d.get("turn_3_peak_regen_kw") is None:
            for alias in [
                "turn_3_regen_kw",
                "turn_3_regen",
                "t3_peak_regen_kw",
                "t3_regen_kw",
                "t3_regen",
            ]:
                if alias in d and d[alias] is not None:
                    d["turn_3_peak_regen_kw"] = float(d[alias])
                    break

        # Harmonize Turn 8 aliases
        if d.get("turn_8_peak_regen_kw") is None:
            for alias in [
                "turn_8_regen_kw",
                "turn_8_regen",
                "t8_peak_regen_kw",
                "t8_regen_kw",
                "t8_regen",
            ]:
                if alias in d and d[alias] is not None:
                    d["turn_8_peak_regen_kw"] = float(d[alias])
                    break

        # Harmonize Turn 13 aliases
        if d.get("turn_13_peak_regen_kw") is None:
            for alias in [
                "turn_13_regen_kw",
                "turn_13_regen",
                "t13_peak_regen_kw",
                "t13_regen_kw",
                "t13_regen",
            ]:
                if alias in d and d[alias] is not None:
                    d["turn_13_peak_regen_kw"] = float(d[alias])
                    break

        # Harmonize Lift and Coast aliases
        if d.get("lift_and_coast_distance_m") is None:
            for alias in [
                "lift_and_coast_distance",
                "lift_and_coast_m",
                "lift_and_coast",
                "coasting_distance_m",
                "coasting_distance",
                "coast_distance_m",
                "coast_distance",
            ]:
                if alias in d and d[alias] is not None:
                    d["lift_and_coast_distance_m"] = float(d[alias])
                    break

        # Cross-populate peak_regen_kw if needed
        t3 = d.get("turn_3_peak_regen_kw")
        t8 = d.get("turn_8_peak_regen_kw")
        t13 = d.get("turn_13_peak_regen_kw")
        peak = d.get("peak_regen_kw")

        if peak is not None:
            peak = float(peak)
            d["peak_regen_kw"] = peak
            if t3 is None:
                d["turn_3_peak_regen_kw"] = peak
            if t8 is None:
                d["turn_8_peak_regen_kw"] = peak
            if t13 is None:
                d["turn_13_peak_regen_kw"] = peak
        else:
            val_t3 = float(t3) if t3 is not None else 0.0
            val_t8 = float(t8) if t8 is not None else 0.0
            val_t13 = float(t13) if t13 is not None else 0.0
            d["peak_regen_kw"] = max(val_t3, val_t8, val_t13)

        # Defaults for missing values
        if d.get("turn_3_peak_regen_kw") is None:
            d["turn_3_peak_regen_kw"] = 0.0
        else:
            d["turn_3_peak_regen_kw"] = float(d["turn_3_peak_regen_kw"])

        if d.get("turn_8_peak_regen_kw") is None:
            d["turn_8_peak_regen_kw"] = 0.0
        else:
            d["turn_8_peak_regen_kw"] = float(d["turn_8_peak_regen_kw"])

        if d.get("turn_13_peak_regen_kw") is None:
            d["turn_13_peak_regen_kw"] = 0.0
        else:
            d["turn_13_peak_regen_kw"] = float(d["turn_13_peak_regen_kw"])

        if d.get("lift_and_coast_distance_m") is None:
            d["lift_and_coast_distance_m"] = 0.0
        else:
            d["lift_and_coast_distance_m"] = float(d["lift_and_coast_distance_m"])

        return d


class EvaluationResponse(BaseModel):
    """Evaluation result for Formula E driver performance."""

    efficiency_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Calculated driver efficiency score (1-100 scale, sum of braking and coasting)",
    )
    rating: str = Field(
        ...,
        description="Driver performance rating: EXCELLENT, OPTIMAL, or NEEDS_IMPROVEMENT",
    )
    sensor_fault_detected: bool = Field(
        ...,
        description="Flag indicating if telemetry exceeded the 600 kW physical limit",
    )
    feedback: List[str] = Field(
        ...,
        description="Actionable feedback messages for the race engineer",
    )
    sensor_error: bool = Field(
        ...,
        description="Alias for sensor_fault_detected for compatibility",
    )
    braking_points: int = Field(
        ...,
        ge=0,
        le=50,
        description="Energy recovery points awarded for heavy braking zones (max 50)",
    )
    lift_and_coast_points: int = Field(
        ...,
        ge=0,
        le=50,
        description="Energy management points awarded for lift-and-coast (max 50)",
    )
    turn_3_peak_regen_kw: float = Field(
        ...,
        description="Validated peak regen at Turn 3 (capped at 600 kW)",
    )
    turn_8_peak_regen_kw: float = Field(
        default=0.0,
        description="Validated peak regen at Turn 8 (capped at 600 kW)",
    )
    turn_13_peak_regen_kw: float = Field(
        ...,
        description="Validated peak regen at Turn 13 (capped at 600 kW)",
    )
    peak_regen_kw: float = Field(
        ...,
        description="Overall peak regen across heavy zones (capped at 600 kW)",
    )
    lift_and_coast_distance_m: float = Field(
        ...,
        description="Validated lift-and-coast distance in meters",
    )
    driver_name: Optional[str] = Field(default="Driver", description="Driver name")
    lap_number: Optional[int] = Field(default=1, description="Lap number evaluated")
