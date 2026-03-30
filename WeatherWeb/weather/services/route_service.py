"""
Route service - route weather analysis on road geometry.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from weather.services.routing_service import get_route_geometry, sample_line_string_by_distance
from weather.services.weather_service import get_current_weather


WEATHER_KEYS = {
    "temperature": None,
    "feels_like": None,
    "temp_min": None,
    "temp_max": None,
    "humidity": None,
    "pressure": None,
    "wind_speed": None,
    "wind_deg": None,
    "visibility": None,
    "description": None,
    "weather_main": None,
    "icon": None,
    "clouds": None,
    "rain_1h": None,
    "source": None,
}


def _normalize_weather(weather: dict | None) -> dict | None:
    if weather is None:
        return None
    normalized = dict(WEATHER_KEYS)
    normalized.update(weather)
    return normalized


def _severity_score(weather: dict | None) -> float:
    if not weather:
        return 0.0

    rain = float(weather.get("rain_1h") or 0.0)
    wind = float(weather.get("wind_speed") or 0.0)
    humidity = float(weather.get("humidity") or 0.0)
    main = str(weather.get("weather_main") or "").lower()

    score = rain * 6.0 + max(0.0, wind - 8.0) * 1.6 + max(0.0, humidity - 85.0) * 0.2
    if main in {"thunderstorm", "snow"}:
        score += 6.0
    elif main in {"rain", "drizzle"}:
        score += 3.5
    elif main == "clouds":
        score += 1.0
    return round(score, 2)


def _segment_weather(start: dict, end: dict) -> dict:
    start_weather = start.get("weather")
    end_weather = end.get("weather")
    if not start_weather and not end_weather:
        return {
            "temperature": None,
            "humidity": None,
            "wind_speed": None,
            "rain_1h": None,
            "severity_score": 0.0,
            "status": "missing",
        }

    def avg(field: str):
        values = []
        for weather in (start_weather, end_weather):
            if weather and weather.get(field) is not None:
                values.append(float(weather[field]))
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    segment_payload = {
        "temperature": avg("temperature"),
        "humidity": avg("humidity"),
        "wind_speed": avg("wind_speed"),
        "rain_1h": avg("rain_1h"),
        "severity_score": max(_severity_score(start_weather), _severity_score(end_weather)),
        "status": "ok" if start_weather and end_weather else "partial",
    }
    return segment_payload


def _fetch_point_weather(point: dict, generated_at: str) -> dict:
    lat = float(point["latitude"])
    lng = float(point["longitude"])
    point_index = int(point["index"])

    try:
        weather = _normalize_weather(get_current_weather(lat, lng))
        return {
            "index": point_index,
            "latitude": lat,
            "longitude": lng,
            "timestamp": generated_at,
            "weather": weather,
            "source": weather.get("source") if weather else None,
            "status": "ok",
            "error": None,
        }
    except Exception as exc:
        return {
            "index": point_index,
            "latitude": lat,
            "longitude": lng,
            "timestamp": generated_at,
            "weather": None,
            "source": None,
            "status": "failed",
            "error": str(exc),
        }


def analyze_route_weather(start_location, end_location, point_count=5, max_workers=4) -> dict:
    if int(start_location.id) == int(end_location.id):
        raise ValueError("Diem xuat phat va diem dich phai khac nhau")

    bounded_points = max(2, min(20, int(point_count)))
    geometry_payload = get_route_geometry(
        float(start_location.latitude),
        float(start_location.longitude),
        float(end_location.latitude),
        float(end_location.longitude),
    )

    coordinates = geometry_payload["geometry"]["coordinates"]
    sampled_points = sample_line_string_by_distance(coordinates, bounded_points)
    generated_at = datetime.now(timezone.utc).isoformat()

    route_points = [None] * len(sampled_points)
    workers = max(1, min(int(max_workers), len(sampled_points)))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {
            pool.submit(_fetch_point_weather, point, generated_at): int(point["index"])
            for point in sampled_points
        }
        for future in as_completed(future_map):
            idx = future_map[future]
            route_points[idx] = future.result()

    segments = []
    for i in range(1, len(route_points)):
        start = route_points[i - 1]
        end = route_points[i]
        segment_payload = _segment_weather(start, end)
        segments.append(
            {
                "index": i - 1,
                "start_index": i - 1,
                "end_index": i,
                "start": {"latitude": start["latitude"], "longitude": start["longitude"]},
                "end": {"latitude": end["latitude"], "longitude": end["longitude"]},
                "weather": segment_payload,
            }
        )

    success_points = [point for point in route_points if point["status"] == "ok" and point["weather"]]
    failed_count = len(route_points) - len(success_points)

    def average(field: str):
        values = [float(point["weather"].get(field)) for point in success_points if point["weather"].get(field) is not None]
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    source_breakdown = {}
    for point in success_points:
        source = point.get("source") or "unknown"
        source_breakdown[source] = source_breakdown.get(source, 0) + 1

    worst_segment = None
    if segments:
        worst_segment = max(segments, key=lambda seg: float(seg["weather"]["severity_score"]))

    return {
        "geometry": geometry_payload["geometry"],
        "distance": geometry_payload["distance"],
        "duration": geometry_payload["duration"],
        "country": geometry_payload.get("country"),
        "cross_border": geometry_payload.get("cross_border", False),
        "route_points": route_points,
        "segments": segments,
        "summary": {
            "total_points": len(route_points),
            "successful_points": len(success_points),
            "failed_points": failed_count,
            "average_temperature": average("temperature"),
            "average_humidity": average("humidity"),
            "average_wind_speed": average("wind_speed"),
            "average_rain_1h": average("rain_1h"),
            "worst_segment": worst_segment,
        },
        "metadata": {
            "generated_at": generated_at,
            "source_breakdown": source_breakdown,
            "sample_count": bounded_points,
        },
    }


def generate_route_weather(start_location, end_location, point_count=5):
    """
    Backward-compatible wrapper returning only route points.
    """
    return analyze_route_weather(start_location, end_location, point_count)["route_points"]
