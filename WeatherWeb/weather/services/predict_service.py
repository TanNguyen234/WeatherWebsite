from weather.ml.predictor import ModelInferenceError, predict_weather
from weather.services.weather_service import get_current_weather


def get_prediction_comparison(lat: float, lng: float, horizon_hours: int = 3) -> dict:
    api_weather = get_current_weather(lat, lng)
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
            "message": "Local AI model inference completed",
            "error": None,
        })
    except ModelInferenceError as exc:
        ai_status.update({
            "available": False,
            "message": "Local AI model is unavailable",
            "error": str(exc),
        })
    except Exception as exc:
        ai_status.update({
            "available": False,
            "message": "Unexpected AI runtime error",
            "error": str(exc),
        })

    comparison = {
        "temperature_delta": None,
        "humidity_delta": None,
        "wind_speed_delta": None,
    }
    if ai_weather is not None:
        comparison = {
            "temperature_delta": round(float(ai_weather.get("temperature", 0)) - float(api_weather.get("temperature", 0)), 1),
            "humidity_delta": round(float(ai_weather.get("humidity", 0)) - float(api_weather.get("humidity", 0)), 1),
            "wind_speed_delta": round(float(ai_weather.get("wind_speed", 0)) - float(api_weather.get("wind_speed", 0)), 1),
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
        } if ai_weather else None,
        "comparison": comparison,
    }
