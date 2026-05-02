"""
Namaz vakti çekme ve cache modülü.
Diyanet İşleri API'si (via Aladhan) kullanır.
"""

import json
import os
import requests
from datetime import datetime, date, timedelta
from pathlib import Path

CACHE_FILE = Path(__file__).parent / "data" / "prayer_cache.json"
ALADHAN_URL = "https://api.aladhan.com/v1/timingsByCity"
ALADHAN_URL_COORD = "https://api.aladhan.com/v1/timings"

VAKIT_ISIMLERI = {
    "Fajr":    "İmsak",
    "Sunrise": "Güneş",
    "Dhuhr":   "Öğle",
    "Asr":     "İkindi",
    "Maghrib": "Akşam",
    "Isha":    "Yatsı",
}

VAKIT_SIRASI = ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"]


def _load_cache():
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_cache(data: dict):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_prayer_times(lat: float, lon: float, city: str = "", country: str = "Turkey") -> dict | None:
    """
    Belirtilen koordinatlar için bugün ve yarının namaz vakitlerini çeker.
    Önce cache'e bakar, yoksa API'den alır.
    Döndürülen dict örneği:
    {
      "2024-01-15": {"Fajr": "05:42", "Sunrise": "07:12", ...},
      "2024-01-16": {...}
    }
    """
    cache = _load_cache()
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    # Her iki gün de cache'de varsa direkt döndür
    cache_key = f"{lat:.4f},{lon:.4f}"
    if cache.get("key") == cache_key and today in cache.get("days", {}) and tomorrow in cache.get("days", {}):
        return cache["days"]

    # API'den çek
    result = {}
    for target_date in [today, tomorrow]:
        dt = datetime.strptime(target_date, "%Y-%m-%d")
        timestamp = int(dt.timestamp())
        try:
            resp = requests.get(
                ALADHAN_URL_COORD,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "method": 13,       # Diyanet İşleri Başkanlığı metodu
                    "timestamp": timestamp,
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            timings = data["data"]["timings"]
            # Sadece ihtiyacımız olan vakitler
            result[target_date] = {
                k: timings[k][:5] for k in VAKIT_SIRASI if k in timings
            }
        except Exception as e:
            print(f"API hatası ({target_date}): {e}")
            return None

    # Cache'e kaydet
    _save_cache({"key": cache_key, "fetched": today, "days": result})
    return result


def get_next_prayer(times_dict: dict) -> tuple[str, str, timedelta] | None:
    """
    Şu anki zamana göre bir sonraki namaz vaktini döndürür.
    Returns: (vakit_key, vakit_adi, kalan_sure)
    """
    now = datetime.now()
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    for target_date in [today, tomorrow]:
        day_times = times_dict.get(target_date, {})
        for vakit_key in VAKIT_SIRASI:
            time_str = day_times.get(vakit_key)
            if not time_str:
                continue
            h, m = map(int, time_str.split(":"))
            target_dt = datetime.strptime(target_date, "%Y-%m-%d").replace(hour=h, minute=m, second=0)
            if target_dt > now:
                delta = target_dt - now
                return vakit_key, VAKIT_ISIMLERI.get(vakit_key, vakit_key), delta

    return None


def get_current_prayer(times_dict: dict) -> tuple[str, str] | None:
    """
    Şu an hangi vakit içindeyiz?
    Returns: (vakit_key, vakit_adi)
    """
    now = datetime.now()
    today = date.today().isoformat()

    prev_key = None
    prev_name = None

    day_times = times_dict.get(today, {})
    for vakit_key in VAKIT_SIRASI:
        time_str = day_times.get(vakit_key)
        if not time_str:
            continue
        h, m = map(int, time_str.split(":"))
        target_dt = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
        if target_dt <= now:
            prev_key = vakit_key
            prev_name = VAKIT_ISIMLERI.get(vakit_key, vakit_key)
        else:
            break

    return (prev_key, prev_name) if prev_key else None


def format_delta(delta: timedelta) -> str:
    total = int(delta.total_seconds())
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
