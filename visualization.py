"""Matplotlib Telemetry Visualization Engine for Formula E Gen3 Evo."""

import base64
import io
from typing import Optional

# GEMINI.md Rule 1: Always call matplotlib.use('Agg') BEFORE importing matplotlib.pyplot
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate_telemetry_chart(
    turn_3_regen: float = 520.0,
    turn_8_regen: float = 490.0,
    turn_13_regen: float = 510.0,
    coasting_distance: float = 55.0,
    driver_name: str = "Pascal Wehrlein",
    lap_number: int = 1,
    peak_regen: Optional[float] = None,
) -> bytes:
    """Generate high-contrast dark-themed Formula E telemetry PNG chart."""
    plt.style.use("dark_background")

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10, 7.5), gridspec_kw={"height_ratios": [1.3, 0.9]}
    )
    fig.patch.set_facecolor("#0b0e14")
    ax1.set_facecolor("#111722")
    ax2.set_facecolor("#111722")

    # Subplot 1: Heavy Braking & Sector Regen (kW)
    # Highlight Turn 3, Turn 8, and Turn 13 heavy recovery zones
    turns = [
        "Turn 1",
        "Turn 3\n(Heavy Zone)",
        "Turn 8\n(Heavy Zone)",
        "Turn 10",
        "Turn 13\n(Heavy Zone)",
        "Turn 15",
    ]

    t3_val = min(600.0, float(turn_3_regen))
    t8_val = min(600.0, float(turn_8_regen))
    t13_val = min(600.0, float(turn_13_regen))

    # Values across circuit
    regen_values = [330.0, t3_val, t8_val, 410.0, t13_val, 355.0]

    # Colors: Electric cyan (#00f0ff) and Volt green (#39ff14)
    colors = [
        "#00f0ff",
        "#39ff14" if t3_val >= 500.0 else "#00f0ff",
        "#39ff14" if t8_val >= 480.0 else "#00f0ff",
        "#00f0ff",
        "#39ff14" if t13_val >= 500.0 else "#00f0ff",
        "#00f0ff",
    ]

    bars1 = ax1.bar(
        turns,
        regen_values,
        color=colors,
        width=0.55,
        edgecolor="#ffffff",
        linewidth=0.6,
        alpha=0.9,
    )

    # Reference lines: Turn 8 Target 480 kW, T3/T13 Target 500 kW, Limit 600 kW
    ax1.axhline(
        480,
        color="#00f0ff",
        linestyle=":",
        linewidth=1.6,
        label="480 kW Target (Turn 8 Goal)",
    )
    ax1.axhline(
        500,
        color="#ffd700",
        linestyle="--",
        linewidth=2.0,
        label="500 kW Target (T3 / T13 Goal)",
    )
    ax1.axhline(
        600,
        color="#ff3366",
        linestyle="--",
        linewidth=2.0,
        label="600 kW Max Physical Limit (Gen3 Evo)",
    )

    # Text annotations on top of bars
    for bar, val in zip(bars1, regen_values):
        height = bar.get_height()
        ax1.annotate(
            f"{val:.0f} kW",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9.5,
            fontweight="bold",
            color="#ffffff",
        )

    ax1.set_ylim(0, 700)
    ax1.set_ylabel("Peak Regen (kW)", color="#e0e0e0", fontsize=11, fontweight="bold")
    ax1.set_title(
        f"FORMULA E GEN3 EVO TELEMETRY — LAP {lap_number} REGEN RECOVERY [{driver_name.upper()}]",
        color="#00f0ff",
        fontsize=12.5,
        fontweight="bold",
        pad=10,
    )
    ax1.legend(loc="upper right", facecolor="#151b26", edgecolor="#2d3748", fontsize=9.0)
    ax1.grid(True, linestyle=":", alpha=0.3, color="#4a5568")

    # Subplot 2: Lift-and-Coast Energy Management (Meters)
    coast_val = float(coasting_distance)
    approach_zones = ["T3 Approach", "T8 Approach", "T13 Approach"]
    approach_distances = [
        coast_val,
        max(10.0, coast_val * 0.85),
        max(15.0, coast_val * 0.95),
    ]
    coast_colors = [
        "#39ff14" if coast_val >= 50.0 else ("#ffd700" if coast_val >= 25.0 else "#00f0ff"),
        "#00f0ff",
        "#39ff14" if (coast_val * 0.95) >= 50.0 else ("#ffd700" if (coast_val * 0.95) >= 25.0 else "#00f0ff"),
    ]

    bars2 = ax2.bar(
        approach_zones,
        approach_distances,
        color=coast_colors,
        width=0.45,
        edgecolor="#ffffff",
        linewidth=0.6,
        alpha=0.9,
    )

    ax2.axhline(
        50,
        color="#39ff14",
        linestyle="--",
        linewidth=1.8,
        label="50m Target (Optimal Coasting)",
    )
    ax2.axhline(
        25,
        color="#ffd700",
        linestyle="--",
        linewidth=1.8,
        label="25m Minimum Threshold",
    )

    for bar, val in zip(bars2, approach_distances):
        height = bar.get_height()
        ax2.annotate(
            f"{val:.1f} m",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9.5,
            fontweight="bold",
            color="#ffffff",
        )

    ax2.set_ylim(0, max(75.0, coast_val + 15.0))
    ax2.set_ylabel("Coasting Distance (m)", color="#e0e0e0", fontsize=11, fontweight="bold")
    ax2.set_title(
        "LIFT-AND-COAST ENERGY CONSERVATION BY BRAKING APPROACH",
        color="#39ff14",
        fontsize=11.5,
        fontweight="bold",
        pad=8,
    )
    ax2.legend(loc="upper right", facecolor="#151b26", edgecolor="#2d3748", fontsize=9.5)
    ax2.grid(True, linestyle=":", alpha=0.3, color="#4a5568")

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(
        buf,
        format="png",
        dpi=110,
        facecolor=fig.get_facecolor(),
        edgecolor="none",
        bbox_inches="tight",
    )
    plt.close(fig)
    return buf.getvalue()


def generate_chart_base64(**kwargs) -> str:
    """Generate base64 encoded PNG telemetry chart."""
    img_bytes = generate_telemetry_chart(**kwargs)
    return base64.b64encode(img_bytes).decode("utf-8")
