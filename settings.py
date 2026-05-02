"""
Ayarlar penceresi - Estetik tkinter UI
Konum ayarı, bildirim ayarı, autostart, tema seçimi
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
from pathlib import Path

import location as loc_module
import autostart as auto_module

SETTINGS_FILE = Path(__file__).parent / "data" / "settings.json"

DEFAULT_SETTINGS = {
    "notify_before_minutes": 10,
    "autostart": False,
    "theme": "dark",
    "show_seconds": True,
    "location": None,
}

# ─── Renk paleti ──────────────────────────────────────────────────────────────
DARK = {
    "bg":         "#0f1117",
    "surface":    "#1a1d2e",
    "surface2":   "#252840",
    "accent":     "#c9a84c",   # Altın / Osmanlı sarısı
    "accent2":    "#8b6914",
    "text":       "#e8e3d8",
    "text_dim":   "#7c7a72",
    "border":     "#2e3250",
    "green":      "#4caf7d",
    "red":        "#e05c5c",
}

LIGHT = {
    "bg":         "#f5f0e8",
    "surface":    "#fffdf7",
    "surface2":   "#ece8de",
    "accent":     "#8b5e1a",
    "accent2":    "#c9943a",
    "text":       "#1a1610",
    "text_dim":   "#7a7060",
    "border":     "#d4cdb8",
    "green":      "#2e7d52",
    "red":        "#c0392b",
}


def load_settings() -> dict:
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                s = json.load(f)
                return {**DEFAULT_SETTINGS, **s}
    except Exception:
        pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


class SettingsWindow:
    def __init__(self, on_close_callback=None, on_location_change=None):
        self.settings = load_settings()
        self.on_close_callback = on_close_callback
        self.on_location_change = on_location_change
        self.C = DARK if self.settings.get("theme", "dark") == "dark" else LIGHT

        self.root = tk.Tk()
        self.root.title("Ezan Vakti — Ayarlar")
        self.root.geometry("480x620")
        self.root.resizable(False, False)
        self.root.configure(bg=self.C["bg"])

        # Font
        self.font_title  = ("Georgia", 22, "bold")
        self.font_header = ("Georgia", 12, "bold")
        self.font_body   = ("Segoe UI", 10)
        self.font_small  = ("Segoe UI", 9)
        self.font_arabic = ("Traditional Arabic", 18)

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        C = self.C

        # Başlık
        header = tk.Frame(self.root, bg=C["surface"], pady=20)
        header.pack(fill="x")

        tk.Label(header, text="☽", font=("Segoe UI Symbol", 28),
                 bg=C["surface"], fg=C["accent"]).pack()
        tk.Label(header, text="Ezan Vakti", font=self.font_title,
                 bg=C["surface"], fg=C["text"]).pack()
        tk.Label(header, text="Namaz Vakti Göstergesi Ayarları",
                 font=self.font_small, bg=C["surface"], fg=C["text_dim"]).pack()

        # Ayırıcı
        tk.Frame(self.root, height=1, bg=C["border"]).pack(fill="x")

        # Scrollable area
        canvas = tk.Canvas(self.root, bg=C["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=C["bg"])

        self.scroll_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=0)
        scrollbar.pack(side="right", fill="y")

        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        f = self.scroll_frame
        pad = {"padx": 28, "pady": 0}

        self._section(f, "📍 Konum")
        self._build_location_section(f, pad)

        self._spacer(f)
        self._section(f, "🔔 Bildirim")
        self._build_notification_section(f, pad)

        self._spacer(f)
        self._section(f, "⚙️ Genel")
        self._build_general_section(f, pad)

        self._spacer(f)
        self._section(f, "🎨 Görünüm")
        self._build_theme_section(f, pad)

        self._spacer(f, 20)
        self._build_save_button(f)
        self._spacer(f, 16)

    def _section(self, parent, title):
        C = self.C
        frame = tk.Frame(parent, bg=self.C["bg"])
        frame.pack(fill="x", padx=28, pady=(18, 6))
        tk.Label(frame, text=title, font=self.font_header,
                 bg=C["bg"], fg=C["accent"]).pack(side="left")
        tk.Frame(frame, height=1, bg=C["border"]).pack(
            side="left", fill="x", expand=True, padx=(10, 0), pady=6)

    def _spacer(self, parent, h=8):
        tk.Frame(parent, height=h, bg=self.C["bg"]).pack()

    def _card(self, parent):
        C = self.C
        f = tk.Frame(parent, bg=C["surface"], bd=0, relief="flat",
                     highlightthickness=1, highlightbackground=C["border"])
        f.pack(fill="x", padx=28, pady=4)
        return f

    # ─── Konum ────────────────────────────────────────────────────────────────

    def _build_location_section(self, parent, pad):
        C = self.C
        card = self._card(parent)

        self.loc_status_var = tk.StringVar()
        saved = self.settings.get("location")
        if saved:
            city = saved.get("city", "")
            lat  = saved.get("lat", 0)
            lon  = saved.get("lon", 0)
            self.loc_status_var.set(f"✓  {city}  ({lat:.3f}, {lon:.3f})")
        else:
            self.loc_status_var.set("Konum belirlenmedi")

        inner = tk.Frame(card, bg=C["surface"], padx=16, pady=12)
        inner.pack(fill="x")

        tk.Label(inner, textvariable=self.loc_status_var,
                 font=self.font_body, bg=C["surface"], fg=C["text"],
                 wraplength=360, justify="left").pack(anchor="w")

        btn_frame = tk.Frame(inner, bg=C["surface"])
        btn_frame.pack(anchor="w", pady=(10, 0))

        self._btn(btn_frame, "📡  Otomatik Tespit", self._auto_detect).pack(side="left", padx=(0, 8))
        self._btn(btn_frame, "✏️  Manuel Gir", self._manual_location).pack(side="left")

    def _auto_detect(self):
        self.loc_status_var.set("⏳ Tespit ediliyor...")
        self.root.update()

        def detect():
            result = loc_module.get_location_from_ip()
            if result:
                self.settings["location"] = result
                loc_module.save_location(result)
                city = result.get("city", "")
                lat  = result.get("lat", 0)
                lon  = result.get("lon", 0)
                self.loc_status_var.set(f"✓  {city}  ({lat:.3f}, {lon:.3f})")
            else:
                self.loc_status_var.set("❌ Tespit başarısız, lütfen manuel girin")

        threading.Thread(target=detect, daemon=True).start()

    def _manual_location(self):
        C = self.C
        win = tk.Toplevel(self.root)
        win.title("Manuel Konum")
        win.geometry("360x280")
        win.configure(bg=C["bg"])
        win.grab_set()

        tk.Label(win, text="Manuel Konum Girişi", font=self.font_header,
                 bg=C["bg"], fg=C["accent"]).pack(pady=(20, 4))
        tk.Label(win, text="Şehir adı veya koordinat girebilirsiniz",
                 font=self.font_small, bg=C["bg"], fg=C["text_dim"]).pack()

        fields_frame = tk.Frame(win, bg=C["bg"], pady=16)
        fields_frame.pack(fill="x", padx=30)

        def lbl_entry(label, default=""):
            tk.Label(fields_frame, text=label, font=self.font_small,
                     bg=C["bg"], fg=C["text_dim"]).pack(anchor="w", pady=(8,1))
            e = tk.Entry(fields_frame, font=self.font_body,
                         bg=C["surface2"], fg=C["text"],
                         insertbackground=C["accent"],
                         relief="flat", bd=6)
            e.insert(0, default)
            e.pack(fill="x", ipady=4)
            return e

        saved = self.settings.get("location") or {}
        e_city    = lbl_entry("Şehir", saved.get("city", ""))
        e_country = lbl_entry("Ülke", saved.get("country", "Turkey"))
        e_lat     = lbl_entry("Enlem (opsiyonel)", str(saved.get("lat", "")))
        e_lon     = lbl_entry("Boylam (opsiyonel)", str(saved.get("lon", "")))

        def save_manual():
            city    = e_city.get().strip()
            country = e_country.get().strip()
            lat_s   = e_lat.get().strip()
            lon_s   = e_lon.get().strip()

            if lat_s and lon_s:
                try:
                    lat = float(lat_s)
                    lon = float(lon_s)
                except ValueError:
                    messagebox.showerror("Hata", "Geçersiz koordinat")
                    return
                new_loc = {"lat": lat, "lon": lon, "city": city, "country": country}
            elif city:
                # Geocoding via API
                try:
                    resp = __import__("requests").get(
                        "https://nominatim.openstreetmap.org/search",
                        params={"q": f"{city},{country}", "format": "json", "limit": 1},
                        headers={"User-Agent": "EzanVaktiApp/1.0"},
                        timeout=8
                    )
                    data = resp.json()
                    if data:
                        lat = float(data[0]["lat"])
                        lon = float(data[0]["lon"])
                        new_loc = {"lat": lat, "lon": lon, "city": city, "country": country}
                    else:
                        messagebox.showerror("Hata", "Şehir bulunamadı")
                        return
                except Exception as ex:
                    messagebox.showerror("Hata", f"Geocoding başarısız: {ex}")
                    return
            else:
                messagebox.showwarning("Uyarı", "Şehir adı veya koordinat giriniz")
                return

            self.settings["location"] = new_loc
            loc_module.save_location(new_loc)
            self.loc_status_var.set(f"✓  {new_loc['city']}  ({new_loc['lat']:.3f}, {new_loc['lon']:.3f})")
            win.destroy()

        self._btn(win, "Kaydet", save_manual).pack(pady=12)

    # ─── Bildirim ─────────────────────────────────────────────────────────────

    def _build_notification_section(self, parent, pad):
        C = self.C
        card = self._card(parent)
        inner = tk.Frame(card, bg=C["surface"], padx=16, pady=12)
        inner.pack(fill="x")

        self.notify_var = tk.BooleanVar(value=self.settings.get("notify_before_minutes", 10) > 0)
        self.notify_mins_var = tk.IntVar(value=self.settings.get("notify_before_minutes", 10))

        row = tk.Frame(inner, bg=C["surface"])
        row.pack(fill="x", pady=(0, 8))

        self._toggle(row, "Vakitten önce bildirim gönder", self.notify_var).pack(side="left")

        mins_frame = tk.Frame(inner, bg=C["surface"])
        mins_frame.pack(fill="x")

        tk.Label(mins_frame, text="Kaç dakika önce:  ",
                 font=self.font_body, bg=C["surface"], fg=C["text"]).pack(side="left")

        for m in [10, 20, 30, 45, 60]:
            tk.Radiobutton(
                mins_frame, text=str(m), variable=self.notify_mins_var, value=m,
                font=self.font_small,
                bg=C["surface"], fg=C["text"],
                selectcolor=C["surface2"],
                activebackground=C["surface"],
                highlightthickness=0,
            ).pack(side="left", padx=4)

    # ─── Genel ────────────────────────────────────────────────────────────────

    def _build_general_section(self, parent, pad):
        C = self.C
        card = self._card(parent)
        inner = tk.Frame(card, bg=C["surface"], padx=16, pady=12)
        inner.pack(fill="x")

        self.autostart_var = tk.BooleanVar(value=auto_module.is_autostart_enabled())
        self.seconds_var   = tk.BooleanVar(value=self.settings.get("show_seconds", True))

        self._toggle(inner, "Windows başlangıcında otomatik başlat",
                     self.autostart_var).pack(anchor="w", pady=3)
        self._toggle(inner, "Kalan sürede saniyeyi göster",
                     self.seconds_var).pack(anchor="w", pady=3)

    # ─── Tema ─────────────────────────────────────────────────────────────────

    def _build_theme_section(self, parent, pad):
        C = self.C
        card = self._card(parent)
        inner = tk.Frame(card, bg=C["surface"], padx=16, pady=12)
        inner.pack(fill="x")

        self.theme_var = tk.StringVar(value=self.settings.get("theme", "dark"))
        tk.Label(inner, text="Uygulama teması:",
                 font=self.font_body, bg=C["surface"], fg=C["text"]).pack(anchor="w", pady=(0, 6))

        themes = [("🌙  Gece (Koyu)", "dark"), ("☀️  Gündüz (Açık)", "light")]
        for label, val in themes:
            tk.Radiobutton(
                inner, text=label, variable=self.theme_var, value=val,
                font=self.font_body, bg=C["surface"], fg=C["text"],
                selectcolor=C["surface2"], activebackground=C["surface"],
                highlightthickness=0,
            ).pack(anchor="w", pady=2)

    # ─── Widgets ──────────────────────────────────────────────────────────────

    def _btn(self, parent, text, command):
        C = self.C
        return tk.Button(
            parent, text=text, command=command,
            font=self.font_body,
            bg=C["accent"], fg=C["bg"],
            activebackground=C["accent2"], activeforeground=C["bg"],
            relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
        )

    def _toggle(self, parent, text, var):
        C = self.C
        return tk.Checkbutton(
            parent, text=text, variable=var,
            font=self.font_body,
            bg=C["surface"] if parent.cget("bg") == C["surface"] else C["bg"],
            fg=C["text"],
            selectcolor=C["surface2"],
            activebackground=C["surface"],
            highlightthickness=0,
            cursor="hand2",
        )

    def _build_save_button(self, parent):
        C = self.C
        frame = tk.Frame(parent, bg=C["bg"])
        frame.pack(fill="x", padx=28)

        save_btn = tk.Button(
            frame, text="✓  Kaydet & Uygula",
            command=self._save,
            font=("Segoe UI", 11, "bold"),
            bg=C["accent"], fg=C["bg"],
            activebackground=C["accent2"], activeforeground=C["bg"],
            relief="flat", bd=0, pady=10, cursor="hand2",
        )
        save_btn.pack(fill="x")

    # ─── Save ─────────────────────────────────────────────────────────────────

    def _save(self):
        self.settings["notify_before_minutes"] = self.notify_mins_var.get() if self.notify_var.get() else 0
        self.settings["autostart"]   = self.autostart_var.get()
        self.settings["show_seconds"]= self.seconds_var.get()
        self.settings["theme"]       = self.theme_var.get()

        save_settings(self.settings)

        if self.autostart_var.get():
            auto_module.enable_autostart()
        else:
            auto_module.disable_autostart()

        if self.on_location_change:
            self.on_location_change()

        messagebox.showinfo("Kaydedildi", "Ayarlar başarıyla kaydedildi.")
        self._on_close()

    def _on_close(self):
        if self.on_close_callback:
            self.on_close_callback()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    SettingsWindow().run()
