"""
Ezan Vakti - Ana uygulama
Windows system tray namaz vakti göstergesi
"""

import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

# Windows kontrolü
if sys.platform != "win32":
    print("Bu uygulama yalnızca Windows'ta çalışır.")
    sys.exit(1)

import pystray
from PIL import Image

import prayer_times as pt
import location as loc_module
import notifier
import tray_icon as ti
from settings import load_settings, SettingsWindow

# ─── Global durum ─────────────────────────────────────────────────────────────
_state = {
    "location":    None,
    "times":       None,
    "next_prayer": None,
    "next_name":   None,
    "next_delta":  None,
    "settings":    None,
    "tray":        None,
    "notified":    set(),   # Bu oturum bildirim gönderilenleri takip et
    "running":     True,
}

VAKIT_EMOJILERI = {
    "Fajr":    "🌙",
    "Sunrise": "🌅",
    "Dhuhr":   "☀️",
    "Asr":     "🌤️",
    "Maghrib": "🌇",
    "Isha":    "🌃",
}


# ─── Veri güncelleme ──────────────────────────────────────────────────────────

def _refresh_location():
    settings = _state["settings"]
    loc = settings.get("location") if settings else None
    if not loc:
        loc = loc_module.get_location()
    _state["location"] = loc
    return loc


def _refresh_prayer_times():
    loc = _state["location"]
    if not loc:
        return None
    times = pt.fetch_prayer_times(loc["lat"], loc["lon"])
    _state["times"] = times
    return times


def _update_next_prayer():
    times = _state["times"]
    if not times:
        return
    result = pt.get_next_prayer(times)
    if result:
        key, name, delta = result
        _state["next_prayer"] = key
        _state["next_name"]   = name
        _state["next_delta"]  = delta


# ─── Bildirim ─────────────────────────────────────────────────────────────────

def _check_notifications():
    settings = _state["settings"] or {}
    mins = settings.get("notify_before_minutes", 10)
    if mins <= 0:
        return

    times = _state["times"]
    if not times:
        return

    result = pt.get_next_prayer(times)
    if not result:
        return

    key, name, delta = result
    total_seconds = int(delta.total_seconds())
    notify_threshold = mins * 60

    # Eğer vakite X dakika kaldıysa ve bu vakti bu dakikada bildirim göndermediyse
    notify_key = f"{key}_{datetime.now().strftime('%Y-%m-%d')}"
    if total_seconds <= notify_threshold and notify_key not in _state["notified"]:
        emoji = VAKIT_EMOJILERI.get(key, "🕌")
        minutes_left = total_seconds // 60
        notifier.send_notification(
            f"{emoji} {name} Vakti Yaklaşıyor",
            f"{name} vaktine {minutes_left} dakika kaldı.",
        )
        _state["notified"].add(notify_key)


# ─── Tray menü ────────────────────────────────────────────────────────────────

def _build_menu():
    times   = _state["times"]
    loc     = _state["location"]
    settings= _state["settings"] or {}
    theme   = settings.get("theme", "dark")

    # Bugünün vakitleri
    today   = datetime.now().date().isoformat()
    today_times = (times or {}).get(today, {})

    menu_items = []

    # Konum satırı
    if loc:
        city = loc.get("city", "")
        menu_items.append(pystray.MenuItem(
            f"📍 {city}" if city else "📍 Konum ayarlı",
            None, enabled=False
        ))
    else:
        menu_items.append(pystray.MenuItem("📍 Konum belirlenmedi", None, enabled=False))

    menu_items.append(pystray.Menu.SEPARATOR)

    # Sonraki vakit
    result = pt.get_next_prayer(times) if times else None
    if result:
        key, name, delta = result
        emoji = VAKIT_EMOJILERI.get(key, "🕌")
        delta_str = pt.format_delta(delta)
        menu_items.append(pystray.MenuItem(
            f"{emoji}  Sıradaki: {name}  —  {delta_str}",
            None, enabled=False
        ))
        menu_items.append(pystray.Menu.SEPARATOR)

    # Tüm vakitler
    for vakit_key in pt.VAKIT_SIRASI:
        time_str = today_times.get(vakit_key, "—")
        name     = pt.VAKIT_ISIMLERI.get(vakit_key, vakit_key)
        emoji    = VAKIT_EMOJILERI.get(vakit_key, "")

        # Geçmiş vakitler soluk gösterilir (pystray enabled=False)
        passed = False
        if time_str != "—":
            h, m = map(int, time_str.split(":"))
            vakit_dt = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
            passed = vakit_dt < datetime.now()

        label = f"  {emoji}  {name:<10} {time_str}"
        menu_items.append(pystray.MenuItem(label, None, enabled=not passed))

    menu_items.append(pystray.Menu.SEPARATOR)

    # Ayarlar ve çıkış
    menu_items.append(pystray.MenuItem("⚙️  Ayarlar", _open_settings))
    menu_items.append(pystray.MenuItem("🔄  Vakitleri Yenile", _force_refresh))
    menu_items.append(pystray.Menu.SEPARATOR)
    menu_items.append(pystray.MenuItem("✕  Çıkış", _quit_app))

    return pystray.Menu(*menu_items)


