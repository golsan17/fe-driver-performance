"""Comprehensive pytest suite for Formula E Driver Performance Evaluation service."""

import io
from fastapi.testclient import TestClient
from PIL import Image
import pytest

from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test Case 1: Ideal Lap Evaluation
# ---------------------------------------------------------------------------
def test_ideal_lap_evaluation():
    """Verify ideal lap: >= 500 kW in T3/T13, >= 480 kW in T8, >= 50m lift-and-coast yields 100 & EXCELLENT."""
    payload = {
        "driver_name": "Pascal Wehrlein",
        "lap_number": 14,
        "turn_3_peak_regen_kw": 535.0,
        "turn_8_peak_regen_kw": 495.0,
        "turn_13_peak_regen_kw": 515.0,
        "lift_and_coast_distance_m": 55.0,
    }
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()
    assert data["efficiency_score"] == 100
    assert data["rating"] == "EXCELLENT"
    assert data["sensor_fault_detected"] is False
    assert data["sensor_error"] is False
    assert data["braking_points"] == 50
    assert data["lift_and_coast_points"] == 50
    assert data["turn_3_peak_regen_kw"] == 535.0
    assert data["turn_8_peak_regen_kw"] == 495.0
    assert data["turn_13_peak_regen_kw"] == 515.0
    assert data["lift_and_coast_distance_m"] == 55.0
    assert data["driver_name"] == "Pascal Wehrlein"
    assert data["lap_number"] == 14

    # Feedback validation
    assert isinstance(data["feedback"], list)
    assert len(data["feedback"]) >= 4
    feedback_str = " ".join(data["feedback"])
    assert "Turn 3" in feedback_str
    assert "Turn 8" in feedback_str
    assert "Turn 13" in feedback_str
    assert "Lift-and-Coast" in feedback_str


# ---------------------------------------------------------------------------
# Test Case 2: Matplotlib PNG Stream Byte Validation
# ---------------------------------------------------------------------------
def test_matplotlib_png_stream_byte_validation():
    """Verify GET /api/v1/chart returns a valid binary PNG stream with correct headers and magic bytes."""
    response = client.get("/api/v1/chart")
    assert response.status_code == 200
    assert "image/png" in response.headers["content-type"]

    # Validate standard PNG magic signature bytes: \x89PNG\r\n\x1a\n
    png_magic_bytes = b"\x89PNG\r\n\x1a\n"
    assert response.content.startswith(png_magic_bytes), "Response content does not start with PNG magic bytes"

    # Validate non-trivial payload size
    assert len(response.content) > 5000, f"PNG stream suspiciously small: {len(response.content)} bytes"

    # Verify PNG is decodable as a valid raster image
    image = Image.open(io.BytesIO(response.content))
    assert image.format == "PNG"
    width, height = image.size
    assert width > 200 and height > 200, f"Unexpected image dimensions: {width}x{height}"


def test_matplotlib_png_stream_with_custom_telemetry_parameters():
    """Verify GET /api/v1/chart accepts custom query parameters including Turn 8 and streams valid PNG bytes."""
    params = {
        "turn_3_regen": 550.0,
        "turn_8_regen": 485.0,
        "turn_13_regen": 520.0,
        "coasting_distance": 58.0,
        "driver_name": "Mitch Evans",
        "lap_number": 8,
    }
    response = client.get("/api/v1/chart", params=params)
    assert response.status_code == 200
    assert "image/png" in response.headers["content-type"]
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")

    image = Image.open(io.BytesIO(response.content))
    assert image.format == "PNG"


