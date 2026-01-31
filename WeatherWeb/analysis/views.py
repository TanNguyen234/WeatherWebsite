from django.shortcuts import render
from django.views import View
from django.conf import settings
import json
import requests

# Danh sách địa điểm gợi ý (lat, lon) — dùng khi không có API key hoặc user chọn nhanh
LOCATIONS = {
    "hanoi": {"name": "Hà Nội", "lat": 21.0285, "lon": 105.8542},
    "danang": {"name": "Đà Nẵng", "lat": 16.0544, "lon": 108.2022},
    "hcm": {"name": "TP.HCM", "lat": 10.7769, "lon": 106.7009},
    "hue": {"name": "Huế", "lat": 16.4637, "lon": 107.5909},
    "nhatrang": {"name": "Nha Trang", "lat": 12.2388, "lon": 109.1967},
}


def _get_api_key():
    return getattr(settings, "OPENWEATHER_API_KEY", None) or ""


def _parse_coords(s):
    """Parse 'lat,lon' string -> (lat, lon) or None."""
    if not s or "," not in s:
        return None
    try:
        parts = s.strip().split(",", 1)
        return (float(parts[0].strip()), float(parts[1].strip()))
    except (ValueError, IndexError):
        return None


def _geocode_openweather(place_name, api_key):
    """Geocode tên địa điểm qua OpenWeather Geocoding API -> (lat, lon, display_name)."""
    if not api_key or not (place_name and place_name.strip()):
        return None
    q = place_name.strip()
    url = "https://api.openweathermap.org/geo/1.0/direct"
    params = {"q": q, "limit": 1, "appid": api_key}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data and isinstance(data, list) and len(data) > 0:
            item = data[0]
            lat = item.get("lat")
            lon = item.get("lon")
            name = item.get("name") or q
            if lat is not None and lon is not None:
                return (float(lat), float(lon), name)
    except Exception:
        pass
    return None


def _weather_openweather(lat, lon, api_key):
    """Lấy thời tiết hiện tại từ OpenWeather API (theo lat, lon)."""
    if not api_key:
        return None
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric", "lang": "vi"}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        temp = data.get("main", {}).get("temp")
        humidity = data.get("main", {}).get("humidity")
        desc_list = data.get("weather", [])
        description = desc_list[0].get("description", "—") if desc_list else "—"
        return {
            "temp": round(float(temp), 1) if temp is not None else None,
            "humidity": int(humidity) if humidity is not None else None,
            "description": description,
        }
    except Exception:
        return None


def _mock_weather(name, lat, lon):
    """Dữ liệu thời tiết mẫu (khi không có API hoặc lỗi)."""
    base_temp = 32 - (lat - 10) * 0.15
    humidity = 70 + int(lat) % 20
    desc = "Nắng" if (int(lat * 10) % 3) == 0 else "Mây" if (int(lat * 10) % 3) == 1 else "Mưa nhẹ"
    return {
        "name": name,
        "lat": lat,
        "lon": lon,
        "temp": round(base_temp, 1),
        "humidity": min(99, humidity),
        "description": desc,
    }


def _resolve_place_to_coords(place_input, api_key):
    """
    place_input: tên địa điểm (text) hoặc id preset (hanoi, danang,...) hoặc 'lat,lon'.
    Trả về (lat, lon, display_name) hoặc None.
    """
    if not place_input or not place_input.strip():
        return None
    s = place_input.strip()
    # Tọa độ trực tiếp
    coords = _parse_coords(s)
    if coords:
        lat, lon = coords
        return (lat, lon, f"({lat:.2f}, {lon:.2f})")
    # Preset
    loc = LOCATIONS.get(s.lower())
    if loc:
        return (loc["lat"], loc["lon"], loc["name"])
    # Geocode qua OpenWeather
    geo = _geocode_openweather(s, api_key)
    if geo:
        return geo
    return None


def _get_weather_for_place(name, lat, lon, api_key):
    """Trả về dict thời tiết (name, lat, lon, temp, humidity, description)."""
    out = {"name": name, "lat": lat, "lon": lon, "temp": None, "humidity": None, "description": "—"}
    w = _weather_openweather(lat, lon, api_key)
    if w:
        out["temp"] = w.get("temp")
        out["humidity"] = w.get("humidity")
        out["description"] = w.get("description") or "—"
    if out["temp"] is None:
        mock = _mock_weather(name, lat, lon)
        out["temp"] = mock["temp"]
        out["humidity"] = mock["humidity"]
        out["description"] = mock["description"]
    return out


