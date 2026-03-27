from weather.services.prediction_service import get_prediction_comparison as _get_prediction_comparison


def get_prediction_comparison(lat: float, lng: float, horizon_hours: int = 3) -> dict:
    """Backward-compatible wrapper for legacy imports."""
    return _get_prediction_comparison(lat, lng, horizon_hours=horizon_hours)
