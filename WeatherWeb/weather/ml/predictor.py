"""Real pre-trained weather predictor for the Predict page.

Inference stack:
- Pre-trained model: amazon/chronos-t5-tiny (HuggingFace)
- Historical input: Open-Meteo archive hourly series
- No training step in this project
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import requests

MODEL_ID = "amazon/chronos-t5-tiny"
MODEL_CACHE_DIR = Path(__file__).resolve().parent / "saved_models" / "hf_cache"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


@dataclass
class ForecastStats:
    value: float
    spread: float


class ModelInferenceError(RuntimeError):
    """Raised when local AI model inference cannot produce a valid output."""


_PIPELINE = None


def _get_torch():
    try:
        import torch
    except ImportError as exc:
        raise ModelInferenceError("Thiếu thư viện torch cho local model inference") from exc
    return torch


def _get_pipeline():
    global _PIPELINE
    if _PIPELINE is not None:
        return _PIPELINE

    try:
        from chronos import ChronosPipeline
    except ImportError as exc:
        raise ModelInferenceError(
            "Thiếu thư viện chronos-forecasting. Cài bằng: pip install chronos-forecasting"
        ) from exc

    MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    torch = _get_torch()
    dtype = torch.float32

    _PIPELINE = ChronosPipeline.from_pretrained(
        MODEL_ID,
        cache_dir=str(MODEL_CACHE_DIR),
        torch_dtype=dtype,
        device_map="cpu",
    )
    return _PIPELINE


def _condition_from_temp(temp: float) -> tuple[str, str, str]:
    if temp >= 34:
        return "Nắng nóng", "Clear", "01d"
    if temp >= 29:
        return "Trời quang", "Clear", "01d"
    if temp >= 24:
        return "Ít mây", "Clouds", "02d"
    if temp >= 20:
        return "Mây rải rác", "Clouds", "03d"
    return "Mưa nhẹ", "Rain", "10d"


def _fetch_open_meteo_history(lat: float, lng: float, days: int = 10) -> dict[str, list[float]]:
    end_date = datetime.now(tz=timezone.utc).date() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)

    params = {
        "latitude": lat,
        "longitude": lng,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        "timezone": "UTC",
    }

    resp = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    hourly = payload.get("hourly", {})

    temp = [float(x) for x in hourly.get("temperature_2m", []) if x is not None]
    humidity = [float(x) for x in hourly.get("relative_humidity_2m", []) if x is not None]
    wind = [float(x) for x in hourly.get("wind_speed_10m", []) if x is not None]

    if len(temp) < 48 or len(humidity) < 48 or len(wind) < 48:
        raise ModelInferenceError("Không đủ dữ liệu lịch sử để chạy local model")

    return {
        "temperature": temp,
        "humidity": humidity,
        "wind_speed": wind,
    }


def _to_numpy(samples: Any) -> np.ndarray:
    if hasattr(samples, "detach"):
        samples = samples.detach().cpu().numpy()
    elif hasattr(samples, "cpu"):
        samples = samples.cpu().numpy()
    return np.asarray(samples, dtype=np.float32)


def _forecast_series(values: list[float], horizon_hours: int) -> ForecastStats:
    pipeline = _get_pipeline()
    torch = _get_torch()
    context = torch.tensor(values, dtype=torch.float32)

    samples = pipeline.predict(context=context, prediction_length=horizon_hours)
    arr = _to_numpy(samples)

    if arr.ndim == 3:
        # [batch, n_samples, horizon]
        horizon_values = arr[0, :, horizon_hours - 1]
    elif arr.ndim == 2:
        # [n_samples, horizon]
        horizon_values = arr[:, horizon_hours - 1]
    elif arr.ndim == 1:
        horizon_values = np.array([arr[horizon_hours - 1]], dtype=np.float32)
    else:
        raise ModelInferenceError("Định dạng output của local model không hợp lệ")

    return ForecastStats(
        value=float(np.median(horizon_values)),
        spread=float(np.std(horizon_values)),
    )


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def predict_weather(lat: float, lng: float, current_weather: dict, horizon_hours: int = 3) -> dict:
    if horizon_hours < 1 or horizon_hours > 24:
        raise ValueError("horizon_hours phải nằm trong khoảng [1, 24]")

    try:
        history = _fetch_open_meteo_history(lat, lng, days=10)
        temp_stats = _forecast_series(history["temperature"], horizon_hours)
        humidity_stats = _forecast_series(history["humidity"], horizon_hours)
        wind_stats = _forecast_series(history["wind_speed"], horizon_hours)
    except ModelInferenceError:
        raise
    except Exception as exc:
        raise ModelInferenceError(f"Local model inference failed: {exc}") from exc

    temperature = round(_clamp(temp_stats.value, -30.0, 55.0), 1)
    humidity = int(round(_clamp(humidity_stats.value, 10.0, 100.0), 0))
    wind_speed = round(_clamp(wind_stats.value, 0.0, 60.0), 1)

    spread_norm = _clamp(temp_stats.spread / 4.0, 0.0, 1.0)
    confidence = round(_clamp(1.0 - spread_norm, 0.35, 0.97), 2)
    model_name = MODEL_ID
    source = "ai_local_chronos_openmeteo_history"

    description, weather_main, icon = _condition_from_temp(temperature)

    comfort_score = round(
        _clamp(100 - abs(temperature - 26) * 3 - abs(humidity - 65) * 0.6 - wind_speed * 1.2, 0.0, 100.0),
        1,
    )

    return {
        "model": model_name,
        "horizon_hours": horizon_hours,
        "temperature": temperature,
        "humidity": humidity,
        "wind_speed": wind_speed,
        "pressure": int(float(current_weather.get("pressure", 1013))),
        "description": description,
        "weather_main": weather_main,
        "icon": icon,
        "confidence": confidence,
        "prediction_score": comfort_score,
        "source": source,
    }