def _interpolate_line(lat1, lon1, lat2, lon2, n_points):
    """Chia tuyến A→B thành n_points điểm (đường thẳng)."""
    if n_points < 2:
        return [(lat1, lon1), (lat2, lon2)]
    points = []
    for i in range(n_points):
        t = i / (n_points - 1) if n_points > 1 else 1
        lat = lat1 + (lat2 - lat1) * t
        lon = lon1 + (lon2 - lon1) * t
        points.append((lat, lon))
    return points


def _locations_list():
    return [{"id": k, "name": v["name"], "lat": v["lat"], "lon": v["lon"]} for k, v in LOCATIONS.items()]


def _locations_json():
    return json.dumps(_locations_list())


def _empty_compare_context():
    return {
        "weather_data": [],
        "weather_data_json": "[]",
        "locations_list": _locations_list(),
        "openweather_configured": bool(_get_api_key()),
    }


class CompareView(View):
    """So sánh 2–3 điểm: nhập tên địa điểm hoặc chọn gợi ý → OpenWeather (hoặc mock)."""

    def get(self, request):
        return render(request, "analysis/compare.html", _empty_compare_context())

    def post(self, request):
        api_key = _get_api_key()
        # Ưu tiên: place1, place2, place3 (text). Nếu không có thì dùng locations (multiselect).
        places = []
        for key in ("place1", "place2", "place3"):
            v = (request.POST.get(key) or "").strip()
            if v:
                places.append(v)
        if not places:
            selected = request.POST.getlist("locations")[:3]
            for item in selected:
                item = item.strip()
                if item:
                    places.append(item)

        weather_data = []
        for place_input in places[:3]:
            resolved = _resolve_place_to_coords(place_input, api_key)
            if not resolved:
                weather_data.append({
                    "name": place_input or "?",
                    "lat": 0,
                    "lon": 0,
                    "temp": "—",
                    "humidity": "—",
                    "description": "Không tìm thấy địa điểm",
                })
                continue
            lat, lon, name = resolved
            weather_data.append(_get_weather_for_place(name, lat, lon, api_key))

        return render(request, "analysis/compare.html", {
            "weather_data": weather_data,
            "weather_data_json": json.dumps(weather_data),
            "locations_list": _locations_list(),
            "openweather_configured": bool(api_key),
        })


def _empty_route_context():
    return {
        "route_weather": [],
        "route_points": [],
        "route_points_json": "[]",
        "locations_list": _locations_list(),
        "openweather_configured": bool(_get_api_key()),
    }


class RouteView(View):
    """Tuyến A→B: nhập tên địa điểm hoặc chọn gợi ý → chia N điểm → OpenWeather (hoặc mock)."""

    def get(self, request):
        return render(request, "analysis/route.html", _empty_route_context())

    def post(self, request):
        api_key = _get_api_key()
        start_input = (request.POST.get("start_place") or request.POST.get("start") or "").strip()
        end_input = (request.POST.get("end_place") or request.POST.get("end") or "").strip()
        n_points = max(3, min(20, int(request.POST.get("n_points", 5) or 5)))

        start_coords = _resolve_place_to_coords(start_input, api_key) if start_input else None
        end_coords = _resolve_place_to_coords(end_input, api_key) if end_input else None

        route_weather = []
        route_points = []

        if start_coords and end_coords:
            lat1, lon1, name_a = start_coords
            lat2, lon2, name_b = end_coords
            points = _interpolate_line(lat1, lon1, lat2, lon2, n_points)
            route_points = [{"lat": p[0], "lon": p[1]} for p in points]
            for i, (lat, lon) in enumerate(points):
                label = name_a if i == 0 else name_b if i == len(points) - 1 else f"Điểm {i + 1}"
                route_weather.append(_get_weather_for_place(label, lat, lon, api_key))

        ctx = _empty_route_context()
        ctx["route_weather"] = route_weather
        ctx["route_points"] = route_points
        ctx["route_points_json"] = json.dumps(route_points)
        return render(request, "analysis/route.html", ctx)
