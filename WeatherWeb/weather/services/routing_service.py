"""
Routing service for road geometry retrieval and route point sampling.
All routing logic is centralized here so views stay thin.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

import requests

from weather.services.gis_utils import validate_coordinates

OSRM_BASE_URL = "https://router.project-osrm.org/route/v1/driving"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "WeatherGIS/1.0 (route-analysis)"


@dataclass
class RoutingServiceError(Exception):
    message: str
    status_code: int = 502

    def __str__(self) -> str:
        return self.message


COUNTRY_BBOX = {
    "VN": (8.18, 102.14, 23.40, 109.47),
    "TH": (5.63, 97.34, 20.46, 105.64),
    "KH": (10.49, 102.33, 14.68, 107.63),
    "LA": (13.91, 100.12, 22.50, 107.64),
    "MM": (9.78, 92.18, 28.55, 101.17),
    "CN": (18.16, 73.56, 53.56, 134.77),
    "MY": (0.85, 99.64, 7.36, 119.27),
    "ID": (-11.01, 94.97, 6.08, 141.02),
    "PH": (4.64, 116.93, 21.12, 126.60),
    "JP": (24.04, 122.93, 45.52, 153.99),
    "KR": (33.11, 124.61, 38.61, 130.92),
    "IN": (6.75, 68.11, 35.67, 97.40),
    "US": (18.91, -171.79, 71.36, -66.94),
    "DE": (47.27, 5.87, 55.06, 15.04),
    "FR": (41.33, -5.14, 51.09, 9.56),
    "GB": (49.96, -8.62, 60.84, 1.77),
}


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_m * c


def _reverse_country_code(lat: float, lng: float) -> str | None:
    try:
        response = requests.get(
            NOMINATIM_REVERSE_URL,
            params={
                "lat": lat,
                "lon": lng,
                "format": "json",
                "zoom": 3,
                "addressdetails": 1,
            },
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "en",
            },
            timeout=6,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("address", {}).get("country_code", "").upper() or None
    except Exception:
        return None


def _geometry_exits_country(coordinates: list[list[float]], country_code: str) -> bool:
    bbox = COUNTRY_BBOX.get(country_code)
    if not bbox:
        return False

    min_lat, min_lng, max_lat, max_lng = bbox
    for lon, lat in coordinates:
        if not (min_lat <= lat <= max_lat and min_lng <= lon <= max_lng):
            return True
    return False


def _compute_intermediate_count(slat: float, slng: float, elat: float, elng: float) -> int:
    distance_km = _haversine_m(slat, slng, elat, elng) / 1000.0
    if distance_km <= 80:
        return 2
    if distance_km <= 250:
        return 4
    if distance_km <= 500:
        return 6
    return 8


def _build_waypoint_coords(slat: float, slng: float, elat: float, elng: float, n_intermediate: int) -> str:
    points: list[tuple[float, float]] = [(slng, slat)]
    for i in range(1, n_intermediate + 1):
        frac = i / (n_intermediate + 1)
        points.append((
            slng + frac * (elng - slng),
            slat + frac * (elat - slat),
        ))
    points.append((elng, elat))

    return ";".join(f"{lng:.6f},{lat:.6f}" for lng, lat in points)


def _call_osrm(coords_str: str, timeout: int = 15, retries: int = 2) -> dict:
    osrm_url = (
        f"{OSRM_BASE_URL}/{coords_str}"
        f"?overview=full&geometries=geojson&steps=false"
    )

    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = requests.get(
                osrm_url,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") != "Ok" or not payload.get("routes"):
                raise RoutingServiceError(
                    "Khong tim thay duong di giua hai diem da chon",
                    status_code=404,
                )
            return payload["routes"][0]
        except RoutingServiceError:
            raise
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(0.5 * (2 ** attempt))
                continue

    raise RoutingServiceError(f"Khong the lay duong di tu OSRM: {last_exc}", status_code=502)


def get_route_geometry(slat: float, slng: float, elat: float, elng: float) -> dict:
    validate_coordinates(slat, slng)
    validate_coordinates(elat, elng)

    start_country = _reverse_country_code(slat, slng)
    end_country = _reverse_country_code(elat, elng)
    same_country = bool(start_country and end_country and start_country == end_country)

    if same_country:
        intermediate = _compute_intermediate_count(slat, slng, elat, elng)
        coords_str = _build_waypoint_coords(slat, slng, elat, elng, intermediate)
    else:
        coords_str = f"{slng:.6f},{slat:.6f};{elng:.6f},{elat:.6f}"

    route = _call_osrm(coords_str)
    geometry_coords = route["geometry"]["coordinates"]

    if same_country and _geometry_exits_country(geometry_coords, start_country):
        dense_intermediate = min(_compute_intermediate_count(slat, slng, elat, elng) + 4, 16)
        dense_coords = _build_waypoint_coords(slat, slng, elat, elng, dense_intermediate)
        dense_route = _call_osrm(dense_coords)
        dense_coords_list = dense_route["geometry"]["coordinates"]
        if _geometry_exits_country(dense_coords_list, start_country):
            raise RoutingServiceError(
                (
                    "Khong tim duoc duong di hoan toan trong lanh tho giua hai diem nay. "
                    "Thu chon diem gan hon hoac nam tren truc duong chinh trong nuoc."
                ),
                status_code=422,
            )
        route = dense_route

    return {
        "geometry": route["geometry"],
        "distance": route["distance"],
        "duration": route["duration"],
        "country": start_country if same_country else None,
        "cross_border": False,
    }


def sample_line_string_by_distance(coordinates: list[list[float]], sample_count: int) -> list[dict]:
    if not coordinates:
        raise RoutingServiceError("Tuyen duong khong co du lieu hinh hoc", status_code=422)

    sample_count = max(2, min(20, int(sample_count)))

    if len(coordinates) == 1:
        lon, lat = coordinates[0]
        return [
            {"index": idx, "latitude": lat, "longitude": lon}
            for idx in range(sample_count)
        ]

    cumulative = [0.0]
    total = 0.0
    for i in range(1, len(coordinates)):
        prev_lon, prev_lat = coordinates[i - 1]
        cur_lon, cur_lat = coordinates[i]
        segment = _haversine_m(prev_lat, prev_lon, cur_lat, cur_lon)
        total += segment
        cumulative.append(total)

    if total <= 0:
        lon, lat = coordinates[0]
        return [
            {"index": idx, "latitude": lat, "longitude": lon}
            for idx in range(sample_count)
        ]

    points = []
    segment_idx = 1
    for idx in range(sample_count):
        target = (idx / (sample_count - 1)) * total

        while segment_idx < len(cumulative) and cumulative[segment_idx] < target:
            segment_idx += 1

        if segment_idx >= len(cumulative):
            lon, lat = coordinates[-1]
            points.append({"index": idx, "latitude": lat, "longitude": lon})
            continue

        prev_total = cumulative[segment_idx - 1]
        next_total = cumulative[segment_idx]
        denom = max(next_total - prev_total, 1e-9)
        ratio = (target - prev_total) / denom

        start_lon, start_lat = coordinates[segment_idx - 1]
        end_lon, end_lat = coordinates[segment_idx]
        lon = start_lon + (end_lon - start_lon) * ratio
        lat = start_lat + (end_lat - start_lat) * ratio
        points.append({"index": idx, "latitude": lat, "longitude": lon})

    return points