# ─── Tray ikon güncelleme ─────────────────────────────────────────────────────

def _update_tray():
    tray = _state.get("tray")
    if not tray:
        return

    settings = _state["settings"] or {}
    theme    = settings.get("theme", "dark")
    show_sec = settings.get("show_seconds", True)

    result = pt.get_next_prayer(_state["times"]) if _state["times"] else None

    if result:
        key, name, delta = result
        emoji = VAKIT_EMOJILERI.get(key, "🕌")
        label = pt.format_delta(delta) if show_sec else pt.format_delta(delta)[:5]
        img   = ti.make_tray_icon(label, theme)
        tooltip = f"{emoji} {name} — {label}"
    else:
        img     = ti.make_tray_icon("", theme)
        tooltip = "Ezan Vakti"

    tray.icon    = img
    tray.title   = tooltip
    tray.menu    = _build_menu()


# ─── Arka plan döngüsü ────────────────────────────────────────────────────────

def _background_loop():
    last_refresh = 0
    REFRESH_INTERVAL = 3600   # vakitleri saatte bir yenile

    while _state["running"]:
        now = time.time()

        # Vakitleri yenile
        if now - last_refresh > REFRESH_INTERVAL or _state["times"] is None:
            _refresh_prayer_times()
            last_refresh = now

        _update_next_prayer()
        _check_notifications()
        _update_tray()

        time.sleep(1)


# ─── Menü eylemleri ──────────────────────────────────────────────────────────

def _open_settings():
    def on_location_change():
        _state["settings"] = load_settings()
        loc_module.LOCATION_FILE.unlink(missing_ok=True)
        _refresh_location()
        # Cache'i temizle
        pt.CACHE_FILE.unlink(missing_ok=True)
        _refresh_prayer_times()

    def run_settings():
        win = SettingsWindow(
            on_location_change=on_location_change
        )
        win.run()

    threading.Thread(target=run_settings, daemon=True).start()


def _force_refresh():
    try:
        pt.CACHE_FILE.unlink(missing_ok=True)
    except Exception:
        pass
    _refresh_location()
    _refresh_prayer_times()
    _update_tray()


def _quit_app(icon, item):
    _state["running"] = False
    icon.stop()


# ─── Başlangıç ────────────────────────────────────────────────────────────────

def main():
    # Ayarları yükle
    _state["settings"] = load_settings()
    settings = _state["settings"]
    theme    = settings.get("theme", "dark")

    # Konum
    loc = _refresh_location()
    if not loc:
        # Ayarlar penceresini aç
        print("Konum bulunamadı, ayarlar açılıyor...")
        ev = threading.Event()

        def open_initial_settings():
            win = SettingsWindow(on_close_callback=ev.set)
            win.run()

        t = threading.Thread(target=open_initial_settings, daemon=True)
        t.start()
        ev.wait(timeout=120)
        _state["settings"] = load_settings()
        _refresh_location()

    # Vakitleri çek
    _refresh_prayer_times()

    # Tray ikon
    initial_img = ti.make_loading_icon(theme)

    tray = pystray.Icon(
        "EzanVakti",
        icon=initial_img,
        title="Ezan Vakti yükleniyor...",
        menu=pystray.Menu(
            pystray.MenuItem("⚙️  Ayarlar", _open_settings),
            pystray.MenuItem("✕  Çıkış", _quit_app),
        )
    )
    _state["tray"] = tray

    # Arka plan iş parçacığı
    bg = threading.Thread(target=_background_loop, daemon=True)
    bg.start()

    print("Ezan Vakti başlatıldı. System tray'e bakın.")
    tray.run()


if __name__ == "__main__":
    main()
