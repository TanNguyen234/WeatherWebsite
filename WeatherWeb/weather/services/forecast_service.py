"""
Forecast Service - Generate mock forecast data
In production, this would connect to weather API for forecast data
"""
import random
from datetime import datetime, timedelta


def generate_mock_forecast(lat, lng, mode='hourly'):
    """
    Generate mock forecast data based on coordinates and time mode
    
    Args:
        lat: Latitude
        lng: Longitude
        mode: 'hourly' for next 24 hours, 'daily' for next 7 days
    
    Returns:
        List of forecast data points
    """
    # Base temperature influenced by latitude (rough approximation)
    base_temp = 30 - abs(lat - 15) * 0.3
    
    forecast = []
    now = datetime.now()
    
    conditions = [
        'Clear sky', 'Few clouds', 'Partly cloudy', 
        'Scattered clouds', 'Light rain', 'Overcast'
    ]
    
    if mode == 'hourly':
        # Generate 24 hourly forecasts
        for i in range(24):
            hour = now + timedelta(hours=i)
            
            # Temperature varies by time of day
            hour_of_day = hour.hour
            if 6 <= hour_of_day <= 14:
                temp_modifier = (hour_of_day - 6) * 0.5
            elif 14 < hour_of_day <= 20:
                temp_modifier = 4 - (hour_of_day - 14) * 0.6
            else:
                temp_modifier = -2
            
            temp = base_temp + temp_modifier + random.uniform(-1, 1)
            
            forecast.append({
                'time': hour.strftime('%Y-%m-%d %H:00'),
                'temperature': round(temp, 1),
                'humidity': random.randint(50, 85),
                'wind_speed': round(random.uniform(1, 5), 1),
                'description': random.choice(conditions)
            })
    
    else:  # daily
        # Generate 7 daily forecasts
        for i in range(7):
            day = now + timedelta(days=i)
            
            # Some day-to-day variation
            temp = base_temp + random.uniform(-3, 3)
            
            forecast.append({
                'time': day.strftime('%Y-%m-%d'),
                'temperature': round(temp, 1),
                'temp_min': round(temp - random.uniform(3, 5), 1),
                'temp_max': round(temp + random.uniform(2, 4), 1),
                'humidity': random.randint(55, 80),
                'wind_speed': round(random.uniform(1.5, 4.5), 1),
                'description': random.choice(conditions)
            })
    
    return forecast