# ---------------------------------------------------------------------------
# Test Case 3: Interactive Dashboard HTML Response
# ---------------------------------------------------------------------------
def test_dashboard_html_response():
    """Verify GET /dashboard returns Jinja2-rendered interactive HTML with pit-wall elements and Turn 8."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    html = response.text
    # Verify core pit-wall UI and Formula E branding elements
    assert "<!DOCTYPE html>" in html
    assert "FIA GEN3 EVO" in html
    assert "PIT-WALL TELEMETRY CONSOLE" in html
    assert "Efficiency Score" in html
    assert "Heavy Braking Recovery" in html
    assert "Turn 8 Regen" in html or "Turn 8" in html
    assert "Lift-and-Coast Management" in html
    assert "/api/v1/chart" in html
    assert "telemetryForm" in html
    assert "RUN TELEMETRY ANALYSIS" in html


def test_dashboard_html_response_custom_query():
    """Verify GET /dashboard renders prefilled telemetry when query parameters are supplied."""
    response = client.get("/dashboard?driver_name=Jake%20Dennis&lap_number=22&turn_3_regen=525&turn_8_regen=485")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Jake Dennis" in response.text


# ---------------------------------------------------------------------------
# Test Case 4: Sensor Fault (> 600 kW Regen Capping & Flagging)
# ---------------------------------------------------------------------------
def test_sensor_fault_over_600kw_turn_3():
    """Verify telemetry with Turn 3 regen > 600 kW flags sensor fault and caps value at 600 kW."""
    payload = {
        "driver_name": "Jean-Éric Vergne",
        "turn_3_peak_regen_kw": 680.0,  # Exceeds 600 kW physical limit
        "turn_8_peak_regen_kw": 490.0,
        "turn_13_peak_regen_kw": 510.0,
        "lift_and_coast_distance_m": 52.0,
    }
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["sensor_fault_detected"] is True
    assert data["sensor_error"] is True
    # Physical value capped at 600.0 kW
    assert data["turn_3_peak_regen_kw"] == 600.0
    # Capped 600.0 kW >= 500 kW target (20 pts), T8 490 >= 480 (10 pts), T13 510 >= 500 (20 pts) -> 50 pts
    assert data["braking_points"] == 50
    assert data["lift_and_coast_points"] == 50
    assert data["efficiency_score"] == 100
    assert data["rating"] == "EXCELLENT"

    # Actionable sensor fault feedback message verification
    sensor_feedback = [fb for fb in data["feedback"] if "Sensor fault detected" in fb or "CRITICAL" in fb]
    assert len(sensor_feedback) > 0
    assert "600 kW" in sensor_feedback[0]


def test_sensor_fault_over_600kw_turn_8():
    """Verify telemetry with Turn 8 regen > 600 kW flags sensor fault and caps value at 600 kW."""
    payload = {
        "turn_3_peak_regen_kw": 520.0,
        "turn_8_peak_regen_kw": 660.0,  # Exceeds 600 kW physical limit
        "turn_13_peak_regen_kw": 510.0,
        "lift_and_coast_distance_m": 50.0,
    }
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["sensor_fault_detected"] is True
    assert data["sensor_error"] is True
    assert data["turn_8_peak_regen_kw"] == 600.0
    assert data["braking_points"] == 50
    assert data["efficiency_score"] == 100


def test_sensor_fault_over_600kw_peak_regen():
    """Verify general peak_regen_kw > 600 kW flags sensor fault and caps values at 600 kW."""
    payload = {
        "peak_regen_kw": 645.0,  # Exceeds 600 kW
        "lift_and_coast_distance_m": 40.0,
    }
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["sensor_fault_detected"] is True
    assert data["sensor_error"] is True
    assert data["peak_regen_kw"] == 600.0
    assert data["turn_3_peak_regen_kw"] == 600.0
    assert data["turn_8_peak_regen_kw"] == 600.0
    assert data["turn_13_peak_regen_kw"] == 600.0
    assert data["braking_points"] == 50
    assert data["lift_and_coast_points"] == 25  # 25m - 49m -> 25 pts
    assert data["efficiency_score"] == 75
    assert data["rating"] == "OPTIMAL"


# ---------------------------------------------------------------------------
# Additional Comprehensive Test Cases (Turn 8 Specific, Ratings, & Routing)
# ---------------------------------------------------------------------------
def test_turn_8_scoring_and_feedback():
    """Verify Turn 8 meets target at 480 kW (10 pts) and misses below 480 kW (0 pts)."""
    # Turn 8 achieves target
    payload_success = {
        "turn_3_peak_regen_kw": 400.0,  # 0 pts
        "turn_8_peak_regen_kw": 480.0,  # 10 pts
        "turn_13_peak_regen_kw": 400.0,  # 0 pts
        "lift_and_coast_distance_m": 0.0,
    }
    resp1 = client.post("/api/v1/evaluate", json=payload_success)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["braking_points"] == 10
    assert any("Turn 8: Target regen achieved" in fb for fb in data1["feedback"])

    # Turn 8 misses target
    payload_miss = {
        "turn_3_peak_regen_kw": 400.0,  # 0 pts
        "turn_8_peak_regen_kw": 475.0,  # Miss: 0 pts
        "turn_13_peak_regen_kw": 400.0,  # 0 pts
        "lift_and_coast_distance_m": 0.0,
    }
    resp2 = client.post("/api/v1/evaluate", json=payload_miss)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["braking_points"] == 0
    assert any("Turn 8: Under-regenerating" in fb for fb in data2["feedback"])


def test_evaluate_intermediate_optimal_score_75():
    """Verify intermediate coasting (25m - 49m) gives 25 coasting points and OPTIMAL rating."""
    payload = {
        "turn_3_peak_regen_kw": 520.0,
        "turn_8_peak_regen_kw": 490.0,
        "turn_13_peak_regen_kw": 510.0,
        "lift_and_coast_distance_m": 35.0,  # 25m - 49m threshold
    }
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["braking_points"] == 50
    assert data["lift_and_coast_points"] == 25
    assert data["efficiency_score"] == 75
    assert data["rating"] == "OPTIMAL"


def test_evaluate_single_turn_braking_recovery():
    """Verify hitting >= 500 kW in only Turn 3 awards 20 braking points."""
    payload = {
        "turn_3_peak_regen_kw": 520.0,  # Hit (20 pts)
        "turn_8_peak_regen_kw": 420.0,  # Miss (0 pts)
        "turn_13_peak_regen_kw": 440.0,  # Miss (0 pts)
        "lift_and_coast_distance_m": 55.0,  # Hit (50 pts)
    }
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["braking_points"] == 20
    assert data["lift_and_coast_points"] == 50
    assert data["efficiency_score"] == 70
    assert data["rating"] == "OPTIMAL"


def test_evaluate_poor_performance_needs_improvement():
    """Verify score < 50 awards NEEDS_IMPROVEMENT rating."""
    payload = {
        "turn_3_peak_regen_kw": 350.0,
        "turn_8_peak_regen_kw": 380.0,
        "turn_13_peak_regen_kw": 400.0,
        "lift_and_coast_distance_m": 15.0,  # < 25m -> 0 pts
    }
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["braking_points"] == 0
    assert data["lift_and_coast_points"] == 0
    assert data["efficiency_score"] == 0
    assert data["rating"] == "NEEDS_IMPROVEMENT"
    assert data["sensor_fault_detected"] is False


def test_root_redirect_to_dashboard():
    """Verify GET / redirects to /dashboard."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/dashboard"


def test_health_check():
    """Verify GET /api/v1/health returns healthy status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
