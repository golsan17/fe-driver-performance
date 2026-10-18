---
name: driver-evaluation
description: Evaluates Formula E Gen3 Evo driver telemetry against braking zone regeneration limits, lift-and-coast energy management, generates dark-themed Matplotlib telemetry charts, and calculates an efficiency score (1-100).
---
# Formula E Gen3 Evo Driver Performance Evaluation & Visualization Rules
Use these rules whenever analyzing lap telemetry, generating matplotlib charts, or serving pit-wall dashboards:
## 1. Physical Regeneration Constraints
- **Maximum Regen**: Formula E Gen3 Evo peak regenerative braking is capped at **600 kW**.
- **Sensor Fault Validation**: If telemetry reports `peak_regen_kw > 600`, flag `sensor_error: true` and cap the calculated value at 600 kW.
## 2. Heavy Braking Energy Recovery
- **Key Recovery Zones**: Turn 3, Turn 8, and Turn 13 are the primary heavy braking zones.
- **Target Regen**: Drivers should achieve $\ge 500\text{ kW}$ peak regen in Turn 3 and Turn 13, and $\ge 480\text{ kW}$ in Turn 8.
- **Scoring Weight**: Hitting targets in all three heavy zones contributes **50 points** to the score (Turn 3: 20 points, Turn 8: 10 points, Turn 13: 20 points).
## 3. Lift-and-Coast Energy Management
- **Target Distance**: Lift-and-coast (coasting before braking) must start at least **50 meters** before the braking zone threshold.
- **Scoring Weight**: Coasting $\ge 50\text{ meters}$ before braking zones contributes **50 points** to the score. If coasting is between 25m and 49m, award **25 points**. Below 25m, award **0 points**.
## 4. Matplotlib Telemetry Chart Design
- **Theme**: Use `plt.style.use('dark_background')` with high-contrast electric cyan (`#00f0ff`) and volt green (`#39ff14`) bars.
- **Reference Lines**: Draw horizontal dashed lines at **480 kW** (Turn 8 Target - Cyan/Gold), **500 kW** (Target - Gold `#ffd700`) and **600 kW** (Max Physical Limit - Red `#ff3366`).
- **Export**: Render charts as PNG image buffers returned via HTTP or base64-encoded strings for inline HTML rendering.
## 5. Output Response Schema
Calculate `efficiency_score` as the sum of braking energy points (max 50) and lift-and-coast points (max 50).
Return JSON containing:
- `efficiency_score` (integer 1-100)
- `rating` ("EXCELLENT", "OPTIMAL", or "NEEDS_IMPROVEMENT")
- `sensor_fault_detected` (boolean)
- `feedback` (list of actionable strings for the race engineer)
