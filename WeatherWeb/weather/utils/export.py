from __future__ import annotations

import csv
from io import StringIO


EXPORT_HEADERS = [
    "time",
    "hour_offset",
    "api_temperature",
    "api_humidity",
    "api_wind_speed",
    "predicted_temperature",
    "predicted_humidity",
    "predicted_wind_speed",
]


def build_export_rows(rows: list[dict]) -> list[dict]:
    export_rows = []
    for row in rows:
        export_rows.append(
            {
                "time": row.get("timestamp"),
                "hour_offset": row.get("hour_offset"),
                "api_temperature": row.get("api_temperature"),
                "api_humidity": row.get("api_humidity"),
                "api_wind_speed": row.get("api_wind_speed"),
                "predicted_temperature": row.get("ai_temperature"),
                "predicted_humidity": row.get("ai_humidity"),
                "predicted_wind_speed": row.get("ai_wind_speed"),
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
