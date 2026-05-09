from __future__ import annotations

import base64
from datetime import datetime
from io import BytesIO

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _parse_dt(timestamp: str | None) -> datetime | None:
    if not timestamp:
        return None

    normalized = str(timestamp)
    if len(normalized) == 16 and "T" in normalized:
        normalized = f"{normalized}:00"
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _infer_granularity(rows: list[dict]) -> str:
    times = []
    for row in rows:
        parsed = _parse_dt(row.get("timestamp"))
        if parsed is not None:
            times.append(parsed)

    if len(times) < 2:
        return "hourly"

    times.sort()
    min_diff_seconds = None
    for idx in range(1, len(times)):
        diff_seconds = int((times[idx] - times[idx - 1]).total_seconds())
        if diff_seconds <= 0:
            continue
        if min_diff_seconds is None or diff_seconds < min_diff_seconds:
            min_diff_seconds = diff_seconds

    if min_diff_seconds is None:
        return "hourly"

    return "daily" if min_diff_seconds >= 23 * 3600 else "hourly"


def _should_show_date(rows: list[dict]) -> bool:
    if len(rows) >= 24:
        return True

    day_keys = set()
    hour_minute_keys = set()
    for row in rows:
        parsed = _parse_dt(row.get("timestamp"))
        if parsed is None:
            continue
        day_keys.add(parsed.strftime("%Y-%m-%d"))
        hm_key = parsed.strftime("%H:%M")
        if hm_key in hour_minute_keys:
            return True
        hour_minute_keys.add(hm_key)

    return len(day_keys) > 1


def _parse_time_label(
    timestamp: str | None,
    hour_offset: int | None,
    *,
    show_date: bool,
    granularity: str,
) -> str:
    parsed = _parse_dt(timestamp)
    if parsed is not None:
        if granularity == "daily":
            return parsed.strftime("%d/%m")
        if show_date:
            return parsed.strftime("%d/%m %H:%M")
        return parsed.strftime("%H:%M")

    if timestamp:
        normalized = str(timestamp)
        return normalized.replace("T", " ")[:16]
    if hour_offset is not None:
        return f"+{hour_offset}h"
    return "--"


def generate_prediction_chart_png(rows: list[dict], metric: str = "temperature") -> bytes:
    metric_map = {
        "temperature": ("api_temperature", "ai_temperature", "Nhiệt độ", "°C"),
        "humidity": ("api_humidity", "ai_humidity", "Độ ẩm", "%"),
        "wind_speed": ("api_wind_speed", "ai_wind_speed", "Tốc độ gió", "m/s"),
    }
    api_key, ai_key, title, unit = metric_map.get(metric, metric_map["temperature"])

    show_date = _should_show_date(rows)
    granularity = _infer_granularity(rows)
    labels = [
        _parse_time_label(
            r.get("timestamp"),
            r.get("hour_offset"),
            show_date=show_date,
            granularity=granularity,
        )
        for r in rows
    ]
    api_values = [r.get(api_key) for r in rows]
    ai_values = [r.get(ai_key) for r in rows]

    fig, ax = plt.subplots(figsize=(12, 5), dpi=120)
    ax.plot(labels, api_values, label=f"API {title} ({unit})", color="#2563eb", linewidth=2)
    if any(v is not None for v in ai_values):
        ax.plot(labels, ai_values, label=f"AI {title} ({unit})", color="#10b981", linewidth=2, linestyle="--")

    ax.set_title(f"So sánh dự báo {title}")
    ax.set_xlabel("Thời gian")
    ax.set_ylabel(f"{title} ({unit})")
    ax.grid(alpha=0.25)
    ax.legend()

    if len(labels) > 24:
        step = max(1, len(labels) // 12)
        for idx, tick in enumerate(ax.get_xticklabels()):
            tick.set_visible(idx % step == 0)

    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    return buffer.getvalue()


def png_to_base64(png_bytes: bytes) -> str:
    return base64.b64encode(png_bytes).decode("ascii")
