from weather.ml.predictor import ModelInferenceError, predict_weather
from weather.services.weather_service import get_current_weather, get_hourly_weather_forecast


def get_prediction_comparison(lat: float, lng: float, horizon_hours: int = 3) -> dict:
    api_weather = get_current_weather(lat, lng)
    api_hourly = get_hourly_weather_forecast(lat, lng, hours=horizon_hours)
    ai_weather = None
    ai_status = {
        "available": False,
        "mode": "local-ai",
        "message": None,
        "error": None,
    }

    try:
        ai_weather = predict_weather(lat, lng, api_weather, horizon_hours=horizon_hours)
        ai_status.update({
            "available": True,
            "message": "Mô hình AI cục bộ dự đoán thành công",
            "error": None,
        })
    except ModelInferenceError as exc:
        ai_status.update({
            "available": False,
            "message": "Mô hình AI cục bộ hiện không khả dụng",
            "error": str(exc),
        })
    except Exception as exc:
        ai_status.update({
            "available": False,
            "message": "Lỗi runtime không mong muốn của AI",
            "error": str(exc),
        })

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
                    "temperature_delta": round(float(ai_point.get("temperature", 0)) - float(api_point.get("temperature", 0)), 1),
                    "humidity_delta": round(float(ai_point.get("humidity", 0)) - float(api_point.get("humidity", 0)), 1),
                    "wind_speed_delta": round(float(ai_point.get("wind_speed", 0)) - float(api_point.get("wind_speed", 0)), 1),
                }
            )

        latest_idx = max_len - 1 if max_len > 0 else None
        comparison = {
            "temperature_delta": hourly_delta[latest_idx]["temperature_delta"] if latest_idx is not None else None,
            "humidity_delta": hourly_delta[latest_idx]["humidity_delta"] if latest_idx is not None else None,
            "wind_speed_delta": hourly_delta[latest_idx]["wind_speed_delta"] if latest_idx is not None else None,
            "hourly_delta": hourly_delta,
        }

    return {
        "location": {
            "latitude": round(float(lat), 6),
            "longitude": round(float(lng), 6),
        },
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
        } if ai_weather else None,
        "comparison": comparison,
    }
