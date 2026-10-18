"""Formula E Gen3 Evo Driver Performance Evaluation Microservice."""

import os
from typing import List, Optional

# GEMINI.md Rule 1: Always call matplotlib.use('Agg') BEFORE importing matplotlib.pyplot
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates

from models import EvaluationResponse, TelemetryEvaluationRequest
from visualization import generate_telemetry_chart

app = FastAPI(
    title="Formula E Gen3 Evo Driver Performance Evaluation",
    description="Microservice for evaluating driver telemetry and energy management",
    version="1.0.0",
)

# GEMINI.md Rule 2: Always resolve template paths relative to file location using os.path.dirname(__file__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def compute_driver_evaluation(
    telemetry: TelemetryEvaluationRequest,
) -> EvaluationResponse:
    """Evaluate Formula E Gen3 Evo driver telemetry against technical regulations.

    Regulations & Scoring:
    1. Maximum Regen: Peak regenerative braking capped at 600 kW.
       If telemetry reports peak_regen_kw > 600, flag sensor_fault_detected=True,
       sensor_error=True, and cap calculated values at 600.0 kW.
    2. Heavy Braking Energy Recovery:
       Key Recovery Zones: Turn 3, Turn 8, and Turn 13.
       Target Regen: >= 500 kW in Turn 3 and Turn 13; >= 480 kW in Turn 8.
       Scoring: Hitting targets in all three heavy zones contributes 50 points
       (Turn 3: 20 pts, Turn 8: 10 pts, Turn 13: 20 pts).
    3. Lift-and-Coast Energy Management:
       Target Distance: Coasting must start >= 50 meters before braking zones (50 pts).
       Between 25m and 49m: 25 points.
       Below 25m: 0 points.
    4. Total Efficiency Score:
       efficiency_score = braking_points + lift_and_coast_points (range 0-100).
    5. Rating:
       EXCELLENT (>= 80), OPTIMAL (>= 50), or NEEDS_IMPROVEMENT (< 50).
    6. Actionable feedback messages for the race engineer.
    """
    raw_t3 = telemetry.turn_3_peak_regen_kw or 0.0
    raw_t8 = telemetry.turn_8_peak_regen_kw or 0.0
    raw_t13 = telemetry.turn_13_peak_regen_kw or 0.0
    raw_peak = telemetry.peak_regen_kw or max(raw_t3, raw_t8, raw_t13)
    coasting_dist = telemetry.lift_and_coast_distance_m or 0.0

    # 1. Physical Regeneration Constraints & Sensor Fault Validation
    sensor_fault = (
        (raw_peak > 600.0)
        or (raw_t3 > 600.0)
        or (raw_t8 > 600.0)
        or (raw_t13 > 600.0)
    )

    t3_capped = min(600.0, raw_t3)
    t8_capped = min(600.0, raw_t8)
    t13_capped = min(600.0, raw_t13)
    peak_capped = min(600.0, raw_peak)

    # 2. Heavy Braking Energy Recovery (Turn 3, Turn 8 & Turn 13)
    t3_points = 20 if t3_capped >= 500.0 else 0
    t8_points = 10 if t8_capped >= 480.0 else 0
    t13_points = 20 if t13_capped >= 500.0 else 0
    braking_points = t3_points + t8_points + t13_points

    # 3. Lift-and-Coast Energy Management
    if coasting_dist >= 50.0:
        coasting_points = 50
    elif coasting_dist >= 25.0:
        coasting_points = 25
    else:
        coasting_points = 0

    # 4. Total Efficiency Score
    total_score = max(0, min(100, braking_points + coasting_points))

    # 5. Rating Determination
    if total_score >= 80:
        rating = "EXCELLENT"
    elif total_score >= 50:
        rating = "OPTIMAL"
    else:
        rating = "NEEDS_IMPROVEMENT"

    # 6. Actionable Race Engineer Feedback
    feedback: List[str] = []

    if sensor_fault:
        feedback.append(
            "CRITICAL: Sensor fault detected! Peak regen exceeded 600 kW physical limit. "
            "Telemetry capped at 600.0 kW. Inspect MGU-K current sensor."
        )

    # Turn 3 Feedback
    if t3_capped >= 500.0:
        feedback.append(
            f"Turn 3: Target regen achieved ({t3_capped:.1f} kW >= 500 kW target). "
            "Optimal heavy braking recovery."
        )
    else:
        feedback.append(
            f"Turn 3: Under-regenerating ({t3_capped:.1f} kW < 500 kW target). "
            "Driver must brake harder into Turn 3 heavy zone."
        )

    # Turn 8 Feedback
    if t8_capped >= 480.0:
        feedback.append(
            f"Turn 8: Target regen achieved ({t8_capped:.1f} kW >= 480 kW target). "
            "Optimal heavy braking recovery."
        )
    else:
        feedback.append(
            f"Turn 8: Under-regenerating ({t8_capped:.1f} kW < 480 kW target). "
            "Driver must maximize regen braking into Turn 8."
        )

    # Turn 13 Feedback
    if t13_capped >= 500.0:
        feedback.append(
            f"Turn 13: Target regen achieved ({t13_capped:.1f} kW >= 500 kW target). "
            "Optimal heavy braking recovery."
        )
    else:
        feedback.append(
            f"Turn 13: Under-regenerating ({t13_capped:.1f} kW < 500 kW target). "
            "Driver must maximize regen braking into Turn 13."
        )

    # Lift-and-Coast Feedback
    if coasting_dist >= 50.0:
        feedback.append(
            f"Lift-and-Coast: Target achieved ({coasting_dist:.1f}m >= 50m target). "
            "Excellent energy conservation."
        )
    elif coasting_dist >= 25.0:
        feedback.append(
            f"Lift-and-Coast: Moderate coasting distance ({coasting_dist:.1f}m). "
            f"Extend coasting phase by at least {50.0 - coasting_dist:.1f}m to reach 50m threshold."
        )
    else:
        feedback.append(
            f"Lift-and-Coast: Insufficient coasting ({coasting_dist:.1f}m < 25m). "
            "Heavy battery depletion risk; driver must lift earlier before braking zones."
        )

    # Strategic Overall Recommendation
    if rating == "EXCELLENT":
        feedback.append(
            "Strategy: Superb energy management. Maintain current lift/braking profile."
        )
    elif rating == "OPTIMAL":
        feedback.append(
            "Strategy: Solid race pace and recovery. Minor tweaks to braking threshold recommended."
        )
    else:
        feedback.append(
            "Strategy: High battery depletion rate detected. Immediate radio coaching needed."
        )

    return EvaluationResponse(
        efficiency_score=total_score,
        rating=rating,
        sensor_fault_detected=sensor_fault,
        sensor_error=sensor_fault,
        feedback=feedback,
        braking_points=braking_points,
        lift_and_coast_points=coasting_points,
        turn_3_peak_regen_kw=round(t3_capped, 1),
        turn_8_peak_regen_kw=round(t8_capped, 1),
        turn_13_peak_regen_kw=round(t13_capped, 1),
        peak_regen_kw=round(peak_capped, 1),
        lift_and_coast_distance_m=round(coasting_dist, 1),
        driver_name=telemetry.driver_name or "Driver",
        lap_number=telemetry.lap_number or 1,
    )


