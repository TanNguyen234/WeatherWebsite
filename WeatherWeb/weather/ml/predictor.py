"""Real pre-trained weather predictor for the Predict page.

Inference stack:
- Pre-trained model: amazon/chronos-t5-tiny (HuggingFace)
- Historical input: Open-Meteo archive hourly series
- No training step in this project
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
from typing import Any

import numpy as np
import requests

MODEL_ID = "amazon/chronos-t5-tiny"
MODEL_CACHE_DIR = Path(__file__).resolve().parent / "saved_models" / "hf_cache"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

logger = logging.getLogger(__name__)


@dataclass
class ForecastStats:
    value: float
    spread: float


@dataclass
class ForecastSeriesStats:
    values: list[float]
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

    try:
        _PIPELINE = ChronosPipeline.from_pretrained(
            MODEL_ID,
            cache_dir=str(MODEL_CACHE_DIR),
            torch_dtype=dtype,
            device_map="cpu",
        )
    except Exception as exc:
        logger.exception("Khong the tai local model '%s'", MODEL_ID)
        raise ModelInferenceError(f"Không thể tải local model '{MODEL_ID}': {exc}") from exc
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

    try:
        resp = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        logger.exception("Loi goi Open-Meteo lat=%s lng=%s", lat, lng)
        raise ModelInferenceError(f"Lỗi gọi Open-Meteo: {exc}") from exc
    except ValueError as exc:
        logger.exception("Open-Meteo tra ve JSON khong hop le lat=%s lng=%s", lat, lng)
        raise ModelInferenceError(f"Open-Meteo trả về dữ liệu không hợp lệ: {exc}") from exc
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


def _forecast_series_values(values: list[float], horizon_hours: int) -> ForecastSeriesStats:
    pipeline = _get_pipeline()
    torch = _get_torch()
    context = torch.tensor(values, dtype=torch.float32)

    samples = pipeline.predict(context=context, prediction_length=horizon_hours)
    arr = _to_numpy(samples)

    if arr.ndim == 3:
        # [batch, n_samples, horizon]
        sample_matrix = arr[0, :, :horizon_hours]
        median_values = np.median(sample_matrix, axis=0)
        spread = float(np.mean(np.std(sample_matrix, axis=0)))
    elif arr.ndim == 2:
        # [n_samples, horizon]
        sample_matrix = arr[:, :horizon_hours]
        median_values = np.median(sample_matrix, axis=0)
        spread = float(np.mean(np.std(sample_matrix, axis=0)))
    elif arr.ndim == 1:
        median_values = arr[:horizon_hours]
        spread = 0.0
    else:
        raise ModelInferenceError("Định dạng output của local model không hợp lệ")

    return ForecastSeriesStats(
        values=[float(x) for x in np.asarray(median_values).tolist()],
        spread=spread,
    )


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def _bias_correct_series(raw_series: list[float], current_value: float, decay_end: float, max_step: float) -> list[float]:
    if not raw_series:
        return []

    base_bias = current_value - raw_series[0]
    corrected = []
    horizon = len(raw_series)

    for idx, value in enumerate(raw_series, start=1):
        if horizon == 1:
            decay_weight = 1.0
        else:
            ratio = (idx - 1) / float(horizon - 1)
            decay_weight = 1.0 - ratio * (1.0 - decay_end)

        adjusted = value + base_bias * decay_weight
        max_delta_from_current = max_step * idx
        adjusted = _clamp(adjusted, current_value - max_delta_from_current, current_value + max_delta_from_current)
        corrected.append(adjusted)

    return corrected


def predict_weather(lat: float, lng: float, current_weather: dict, horizon_hours: int = 3) -> dict:
    if horizon_hours < 1 or horizon_hours > 24:
        raise ValueError("horizon_hours phải nằm trong khoảng [1, 24]")

    try:
        history = _fetch_open_meteo_history(lat, lng, days=10)
        temp_stats = _forecast_series_values(history["temperature"], horizon_hours)
        humidity_stats = _forecast_series_values(history["humidity"], horizon_hours)
        wind_stats = _forecast_series_values(history["wind_speed"], horizon_hours)
    except ModelInferenceError:
        logger.exception(
            "Local model inference error lat=%s lng=%s horizon_hours=%s",
            lat,
            lng,
            horizon_hours,
        )
        raise
    except Exception as exc:
        logger.exception(
            "Unexpected local model inference error lat=%s lng=%s horizon_hours=%s",
            lat,
            lng,
            horizon_hours,
        )
        raise ModelInferenceError(f"Local model inference failed: {exc}") from exc

    current_temp = float(current_weather.get("temperature", 26.0))
    current_humidity = float(current_weather.get("humidity", 65.0))
    current_wind = float(current_weather.get("wind_speed", 3.5))

    corrected_temp_series = _bias_correct_series(temp_stats.values, current_temp, decay_end=0.45, max_step=1.6)
    corrected_humidity_series = _bias_correct_series(humidity_stats.values, current_humidity, decay_end=0.55, max_step=8.0)
    corrected_wind_series = _bias_correct_series(wind_stats.values, current_wind, decay_end=0.5, max_step=2.2)

    temperature = round(_clamp(corrected_temp_series[-1], -30.0, 55.0), 1)
    humidity = int(round(_clamp(corrected_humidity_series[-1], 10.0, 100.0), 0))
    wind_speed = round(_clamp(corrected_wind_series[-1], 0.0, 60.0), 1)

    spread_norm = _clamp((temp_stats.spread + humidity_stats.spread / 6.0 + wind_stats.spread / 3.0) / 4.2, 0.0, 1.0)
    confidence = round(_clamp(1.0 - spread_norm, 0.35, 0.97), 2)
    model_name = MODEL_ID
    source = "ai_local_chronos_openmeteo_history"

    description, weather_main, icon = _condition_from_temp(temperature)

    comfort_score = round(
        _clamp(100 - abs(temperature - 26) * 3 - abs(humidity - 65) * 0.6 - wind_speed * 1.2, 0.0, 100.0),
        1,
    )

    hourly_series = []
    for idx in range(horizon_hours):
        point_temp = round(_clamp(corrected_temp_series[idx], -30.0, 55.0), 1)
        point_humidity = int(round(_clamp(corrected_humidity_series[idx], 10.0, 100.0), 0))
        point_wind = round(_clamp(corrected_wind_series[idx], 0.0, 60.0), 1)
        point_description, _, _ = _condition_from_temp(point_temp)
        hourly_series.append(
            {
                "hour_offset": idx + 1,
                "temperature": point_temp,
                "humidity": point_humidity,
                "wind_speed": point_wind,
                "description": point_description,
            }
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
        "series": hourly_series,
    }
