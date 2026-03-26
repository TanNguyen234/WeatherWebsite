from __future__ import annotations

from datetime import datetime, timedelta

from weather.ml.predictor import ModelInferenceError, predict_weather
from weather.services.weather_service import get_current_weather, get_hourly_weather_forecast


ALLOWED_FORECAST_DAYS = {3, 7}
ALLOWED_HORIZON_HOURS = {1, 3, 12, 24}


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    normalized = str(value).strip()
    if not normalized:
        return None

    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    if len(normalized) == 16 and "T" in normalized:
        normalized = f"{normalized}:00"

    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def resolve_horizon_hours(forecast_days: int | None = None, horizon_hours: int | None = None) -> int:
    """Resolve prediction horizon with backward compatibility.

    Priority:
    1) horizon_hours (UI contract: 1, 3, 12, 24)
    2) forecast_days (legacy contract: 3 or 7)
    """
    if horizon_hours is not None:
        hours = int(horizon_hours)
        if hours not in ALLOWED_HORIZON_HOURS:
            raise ValueError("horizon_hours chỉ hỗ trợ 1, 3, 12 hoặc 24")
        return hours

    if forecast_days is not None:
        days = int(forecast_days)
        if days not in ALLOWED_FORECAST_DAYS:
            raise ValueError("forecast_days chỉ hỗ trợ 3 hoặc 7")
        return days * 24

    hours = 3
    return hours


def build_prediction_rows(prediction_payload: dict) -> list[dict]:
    """Build tabular rows for export and visualization from prediction output."""
    api_hourly = prediction_payload.get("api_hourly") or []
    ai_series = (prediction_payload.get("ai_result") or {}).get("series") or []

    max_len = max(len(api_hourly), len(ai_series))
    if max_len == 0:
        return []

    first_api_timestamp = None
    for api_point in api_hourly:
        first_api_timestamp = _parse_iso_datetime(api_point.get("timestamp"))
        if first_api_timestamp is not None:
            break

    base_time = (
        first_api_timestamp
        if first_api_timestamp is not None
        else datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    )
    rows = []
    for idx in range(max_len):
        api_point = api_hourly[idx] if idx < len(api_hourly) else {}
        ai_point = ai_series[idx] if idx < len(ai_series) else {}

        timestamp = api_point.get("timestamp")
        if not timestamp:
            timestamp = (base_time + timedelta(hours=idx)).isoformat()

        rows.append(
            {
                "hour_offset": idx + 1,
                "timestamp": timestamp,
                "api_temperature": api_point.get("temperature"),
                "api_humidity": api_point.get("humidity"),
                "api_wind_speed": api_point.get("wind_speed"),
                "ai_temperature": ai_point.get("temperature"),
                "ai_humidity": ai_point.get("humidity"),
                "ai_wind_speed": ai_point.get("wind_speed"),
            }
        )

    return rows


def get_prediction_comparison(
    lat: float,
    lng: float,
    *,
    forecast_days: int | None = None,
    horizon_hours: int | None = None,
) -> dict:
    horizon = resolve_horizon_hours(forecast_days=forecast_days, horizon_hours=horizon_hours)

    api_weather = get_current_weather(lat, lng)
    api_hourly = get_hourly_weather_forecast(lat, lng, hours=horizon)
    ai_weather = None
    ai_status = {
        "available": False,
        "mode": "local-ai",
        "message": None,
        "error": None,
    }

    try:
        ai_weather = predict_weather(lat, lng, api_weather, horizon_hours=horizon)
        ai_status.update(
            {
                "available": True,
                "message": "Mô hình AI cục bộ dự đoán thành công",
                "error": None,
            }
        )
    except ModelInferenceError as exc:
        ai_status.update(
            {
                "available": False,
                "message": "Mô hình AI cục bộ hiện không khả dụng",
                "error": str(exc),
            }
        )
    except Exception as exc:
        ai_status.update(
            {
                "available": False,
                "message": "Lỗi runtime không mong muốn của AI",
                "error": str(exc),
            }
        )

    comparison = {
        "temperature_delta": None,
        "humidity_delta": None,
        "wind_speed_delta": None,
        "hourly_delta": [],
    }
    if ai_weather is not None:
        ai_series = ai_weather.get("series", [])
        hourly_delta = []
        max_len = min(len(ai_series), len(api_hourly))
        for idx in range(max_len):
            ai_point = ai_series[idx]
            api_point = api_hourly[idx]
            hourly_delta.append(
                {
                    "hour_offset": idx + 1,
                    "temperature_delta": round(
                        float(ai_point.get("temperature", 0)) - float(api_point.get("temperature", 0)),
                        1,
                    ),
                    "humidity_delta": round(
                        float(ai_point.get("humidity", 0)) - float(api_point.get("humidity", 0)),
                        1,
                    ),
                    "wind_speed_delta": round(
                        float(ai_point.get("wind_speed", 0)) - float(api_point.get("wind_speed", 0)),
                        1,
                    ),
                }
            )

        latest_idx = max_len - 1 if max_len > 0 else None
        comparison = {
            "temperature_delta": hourly_delta[latest_idx]["temperature_delta"] if latest_idx is not None else None,
            "humidity_delta": hourly_delta[latest_idx]["humidity_delta"] if latest_idx is not None else None,
            "wind_speed_delta": hourly_delta[latest_idx]["wind_speed_delta"] if latest_idx is not None else None,
            "hourly_delta": hourly_delta,
        }

    resolved_days = max(1, int((horizon + 23) // 24))
    payload = {
        "location": {
            "latitude": round(float(lat), 6),
            "longitude": round(float(lng), 6),
        },
        "forecast_days": resolved_days,
        "horizon_hours": horizon,
        "api_result": {
            "temperature": api_weather.get("temperature"),
            "humidity": api_weather.get("humidity"),
            "wind_speed": api_weather.get("wind_speed"),
            "description": api_weather.get("description"),
            "source": api_weather.get("source"),
        },
        "api_hourly": api_hourly,
        "ai_status": ai_status,
        "ai_result": {
            "temperature": ai_weather.get("temperature") if ai_weather else None,
            "humidity": ai_weather.get("humidity") if ai_weather else None,
            "wind_speed": ai_weather.get("wind_speed") if ai_weather else None,
            "description": ai_weather.get("description") if ai_weather else None,
            "confidence": ai_weather.get("confidence") if ai_weather else None,
            "prediction_score": ai_weather.get("prediction_score") if ai_weather else None,
            "model": ai_weather.get("model") if ai_weather else None,
            "horizon_hours": ai_weather.get("horizon_hours") if ai_weather else None,
            "source": ai_weather.get("source") if ai_weather else None,
            "series": ai_weather.get("series") if ai_weather else None,
        }
        if ai_weather
        else None,
        "comparison": comparison,
    }
    payload["rows"] = build_prediction_rows(payload)
    return payload