@app.post(
    "/api/v1/evaluate",
    response_model=EvaluationResponse,
    summary="Evaluate Driver Telemetry",
)
async def evaluate_driver_telemetry(payload: TelemetryEvaluationRequest):
    """Evaluate lap telemetry and return efficiency score, rating, and actionable feedback."""
    return compute_driver_evaluation(payload)


@app.get(
    "/api/v1/chart",
    summary="Generate Lap Telemetry Chart Stream",
    responses={200: {"content": {"image/png": {}}}},
)
async def get_lap_telemetry_chart(
    turn_3_regen: Optional[float] = Query(None, description="Turn 3 regen power (kW)"),
    turn_8_regen: Optional[float] = Query(None, description="Turn 8 regen power (kW)"),
    turn_13_regen: Optional[float] = Query(None, description="Turn 13 regen power (kW)"),
    coasting_distance: Optional[float] = Query(
        None, description="Lift-and-coast distance (m)"
    ),
    turn_3_peak_regen_kw: Optional[float] = Query(None),
    turn_8_peak_regen_kw: Optional[float] = Query(None),
    turn_13_peak_regen_kw: Optional[float] = Query(None),
    lift_and_coast_distance_m: Optional[float] = Query(None),
    peak_regen_kw: Optional[float] = Query(None),
    driver_name: Optional[str] = Query("Pascal Wehrlein", description="Driver name"),
    lap_number: Optional[int] = Query(1, description="Lap number"),
):
    """Generate and stream high-contrast dark-themed Matplotlib telemetry PNG chart."""
    # Resolve aliases
    t3 = (
        turn_3_regen
        if turn_3_regen is not None
        else (turn_3_peak_regen_kw if turn_3_peak_regen_kw is not None else 520.0)
    )
    t8 = (
        turn_8_regen
        if turn_8_regen is not None
        else (turn_8_peak_regen_kw if turn_8_peak_regen_kw is not None else 490.0)
    )
    t13 = (
        turn_13_regen
        if turn_13_regen is not None
        else (turn_13_peak_regen_kw if turn_13_peak_regen_kw is not None else 510.0)
    )
    coast = (
        coasting_distance
        if coasting_distance is not None
        else (
            lift_and_coast_distance_m
            if lift_and_coast_distance_m is not None
            else 55.0
        )
    )

    if peak_regen_kw is not None:
        if turn_3_regen is None and turn_3_peak_regen_kw is None:
            t3 = peak_regen_kw
        if turn_8_regen is None and turn_8_peak_regen_kw is None:
            t8 = peak_regen_kw
        if turn_13_regen is None and turn_13_peak_regen_kw is None:
            t13 = peak_regen_kw

    img_bytes = generate_telemetry_chart(
        turn_3_regen=t3,
        turn_8_regen=t8,
        turn_13_regen=t13,
        coasting_distance=coast,
        driver_name=driver_name or "Pascal Wehrlein",
        lap_number=lap_number or 1,
        peak_regen=peak_regen_kw,
    )
    return Response(content=img_bytes, media_type="image/png")


