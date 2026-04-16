from __future__ import annotations

import csv
from io import StringIO


EXPORT_HEADERS = [
    "Thời gian",
    "Giờ dự báo",
    "Nhiệt độ API (°C)",
    "Độ ẩm API (%)",
    "Tốc độ gió API (m/s)",
    "Nhiệt độ dự đoán (°C)",
    "Độ ẩm dự đoán (%)",
    "Tốc độ gió dự đoán (m/s)",
]


def build_export_rows(rows: list[dict]) -> list[dict]:
    export_rows = []
    for row in rows:
        export_rows.append(
            {
                "Thời gian":                   row.get("timestamp"),
                "Giờ dự báo":                  row.get("hour_offset"),
                "Nhiệt độ API (°C)":           row.get("api_temperature"),
                "Độ ẩm API (%)":               row.get("api_humidity"),
                "Tốc độ gió API (m/s)":        row.get("api_wind_speed"),
                "Nhiệt độ dự đoán (°C)":       row.get("ai_temperature"),
                "Độ ẩm dự đoán (%)":           row.get("ai_humidity"),
                "Tốc độ gió dự đoán (m/s)":   row.get("ai_wind_speed"),
            }
        )
    return export_rows


def generate_prediction_csv(rows: list[dict]) -> bytes:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=EXPORT_HEADERS)
    writer.writeheader()
    for row in build_export_rows(rows):
        writer.writerow(row)
    return output.getvalue().encode("utf-8-sig")
