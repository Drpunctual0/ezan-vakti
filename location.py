"""
Konum tespiti modülü.
Önce IP tabanlı otomatik konum, sonra manuel giriş desteklenir.
"""

import json
import requests
from pathlib import Path

LOCATION_FILE = Path(__file__).parent / "data" / "location.json"


def get_location_from_ip() -> dict | None:
    """
    IP adresine göre konum tespiti yapar.
    Returns: {"lat": float, "lon": float, "city": str, "country": str}
    """
    services = [
        "https://ipapi.co/json/",
        "https://ip-api.com/json/",
    ]
    for url in services:
        try:
            resp = requests.get(url, timeout=6)
            resp.raise_for_status()
            data = resp.json()
            # Her servis farklı field ismi kullanır
            lat = data.get("latitude") or data.get("lat")
            lon = data.get("longitude") or data.get("lon")
            city = data.get("city", "")
            country = data.get("country_name") or data.get("country", "")
            if lat and lon:
                return {"lat": float(lat), "lon": float(lon), "city": city, "country": country}
        except Exception:
            continue
    return None


def save_location(location: dict):
    LOCATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCATION_FILE, "w", encoding="utf-8") as f:
        json.dump(location, f, ensure_ascii=False, indent=2)


def load_location() -> dict | None:
    try:
        if LOCATION_FILE.exists():
            with open(LOCATION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def get_location() -> dict | None:
    """
    Önce kayıtlı konumu dener, yoksa IP'den tespit eder.
    """
    saved = load_location()
    if saved and saved.get("lat") and saved.get("lon"):
        return saved
    detected = get_location_from_ip()
    if detected:
        save_location(detected)
    return detected