@app.get(
    "/dashboard",
    response_class=HTMLResponse,
    summary="Interactive Pit-Wall Dashboard",
)
async def get_dashboard(
    request: Request,
    turn_3_regen: Optional[float] = Query(None),
    turn_8_regen: Optional[float] = Query(None),
    turn_13_regen: Optional[float] = Query(None),
    coasting_distance: Optional[float] = Query(None),
    driver_name: Optional[str] = Query("Pascal Wehrlein"),
    lap_number: Optional[int] = Query(1),
):
    """Serve the interactive pit-wall driver performance dashboard via Jinja2."""
    default_request = TelemetryEvaluationRequest(
        driver_name=driver_name or "Pascal Wehrlein",
        lap_number=lap_number or 1,
        turn_3_peak_regen_kw=turn_3_regen if turn_3_regen is not None else 520.0,
        turn_8_peak_regen_kw=turn_8_regen if turn_8_regen is not None else 490.0,
        turn_13_peak_regen_kw=turn_13_regen if turn_13_regen is not None else 510.0,
        lift_and_coast_distance_m=coasting_distance
        if coasting_distance is not None
        else 55.0,
    )
    initial_eval = compute_driver_evaluation(default_request)

    # GEMINI.md Rule 3: When calling TemplateResponse, explicitly pass request=request and name="dashboard.html"
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"request": request, "initial_eval": initial_eval},
    )


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root path to interactive pit-wall dashboard."""
    return RedirectResponse(url="/dashboard")


@app.get("/api/v1/health", summary="Service Health Check")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "formula-e-driver-performance"}
