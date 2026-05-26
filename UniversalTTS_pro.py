#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UNIVERSAL TTS PRO - v1.3.1 (PORTABLE EDITION)
TELJES FÜGGŐSÉGKEZELŐ + HORDOZHATÓ / PENDRIVE TÁMOGATÁS
Soli Deo Gloria

ÚJDONSÁGOK v1.3.1:
  - Indításkor automatikus függőség-ellenőrzés
  - Hiányzó csomagok automatikus telepítési javaslata
  - opusenc.exe automatikus letöltése
  - Modell letöltési útmutató beépítve
  - PyInstaller kompatibilis hordozható mód
  - Pendrive / offline használat: minden komponens helyi
"""

import sys
import os
import json
import threading
import time
import re
import subprocess
import tempfile
import glob
import queue
import wave
import urllib.request
import urllib.error
import zipfile
import io
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from datetime import datetime

# ════════════════════════════════════════════════════════════════════════════
#  GRACEFUL IMPORTS — minden csomag opcionálisan töltődik be
# ════════════════════════════════════════════════════════════════════════════

try:
    import sherpa_onnx
    SHERPA_OK = True
except ImportError:
    SHERPA_OK = False
    sherpa_onnx = None

try:
    import sounddevice as sd
    SD_OK = True
except ImportError:
    SD_OK = False
    sd = None

try:
    import numpy as np
    NUMPY_OK = True
except ImportError:
    NUMPY_OK = False
    np = None

try:
    from supertonic import TTS as SupertonicTTS
    SUPERTONIC_PKG_OK = True
except ImportError:
    SUPERTONIC_PKG_OK = False
    SupertonicTTS = None

# ════════════════════════════════════════════════════════════════════════════
#  KONSTANSOK
# ════════════════════════════════════════════════════════════════════════════

APP_NAME    = "Universal TTS Pro"
VERSION     = "1.3.1"
CREATE_NO_WINDOW = 0x08000000

# Supertonic hangok listája
SUPERTONIC_VOICES = [
    "ST: Alex  [M1]",
    "ST: James [M2]",
    "ST: Robert[M3]",
    "ST: Sam   [M4]",
    "ST: Daniel[M5]",
    "ST: Sarah [F1]",
    "ST: Lily  [F2]",
    "ST: Jessica[F3]",
    "ST: Olivia[F4]",
    "ST: Emily [F5]",
]

# opusenc letöltési URL-ek (fallback sorrendben)
OPUSENC_URLS = [
    "https://archive.mozilla.org/pub/opus/win32/opus-tools-0.2-opus-1.3.1.zip",
    "https://github.com/xiph/opus-tools/releases/download/v0.2/opus-tools-0.2-opus-1.3.1-win32.zip",
]

# Modell letöltési info
MODEL_DOWNLOAD_INFO = {
    "HU - Anna": {
        "name": "Magyar (HU) - hu_HU-anna-medium",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/hu/hu_HU/anna/medium/",
        "files": ["hu_HU-anna-medium.onnx", "hu_HU-anna-medium.onnx.json"],
        "page": "https://huggingface.co/rhasspy/piper-voices/tree/main/hu/hu_HU/anna/medium",
        "note": "⚠️ FONTOS: A futtatáshoz a 'hu_HU-anna-medium.onnx.tokens' fájlnak is a 'models' mappában kell lennie! (Keresd a letöltött ZIP csomagban!)"
    },
    "HU - Berta": {
        "name": "Magyar (HU) - hu_HU-berta-medium",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/hu/hu_HU/berta/medium/",
        "files": ["hu_HU-berta-medium.onnx", "hu_HU-berta-medium.onnx.json"],
        "page": "https://huggingface.co/rhasspy/piper-voices/tree/main/hu/hu_HU/berta/medium",
        "note": "⚠️ FONTOS: A futtatáshoz a 'hu_HU-berta-medium.onnx.tokens' fájlnak is a 'models' mappában kell lennie! (Keresd a letöltött ZIP csomagban!)"
    },
    "HU - Imre": {
        "name": "Magyar (HU) - hu_HU-imre-medium",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/hu/hu_HU/imre/medium/",
        "files": ["hu_HU-imre-medium.onnx", "hu_HU-imre-medium.onnx.json"],
        "page": "https://huggingface.co/rhasspy/piper-voices/tree/main/hu/hu_HU/imre/medium",
        "note": "⚠️ FONTOS: A futtatáshoz a 'hu_HU-imre-medium.onnx.tokens' fájlnak is a 'models' mappában kell lennie! (Keresd a letöltött ZIP csomagban!)"
    },
    "EN - LibriTTS": {
        "name": "Angol (EN) - en_US-libritts_r-medium",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/",
        "files": ["en_US-libritts_r-medium.onnx", "en_US-libritts_r-medium.onnx.json"],
        "page": "https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/libritts_r/medium",
        "note": "⚠️ IMPORTANT: For the program to run, the 'en_US-libritts_r-medium.onnx.tokens' file must also be in the 'models' folder! (Find it in the downloaded ZIP package!)"
    },
    "RO - Mihai": {
        "name": "Román (RO) - ro_RO-mihai-medium",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/ro/ro_RO/mihai/medium/",
        "files": ["ro_RO-mihai-medium.onnx", "ro_RO-mihai-medium.onnx.json"],
        "page": "https://huggingface.co/rhasspy/piper-voices/tree/main/ro/ro_RO/mihai/medium",
        "note": "⚠️ IMPORTANT: Pentru ca programul să funcționeze, fișierul 'ro_RO-mihai-medium.onnx.tokens' trebuie să fie și el în folderul 'models'! (Căutați-l în arhiva ZIP descărcată!)"
    },
}

# Összes elérhető piper modell listája letöltéshez
PIPER_MODEL_INDEX = "https://huggingface.co/rhasspy/piper-voices/raw/main/voices.json"

# ════════════════════════════════════════════════════════════════════════════
#  ÚTVONAL SEGÉDFÜGGVÉNYEK
# ════════════════════════════════════════════════════════════════════════════

def resource_path(relative_path):
    """PyInstaller _MEIPASS vagy script mappa."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def get_data_path(relative_path):
    """Az EXE / script melletti mappa — ide mennek a modellek, output stb."""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def find_onnx_models():
    """Visszaadja az összes talált .onnx modell nevét."""
    found = []
    dirs = [get_data_path("models"), resource_path("models")]
    for d in dirs:
        if os.path.exists(d):
            found += [f for f in os.listdir(d) if f.endswith(".onnx")]
    return sorted(list(set(found)))

def find_supertonic_models():
    """Rekurzivan keresi a Supertonic modell fajlokat a models/supertonic3/ mappaban
    es osszes almappajaban. Visszaadja: (found_ok, st_root, paths_dict)
    """
    st_root = get_data_path(os.path.join("models", "supertonic3"))
    if not os.path.isdir(st_root):
        return False, st_root

    # Rekurzivan megkeresi a fajlt az osszes almappaban
    def find_file(filename, search_root):
        for dirpath, dirnames, filenames in os.walk(search_root):
            if filename in filenames:
                return os.path.join(dirpath, filename)
        return None

    encoder = find_file("text_encoder.onnx", st_root)
    vocoder = find_file("vocoder.onnx", st_root)
    tts_json = find_file("tts.json", st_root)

    ok = all([encoder, vocoder, tts_json])
    return ok, st_root


def find_opusenc():
    """Megkeresi az opusenc.exe-t a lehetséges helyeken."""
    candidates = [
        resource_path("opusenc.exe"),
        get_data_path("opusenc.exe"),
        get_data_path(os.path.join("tools", "opusenc.exe")),
        os.path.join(os.path.dirname(sys.executable), "opusenc.exe")
          if getattr(sys, 'frozen', False) else "",
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None

def find_onnx_models():
    """Visszaadja az összes talált .onnx modell nevét."""
    found = []
    dirs = [get_data_path("models"), resource_path("models")]
    for d in dirs:
        if os.path.exists(d):
            found += [f for f in os.listdir(d) if f.endswith(".onnx")]
    return sorted(list(set(found)))

def find_supertonic_models():
    """Ellenőrzi, hogy a Supertonic modell fájlok megvannak-e.
    Mappastruktúra: models/supertonic3/onnx/ (text_encoder.onnx, vocoder.onnx)
                   models/supertonic3/       (tts.json, config.json)
                   models/supertonic3/.cache/ (cache)
    """
    st_root = get_data_path(os.path.join("models", "supertonic3"))
    onnx_dir = os.path.join(st_root, "onnx")
    # tts.json lehet a gyokerben VAGY az onnx/ mappaban
    json_candidates = [
        os.path.join(st_root, "tts.json"),
        os.path.join(onnx_dir, "tts.json"),
    ]
    required = [
        os.path.join(onnx_dir, "text_encoder.onnx"),
        os.path.join(onnx_dir, "vocoder.onnx"),
    ]
    if not os.path.isdir(st_root):
        return False, st_root
    missing = [f for f in required if not os.path.isfile(f)]
    # tts.json barmely helyen megfelel
    if not any(os.path.isfile(p) for p in json_candidates):
        missing.append(json_candidates[0])
    return (len(missing) == 0), st_root

# ════════════════════════════════════════════════════════════════════════════
#  DEPENDENCY MANAGER — ellenőrzés + letöltés
# ════════════════════════════════════════════════════════════════════════════

class DependencyManager:
    """
    Összegyűjti az összes függőség állapotát, és képes letölteni / telepíteni
    a hiányzó komponenseket.
    """

    def __init__(self):
        self.results = {}  # name → {"ok": bool, "msg": str, "critical": bool}
        self.refresh()

    def refresh(self):
        """Újraellenőrzi az összes komponenst."""
        r = {}
        IS_FROZEN = getattr(sys, 'frozen', False)

        # --- Python csomagok (csak .py módban releváns) ---
        if not IS_FROZEN:
            r["sherpa_onnx"] = {
                "label":    "sherpa-onnx  (TTS motor)",
                "ok":       SHERPA_OK,
                "critical": True,
                "fix_type": "pip",
                "fix_arg":  "sherpa-onnx",
                "msg":      "pip install sherpa-onnx" if not SHERPA_OK else "OK",
            }
            r["sounddevice"] = {
                "label":    "sounddevice  (hanglejátszás)",
                "ok":       SD_OK,
                "critical": True,
                "fix_type": "pip",
                "fix_arg":  "sounddevice",
                "msg":      "pip install sounddevice" if not SD_OK else "OK",
            }
            r["numpy"] = {
                "label":    "numpy  (számítás)",
                "ok":       NUMPY_OK,
                "critical": True,
                "fix_type": "pip",
                "fix_arg":  "numpy",
                "msg":      "pip install numpy" if not NUMPY_OK else "OK",
            }
            r["supertonic_pkg"] = {
                "label":    "supertonic  (ST hangok, opcionális)",
                "ok":       SUPERTONIC_PKG_OK,
                "critical": False,
                "fix_type": "pip",
                "fix_arg":  "supertonic",
                "msg":      "pip install supertonic" if not SUPERTONIC_PKG_OK else "OK",
            }

        # --- opusenc.exe ---
        opus_path = find_opusenc()
        r["opusenc"] = {
            "label":    "opusenc.exe  (OPUS mentés)",
            "ok":       opus_path is not None,
            "critical": False,
            "fix_type": "download_opusenc",
            "fix_arg":  get_data_path("opusenc.exe"),
            "msg":      opus_path if opus_path else "Hiányzik — letölthető",
        }

        # --- ONNX modellek ---
        models = find_onnx_models()
        r["models"] = {
            "label":    f"ONNX hangmodellek  ({len(models)} db)",
            "ok":       len(models) > 0,
            "critical": True,
            "fix_type": "model_info",
            "fix_arg":  "",
            "msg":      ", ".join(models[:3]) + ("…" if len(models) > 3 else "")
                        if models else "Nincs modell a models/ mappában!",
        }

        # --- Supertonic modell fájlok ---
        st_ok, st_dir = find_supertonic_models()
        r["supertonic_models"] = {
            "label":    "Supertonic3 modell (~305 MB, opcionális)",
            "ok":       st_ok,
            "critical": False,
            "fix_type": "supertonic_dl",
            "fix_arg":  st_dir,
            "msg":      f"Found: {st_dir}" if st_ok else f"Missing — searched: {st_dir}",
        }

        self.results = r
        return r

    def has_critical_missing(self):
        return any(not v["ok"] and v["critical"] for v in self.results.values())

    def all_ok(self):
        return all(v["ok"] for v in self.results.values())

    def pip_install(self, package_name, progress_cb=None):
        """pip install futtatása. Visszatér: (success, output)."""
        try:
            cmd = [sys.executable, "-m", "pip", "install", package_name,
                   "--quiet", "--no-warn-script-location"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            ok = proc.returncode == 0
            out = proc.stdout + proc.stderr
            return ok, out
        except subprocess.TimeoutExpired:
            return False, "Időtúllépés (timeout)"
        except Exception as e:
            return False, str(e)

    def download_opusenc(self, dest_path, progress_cb=None):
        """
        Letölti az opusenc.exe-t a ZIP csomagból.
        dest_path: a célútvonal (pl. get_data_path('opusenc.exe'))
        """
        last_err = ""
        for url in OPUSENC_URLS:
            try:
                if progress_cb:
                    progress_cb(f"Letöltés: {url[:60]}…")
                data = urllib.request.urlopen(url, timeout=30).read()
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    # Keresünk valami opusenc-szerű fájlt
                    for name in z.namelist():
                        if "opusenc" in name.lower() and name.endswith(".exe"):
                            with z.open(name) as src, open(dest_path, "wb") as dst:
                                dst.write(src.read())
                            if progress_cb:
                                progress_cb(f"opusenc.exe kicsomagolva: {dest_path}")
                            return True, dest_path
                last_err = "opusenc.exe nem található a ZIP-ben"
            except Exception as e:
                last_err = str(e)
                continue
        return False, last_err

    def download_model_file(self, lang_code, progress_cb=None):
        """
        Letölti az adott nyelvhez tartozó piper modell fájlokat.
        Visszatér: (success, message)
        """
        info = MODEL_DOWNLOAD_INFO.get(lang_code)
        if not info:
            return False, f"Ismeretlen nyelv: {lang_code}"
        dest_dir = get_data_path("models")
        os.makedirs(dest_dir, exist_ok=True)
        errors = []
        for fname in info["files"]:
            url = info["url"] + fname
            dest = os.path.join(dest_dir, fname)
            if os.path.isfile(dest):
                continue
            try:
                if progress_cb:
                    progress_cb(f"Letöltés: {fname}…")
                urllib.request.urlretrieve(url, dest)
            except Exception as e:
                errors.append(f"{fname}: {e}")
        if errors:
            return False, "\n".join(errors)
        return True, f"Modellek letöltve: {dest_dir}"

# ════════════════════════════════════════════════════════════════════════════
#  SETUP WIZARD — indítási telepítő ablak
# ════════════════════════════════════════════════════════════════════════════

class SetupWizard(tk.Toplevel):
    """
    Indításkor megjelenik, ha valamelyik komponens hiányzik.
    Lehetővé teszi a letöltést / telepítést közvetlenül az ablakból.
    """

    BG   = "#1a1a2e"
    FG   = "#e0e0e0"
    ACC  = "#00d4ff"
    WARN = "#ffcc00"
    ERR  = "#ff6666"
    OK_C = "#00ff88"

    def __init__(self, parent, dep_mgr: DependencyManager, on_continue_cb=None):
        super().__init__(parent)
        self.dep_mgr     = dep_mgr
        self.on_cont_cb  = on_continue_cb
        self._rows       = {}   # key → {"icon_lbl", "msg_lbl", "btn"}
        self._busy       = False

        self.title(f"{APP_NAME} v{VERSION}  —  Beállítás / Setup")
        self.geometry("820x620")
        self.configure(bg=self.BG)
        self.resizable(True, True)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_exit)

        self._build()
        self._refresh_rows()

    # ------------------------------------------------------------------ build
    def _build(self):
        hdr = tk.Frame(self, bg=self.BG)
        hdr.pack(fill="x", padx=15, pady=(12, 4))
        tk.Label(hdr, text=f"⚙  {APP_NAME} — Component Checker",
                 bg=self.BG, fg=self.ACC, font=("Arial", 13, "bold")).pack(side="left")

        tk.Label(self,
                 text="To start the program, the following components are required.\n"
                      "Click the 'Install / Download' button to install any missing ones,\n"
                      "or place the files in the appropriate folders manually.",
                 bg=self.BG, fg="#aaa", font=("Arial", 9), justify="left"
                 ).pack(anchor="w", padx=15, pady=(0, 8))

        # Elválasztó
        tk.Frame(self, bg="#333355", height=1).pack(fill="x", padx=10)

        # Görgethető komponens lista
        list_outer = tk.Frame(self, bg=self.BG)
        list_outer.pack(fill="both", expand=True, padx=10, pady=6)

        self._canvas = tk.Canvas(list_outer, bg=self.BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_outer, orient="vertical",
                                 command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._list_frame = tk.Frame(self._canvas, bg=self.BG)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._list_frame, anchor="nw")
        self._list_frame.bind("<Configure>",
            lambda e: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
            lambda e: self._canvas.itemconfig(
                self._canvas_window, width=e.width))

        # Progress / log szöveg
        tk.Frame(self, bg="#333355", height=1).pack(fill="x", padx=10)
        log_frame = tk.Frame(self, bg="#111122")
        log_frame.pack(fill="x", padx=10, pady=(4, 0))
        self._log_var = tk.StringVar(value="")
        tk.Label(log_frame, textvariable=self._log_var,
                 bg="#111122", fg="#aaffcc", font=("Consolas", 8),
                 anchor="w").pack(fill="x", padx=8, pady=3)

        # Gombok
        btn_row = tk.Frame(self, bg=self.BG)
        btn_row.pack(fill="x", padx=10, pady=10)

        self._btn_refresh = tk.Button(btn_row, text="🔄 Re-check",
            command=self._do_refresh,
            bg="#333366", fg="#fff", width=16, relief="flat", pady=4)
        self._btn_refresh.pack(side="left", padx=5)

        tk.Button(btn_row, text="📂 Open models/ folder",
            command=self._open_models_folder,
            bg="#444", fg="#ddd", width=22, relief="flat", pady=4
            ).pack(side="left", padx=5)

        self._btn_continue = tk.Button(btn_row, text="▶  Continue",
            command=self._on_continue,
            bg="#006633", fg="#fff", font=("Arial", 10, "bold"),
            width=22, relief="flat", pady=4)
        self._btn_continue.pack(side="right", padx=5)

        tk.Button(btn_row, text="✕ Exit", command=self._on_exit,
            bg="#662222", fg="#fff", width=10, relief="flat", pady=4
            ).pack(side="right", padx=5)

    # --------------------------------------------------------- row rendering
    def _refresh_rows(self):
        """Újraépíti a komponens-lista sorokat."""
        for w in self._list_frame.winfo_children():
            w.destroy()
        self._rows = {}

        for key, info in self.dep_mgr.results.items():
            self._add_row(key, info)

        self._update_continue_btn()

    def _add_row(self, key, info):
        ok       = info["ok"]
        critical = info["critical"]
        fix_type = info["fix_type"]

        row = tk.Frame(self._list_frame, bg="#1e1e2e", bd=0)
        row.pack(fill="x", padx=4, pady=2, ipady=4)

        # Ikon
        icon_text = "✅" if ok else ("🔴" if critical else "🟡")
        icon_lbl = tk.Label(row, text=icon_text,
                             bg="#1e1e2e", font=("Arial", 12), width=3)
        icon_lbl.pack(side="left", padx=(6, 2))

        # Label + msg
        info_frame = tk.Frame(row, bg="#1e1e2e")
        info_frame.pack(side="left", fill="x", expand=True, padx=4)

        name_color = self.OK_C if ok else (self.ERR if critical else self.WARN)
        tk.Label(info_frame, text=info["label"],
                 bg="#1e1e2e", fg=name_color,
                 font=("Consolas", 9, "bold"), anchor="w"
                 ).pack(anchor="w")

        msg_lbl = tk.Label(info_frame, text=info["msg"],
                           bg="#1e1e2e", fg="#888", font=("Consolas", 8),
                           anchor="w", wraplength=480, justify="left")
        msg_lbl.pack(anchor="w")

        # Akció gomb
        btn = None
        if not ok:
            if fix_type == "pip":
                btn = tk.Button(row, text="⬇ pip install",
                    command=lambda k=key, a=info["fix_arg"]: self._do_pip(k, a),
                    bg="#3d5a99", fg="#fff", width=14, relief="flat",
                    font=("Arial", 8))
            elif fix_type == "download_opusenc":
                btn = tk.Button(row, text="⬇ opusenc letölt",
                    command=lambda k=key, a=info["fix_arg"]: self._do_opusenc(k, a),
                    bg="#5a3d99", fg="#fff", width=16, relief="flat",
                    font=("Arial", 8))
            elif fix_type == "model_info":
                btn = tk.Button(row, text="ℹ Modell letöltési útmutató",
                    command=self._show_model_guide,
                    bg="#7a5500", fg="#fff", width=22, relief="flat",
                    font=("Arial", 8))
            elif fix_type == "supertonic_dl":
                lbl = "🔁 Auto-letöltés (supertonic)" if SUPERTONIC_PKG_OK else "⬇ Telepítsd a supertonic csomagot"
                btn = tk.Button(row, text=lbl,
                    command=lambda k=key, a=info["fix_arg"]: self._do_supertonic(k, a),
                    bg="#4a2070", fg="#fff", width=28, relief="flat",
                    font=("Arial", 8))

            if btn:
                btn.pack(side="right", padx=6)

        self._rows[key] = {
            "row": row, "icon_lbl": icon_lbl,
            "msg_lbl": msg_lbl, "btn": btn
        }

    # -------------------------------------------------- action handlers
    def _log(self, msg):
        self._log_var.set(msg)
        self.update_idletasks()

    def _do_refresh(self):
        self._log("Ellenőrzés…")
        self.dep_mgr.refresh()
        self._refresh_rows()
        self._log("✔ Frissítve.")

    def _do_pip(self, key, package_name):
        if self._busy: return
        self._busy = True
        self._log(f"pip install {package_name} …")
        self._btn_refresh.config(state="disabled")
        def _run():
            ok, out = self.dep_mgr.pip_install(package_name)
            self.after(0, lambda: self._pip_done(key, package_name, ok, out))
        threading.Thread(target=_run, daemon=True).start()

    def _pip_done(self, key, pkg, ok, out):
        self._busy = False
        self._btn_refresh.config(state="normal")
        if ok:
            self._log(f"✔ {pkg} telepítve. Indítsd újra a programot!")
            messagebox.showinfo("Telepítés kész",
                f"'{pkg}' sikeresen telepítve!\n\nIndítsd újra a programot.")
        else:
            self._log(f"✖ {pkg} telepítés sikertelen.")
            messagebox.showerror("Telepítés sikertelen",
                f"'{pkg}' nem sikerült telepíteni:\n\n{out[:600]}\n\n"
                "Próbáld manuálisan: pip install " + pkg)

    def _do_opusenc(self, key, dest_path):
        if self._busy: return
        self._busy = True
        self._log("opusenc.exe letöltése…")
        self._btn_refresh.config(state="disabled")
        def _run():
            ok, msg = self.dep_mgr.download_opusenc(dest_path,
                progress_cb=lambda m: self.after(0, lambda: self._log(m)))
            self.after(0, lambda: self._opusenc_done(ok, msg))
        threading.Thread(target=_run, daemon=True).start()

    def _opusenc_done(self, ok, msg):
        self._busy = False
        self._btn_refresh.config(state="normal")
        if ok:
            self._log(f"✔ opusenc.exe kész: {msg}")
            self.dep_mgr.refresh()
            self._refresh_rows()
        else:
            self._log(f"✖ Letöltés sikertelen: {msg}")
            messagebox.showerror("Letöltés sikertelen",
                f"opusenc.exe letöltése nem sikerült:\n{msg}\n\n"
                "Töltsd le kézzel: https://opus-codec.org/downloads/\n"
                f"Másold ide: {get_data_path('opusenc.exe')}")

    def _do_supertonic(self, key, st_dir):
        if not SUPERTONIC_PKG_OK:
            messagebox.showinfo("Supertonic csomag hiányzik",
                "Először telepítsd a supertonic csomagot:\n\n"
                "pip install supertonic\n\nMajd indítsd újra a programot.")
            return
        if self._busy: return
        self._busy = True
        self._log("Supertonic modellek letöltése (~305 MB)… türelem!")
        os.makedirs(st_dir, exist_ok=True)
        def _run():
            try:
                os.environ["SUPERTONIC_CACHE_DIR"] = st_dir
                SupertonicTTS(auto_download=True)
                self.after(0, lambda: self._supertonic_done(True, "OK"))
            except Exception as e:
                self.after(0, lambda: self._supertonic_done(False, str(e)))
        threading.Thread(target=_run, daemon=True).start()

    def _supertonic_done(self, ok, msg):
        self._busy = False
        if ok:
            self._log("✔ Supertonic modellek letöltve.")
            self.dep_mgr.refresh()
            self._refresh_rows()
        else:
            self._log(f"✖ Supertonic letöltés hiba: {msg}")
            messagebox.showerror("Hiba", msg[:500])

    def _show_model_guide(self):
        """Megmutatja a modell letöltési útmutatót."""
        win = tk.Toplevel(self)
        win.title("📥 Modell letöltési útmutató")
        win.geometry("860x680")
        win.configure(bg=self.BG)
        win.grab_set()

        txt = tk.Text(win, bg="#1e1e2e", fg=self.FG, font=("Consolas", 9),
                      wrap="word", padx=10, pady=10)
        txt.pack(fill="both", expand=True, padx=8, pady=8)

        models_dir = get_data_path("models")
        guide = (
            "═══════════════════════════════════════════════════════════\n"
            "  PIPER TTS MODELL LETÖLTÉSI ÚTMUTATÓ\n"
            "═══════════════════════════════════════════════════════════\n\n"
            f"  A modellek helye: {models_dir}\n\n"
            "───────────────────────────────────────────────────────────\n"
            "  GYORS LETÖLTÉS — HuggingFace oldalról:\n"
            "───────────────────────────────────────────────────────────\n\n"
        )
        for lang, info in MODEL_DOWNLOAD_INFO.items():
            guide += f"  [{lang}] {info['name']}\n"
            guide += f"      Oldal:  {info['page']}\n"
            for f in info["files"]:
                guide += f"      Fájl:   {info['url']}{f}\n"
            guide += "\n"

        guide += (
            "───────────────────────────────────────────────────────────\n"
            "  MÁS HANGOK / ALL VOICES:\n"
            "───────────────────────────────────────────────────────────\n"
            f"  {PIPER_MODEL_INDEX}\n\n"
            "  Vagy böngészd: https://huggingface.co/rhasspy/piper-voices\n\n"
            "───────────────────────────────────────────────────────────\n"
            "  TELEPÍTÉS LÉPÉSEI:\n"
            "───────────────────────────────────────────────────────────\n"
            "  1. Töltsd le a .onnx és a .onnx.json fájlokat\n"
            f"  2. Másold őket ebbe a mappába: {models_dir}\n"
            "  3. Indítsd újra a programot — a modellek automatikusan\n"
            "     megjelennek a legördülő listában.\n\n"
            "  PENDRIVE / OFFLINE HASZNÁLAT:\n"
            "  Ha pendrive-on viszed a programot, csak hozd magaddal\n"
            "  az összes fájlt a program mappájával együtt.\n"
            "  Internet nélkül is működik minden funkció!\n\n"
            "═══════════════════════════════════════════════════════════\n"
            "  Soli Deo Gloria\n"
        )

        txt.insert("1.0", guide)
        txt.config(state="disabled")

        btn_row = tk.Frame(win, bg=self.BG)
        btn_row.pack(fill="x", pady=6, padx=8)

        def copy_models_path():
            win.clipboard_clear()
            win.clipboard_append(models_dir)
            self._log(f"Vágólapra másolva: {models_dir}")

        tk.Button(btn_row, text="📋 models/ útvonal másolása",
            command=copy_models_path, bg="#444", fg="#fff"
            ).pack(side="left", padx=4)
        tk.Button(btn_row, text="📂 models/ megnyitása",
            command=self._open_models_folder, bg="#555", fg="#fff"
            ).pack(side="left", padx=4)
        tk.Button(btn_row, text="Bezárás",
            command=win.destroy, bg="#333", fg="#aaa", width=10
            ).pack(side="right", padx=4)

    def _open_models_folder(self):
        d = get_data_path("models")
        os.makedirs(d, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(d)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", d])
            else:
                subprocess.Popen(["xdg-open", d])
        except Exception as e:
            self._log(f"Megnyitás sikertelen: {e}")

    def _update_continue_btn(self):
        has_crit = self.dep_mgr.has_critical_missing()
        if has_crit:
            self._btn_continue.config(bg="#885500",
                text="▶  Folytatás (korlátozott)")
        else:
            self._btn_continue.config(bg="#006633",
                text="▶  Continue")

    def _on_continue(self):
        self.grab_release()
        self.destroy()
        if self.on_cont_cb:
            self.on_cont_cb()

    def _on_exit(self):
        self.grab_release()
        self.destroy()
        sys.exit(0)


# ════════════════════════════════════════════════════════════════════════════
#  FORDÍTÁSOK
# ════════════════════════════════════════════════════════════════════════════

LANGS = {
    "HU": {
        "title":        "UNIVERSAL TTS PRO",
        "settings":     "Beállítások",
        "speak":        "FELOLVASÁS",
        "stop":         "STOP",
        "input_lbl":    "Bemeneti szöveg:",
        "out_lbl":      "Kimeneti (tisztított) szöveg:",
        "import":       "Import .txt",
        "fix":          "JAVÍTÁS (KONVERTÁL)",
        "dict":         "✎ Szótár",
        "clear":        "Törlés",
        "save_wav":     "WAV Mentés",
        "save_opus":    "OPUS Mentés",
        "status_ready": "Kész / Ready",
        "status_gen":   "Generálás...",
        "status_opus":  "Opus kódolás...",
        "save_mod":     "MENTÉS MODELBE",
        "close_btn":    "BEZÁRÁS / CLOSE",
        "about_btn":    "Névjegy",
        "lbl_speed":    "Speed (Length Scale):",
        "lbl_silence":  "Silence:",
        "lbl_buffer":   "Buffer size:",
    },
    "EN": {
        "title":        "UNIVERSAL TTS PRO",
        "settings":     "Settings",
        "speak":        "QUICK SPEAK",
        "stop":         "STOP",
        "input_lbl":    "Input Text:",
        "out_lbl":      "Cleaned Output:",
        "import":       "Import .txt",
        "fix":          "FIX & CONVERT",
        "dict":         "✎ Dictionary",
        "clear":        "Clear",
        "save_wav":     "Save WAV",
        "save_opus":    "Save OPUS",
        "status_ready": "Ready",
        "status_gen":   "Generating...",
        "status_opus":  "Opus encoding...",
        "save_mod":     "SAVE TO MODEL",
        "close_btn":    "CLOSE / BEZÁRÁS",
        "about_btn":    "About",
        "lbl_speed":    "Speed (Length Scale):",
        "lbl_silence":  "Silence:",
        "lbl_buffer":   "Buffer size:",
    },
    "RO": {
        "title":        "UNIVERSAL TTS PRO",
        "settings":     "Setări",
        "speak":        "CITIRE RAPIDĂ",
        "stop":         "STOP",
        "input_lbl":    "Text de intrare:",
        "out_lbl":      "Text curățat (ieșire):",
        "import":       "Import .txt",
        "fix":          "CORECTARE (CONVERSIE)",
        "dict":         "✎ Dicționar",
        "clear":        "Șterge",
        "save_wav":     "Salvare WAV",
        "save_opus":    "Salvare OPUS",
        "status_ready": "Gata / Ready",
        "status_gen":   "Generare...",
        "status_opus":  "Codificare Opus...",
        "save_mod":     "SALVARE ÎN MODEL",
        "close_btn":    "ÎNCHIDE / CLOSE",
        "about_btn":    "Despre",
        "lbl_speed":    "Speed (Length Scale):",
        "lbl_silence":  "Silence:",
        "lbl_buffer":   "Buffer size:",
    },
}


def st_sdk_name(display_name):
    m = re.search(r'\[([MF]\d)\]', display_name)
    return m.group(1) if m else display_name.replace("ST: ", "").strip()


# ════════════════════════════════════════════════════════════════════════════
#  FŐ ALKALMAZÁS
# ════════════════════════════════════════════════════════════════════════════

class App:
    def __init__(self, root):
        self.root = root
        self.lang = "HU"
        self.settings_visible = False
        self.settings_visible_st = False
        self._stop_speak = False
        self.current_proc = None
        self.is_speaking = False
        self._timer_running = False
        self._conv_start_time = None
        self._total_chars = 0
        self._bar_anim_id = None
        self._bar_pct = 0
        self._search_win = None
        self._search_widget = None
        self.tts = None
        self.st_tts = None
        self._st_style = None
        self._hl_tag = "sentence_hl"

        for d in ["models", "output_audio"]:
            path = get_data_path(d)
            if not os.path.exists(path):
                os.makedirs(path)

        self.models = self.scan_models()

        start_model = self.models[0] if self.models else "Nincs modell"
        for m in self.models:
            if "hu" in m.lower():
                start_model = m
                break

        self.model_var = tk.StringVar(value=start_model)
        self.model_var.trace_add("write", lambda *args: self._on_model_change())

        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("900x780")
        self.root.configure(bg="#1e1e2e")

        self.build_ui()
        self.refresh_ui()

        # Figyelmeztető sáv ha kritikus függőség hiányzik
        if not SHERPA_OK or not SD_OK or not NUMPY_OK:
            self.lbl_status.config(
                text="⚠ Hiányzó csomagok! Menü → Program → Függőségek ellenőrzése",
                fg="#ff6666")

    # ---------------------------------------------------------------- sherpa
    def init_sherpa(self):
        if not SHERPA_OK:
            self._show_error("sherpa-onnx hiányzik",
                "A sherpa-onnx csomag nincs telepítve!\n\n"
                "pip install sherpa-onnx\n\nMajd indítsd újra a programot.")
            return False
        if not SD_OK:
            self._show_error("sounddevice hiányzik",
                "pip install sounddevice\nMajd indítsd újra a programot.")
            return False
        if not NUMPY_OK:
            self._show_error("numpy hiányzik",
                "pip install numpy\nMajd indítsd újra a programot.")
            return False

        if self.tts is not None:
            return True
        try:
            model_name = self.model_var.get()
            model_path = self.find_model_path(model_name)
            model_dir  = os.path.dirname(model_path)

            tokens_path = ""
            base_name = os.path.splitext(model_name)[0]
            possible_tokens = [
                os.path.join(model_dir, f"{model_name}.tokens"),
                os.path.join(model_dir, f"{base_name}.onnx.tokens"),
                os.path.join(model_dir, f"{base_name}.tokens"),
                os.path.join(model_dir, f"{base_name}.tokens.txt"),
                os.path.join(model_dir, "tokens.txt"),
                os.path.join(model_dir, "tokens"),
            ]
            for p in possible_tokens:
                if os.path.exists(p):
                    tokens_path = p
                    break

            if not tokens_path:
                for f in os.listdir(model_dir):
                    if "tokens" in f.lower():
                        tokens_path = os.path.join(model_dir, f)
                        break

            if not tokens_path:
                self._show_error("Tokens fájl nem található",
                    f"Nem találok tokens fájlt a {model_dir} mappában.\n"
                    f"Keresett nevek: {base_name}.onnx.tokens, tokens.txt")
                return False

            vits_config = sherpa_onnx.OfflineTtsVitsModelConfig(
                model=model_path, lexicon="", tokens=tokens_path,
                data_dir=model_dir,
                noise_scale=float(self.e_nscale.get()),
                noise_scale_w=float(self.e_nw.get()),
                length_scale=float(self.e_speed.get())
            )
            model_config = sherpa_onnx.OfflineTtsModelConfig(
                vits=vits_config, num_threads=4, debug=False)
            full_config  = sherpa_onnx.OfflineTtsConfig(
                model=model_config, rule_fsts="", max_num_sentences=1)
            self.tts = sherpa_onnx.OfflineTts(full_config)
            return True
        except Exception as e:
            import traceback
            self._show_error("Sherpa Init Hiba",
                f"Nem sikerült a motor indítása!\n\nHiba: {e}\n\n"
                f"{traceback.format_exc()}")
            return False

    def init_supertonic(self):
        if not SUPERTONIC_PKG_OK:
            self._show_error("Supertonic nem telepítve",
                "pip install supertonic\nMajd indítsd újra a programot.")
            return False

        # ── Offline ellenőrzés: a fájlok ott vannak-e? ──────────────────────
        st_ok, st_dir = find_supertonic_models()
        if not st_ok:
            self._show_error(
                "Supertonic3 modell fájlok hiányoznak",
                f"A következő mappában nem találhatók a szükséges fájlok:\n"
                f"  {st_dir}\n\n"
                f"Szükséges fájlok (rekurzív keresés):\n"
                f"  text_encoder.onnx\n  vocoder.onnx\n  tts.json\n\n"
                f"Letöltéshez: Menü → Program → Függőségek ellenőrzése\n"
                f"  (internet szükséges, ~305 MB)\n\n"
                f"Frissítéshez: Menü → Program → ♻ Supertonic3 frissítése"
            )
            return False

        try:
            st_root = get_data_path(os.path.join("models", "supertonic3"))

            # Rekurzivan megkeresi a fajlt
            def _find(fname):
                for dp, dn, fn in os.walk(st_root):
                    if fname in fn:
                        return dp  # a mappa ahol a fajl van
                return None

            onnx_dir    = onnx_dir = st_root  # library maga keresi az onnx/ almappát
            cache_dir   = st_root
            for dp, dn, _ in os.walk(st_root):
                if ".cache" in dn:
                    cache_dir = dp
                    break

            if self.st_tts is None:
                self.root.after(0, lambda: self.lbl_status.config(
                    text="Supertonic betöltése…", fg="#ffaa00"))

                # config.json-t az onnx/ mappaba masoljuk ha csak a gyokerben van
                cfg_src = os.path.join(st_root, "config.json")
                cfg_dst = os.path.join(onnx_dir, "config.json")
                if os.path.isfile(cfg_src) and not os.path.isfile(cfg_dst):
                    import shutil
                    shutil.copy2(cfg_src, cfg_dst)

                os.environ["SUPERTONIC_CACHE_DIR"] = cache_dir
                os.environ["TRANSFORMERS_OFFLINE"] = "1"
                os.environ["HF_HUB_OFFLINE"]       = "1"

                try:
                    self.st_tts = SupertonicTTS(
                        model_dir=onnx_dir,
                        auto_download=False
                    )
                except TypeError:
                    self.st_tts = SupertonicTTS(auto_download=False)

            voice_name   = st_sdk_name(self.model_var.get())
            self._st_style = self.st_tts.get_voice_style(voice_name=voice_name)
            return True
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            st_root2 = get_data_path(os.path.join("models", "supertonic3"))
            found_files = []
            for dp, dn, fn in os.walk(st_root2):
                for f in fn:
                    if f.endswith((".onnx", ".json")):
                        found_files.append(os.path.relpath(os.path.join(dp, f), st_root2))
            files_str = "\n  ".join(found_files[:15]) if found_files else "— nincs fajl"
            self._show_error("Supertonic Hiba",
                f"Betöltési hiba:\n{e}\n\n"
                f"Talált fájlok ({st_root2}):\n  {files_str}\n\n"
                f"SUPERTONIC_CACHE_DIR: {os.environ.get('SUPERTONIC_CACHE_DIR','')}\n\n"
                f"{tb[:800]}")
            return False

    # ----------------------------------------------------------------- utils
    def _show_error(self, title, message):
        try:
            err_win = tk.Toplevel(self.root)
            err_win.title(f"⚠ {title}")
            err_win.geometry("700x350")
            err_win.configure(bg="#1e1e2e")
            err_win.transient(self.root)
            err_win.lift()
            tk.Label(err_win, text=title, bg="#1e1e2e", fg="#ff6666",
                     font=("Arial", 11, "bold")).pack(padx=10, pady=(10, 2), anchor="w")
            txt = tk.Text(err_win, bg="#2a2a3e", fg="#ffcccc",
                          font=("Consolas", 9), wrap="word", relief="flat", bd=0)
            txt.insert("1.0", str(message))
            txt.config(state="disabled")
            txt.pack(fill="both", expand=True, padx=10, pady=5)
            btn_f = tk.Frame(err_win, bg="#1e1e2e")
            btn_f.pack(fill="x", padx=10, pady=5)
            def copy_err():
                self.root.clipboard_clear()
                self.root.clipboard_append(str(message))
            tk.Button(btn_f, text="📋 Másolás", command=copy_err,
                      bg="#555", fg="#fff", width=12).pack(side="left", padx=4)
            tk.Button(btn_f, text="Bezárás", command=err_win.destroy,
                      bg="#444", fg="#fff", width=10).pack(side="right", padx=4)
        except Exception:
            messagebox.showerror(title, str(message)[:500])

    def get_fix_path(self):
        lang     = self.lang
        filename = f"javitasok_{lang}.txt"
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        p = os.path.join(base_path, filename)
        if os.path.exists(p): return p
        p_internal = os.path.join(base_path, "_internal", filename)
        if os.path.exists(p_internal): return p_internal
        self._create_default_fix_file(p, lang)
        return p

    def _create_default_fix_file(self, path, lang):
        HU_TEMPLATE = (
            "# JAVÍTÁSOK - Magyar (HU)\n"
            "# Formátum:  rövidítés:teljes_alak\n"
            "# Bibliai könyvek rövidítései:\n"
            "1Móz:1 Mózes\n2Móz:2 Mózes\n3Móz:3 Mózes\n"
            "4Móz:4 Mózes\n5Móz:5 Mózes\nJózs:Józsué\n"
            "Bír:Bírák\nRuth:Ruth\n1Sám:1 Sámuel\n2Sám:2 Sámuel\n"
            "1Kir:1 Királyok\n2Kir:2 Királyok\n1Krón:1 Krónika\n"
            "2Krón:2 Krónika\nEzsdr:Ezsdrás\nNeh:Nehémiás\nEszt:Eszter\n"
            "Jób:Jób\nZsolt:Zsoltárok\nPéld:Példabeszédek\nPréd:Prédikátor\n"
            "Én:Énekek Éneke\nÉzs:Ézsaiás\nJer:Jeremiás\nJSir:Jeremiás siralmai\n"
            "Ez:Ezékiel\nDán:Dániel\nHós:Hóseás\nJóel:Jóel\nÁm:Ámosz\n"
            "Abd:Abdiás\nJón:Jónás\nMik:Mikeás\nNáh:Náhum\nHab:Habakuk\n"
            "Sof:Sofóniás\nAgg:Aggeus\nZak:Zakariás\nMal:Malakiás\n"
            "Mát:Máté\nMt:Máté\nMár:Márk\nMk:Márk\nLuk:Lukács\nLk:Lukács\n"
            "Ján:János\nJn:János\nApCsel:Apostolok Cselekedetei\nRóm:Róma\n"
            "1Kor:1 Korinthus\n2Kor:2 Korinthus\nGal:Galata\nEf:Efézus\n"
            "Fil:Filippi\nKol:Kolossé\n1Thess:1 Thesszalonika\n2Thess:2 Thesszalonika\n"
            "1Tim:1 Timóteus\n2Tim:2 Timóteus\nTit:Titusz\n"
            "Zsid:Zsidókhoz írt levél\nJak:Jakab\n"
            "1Pét:1 Péter\n1Pt:1 Péter\n2Pét:2 Péter\n2Pt:2 Péter\n"
            "1Ján:1 János\n1Jn:1 János\n2Ján:2 János\n2Jn:2 János\n"
            "3Ján:3 János\n3Jn:3 János\nJúd:Júdás\nJel:Jelenések\n"
            "# Általános rövidítések:\n"
            "pl.:például\nstb.:és a többi\nill.:illetve\nv.:vagy\n"
            "Kr.e.:Krisztus előtt\nKr.u.:Krisztus után\n"
            "i.e.:időszámításunk előtt\ni.sz.:időszámításunk szerint\n"
            "Úsz.:Újszövetség\nÓsz.:Ószövetség\nfej.:fejezet\nvv.:versek\n"
        )
        EN_TEMPLATE = (
            "# CORRECTIONS - English (EN)\n"
            "# Format: abbreviation:full form\n"
            "Gen:Genesis\nEx:Exodus\nLev:Leviticus\nNum:Numbers\nDeut:Deuteronomy\n"
            "Josh:Joshua\nJudg:Judges\nRuth:Ruth\n"
            "1Sam:First Samuel\n2Sam:Second Samuel\n"
            "1Kgs:First Kings\n2Kgs:Second Kings\n"
            "1Chr:First Chronicles\n2Chr:Second Chronicles\n"
            "Ezra:Ezra\nNeh:Nehemiah\nEsth:Esther\nJob:Job\n"
            "Ps:Psalms\nProv:Proverbs\nEccl:Ecclesiastes\nSong:Song of Solomon\n"
            "Isa:Isaiah\nJer:Jeremiah\nLam:Lamentations\nEzek:Ezekiel\nDan:Daniel\n"
            "Hos:Hosea\nJoel:Joel\nAmos:Amos\nObad:Obadiah\nJonah:Jonah\n"
            "Mic:Micah\nNah:Nahum\nHab:Habakkuk\nZeph:Zephaniah\nHag:Haggai\n"
            "Zech:Zechariah\nMal:Malachi\n"
            "Matt:Matthew\nMark:Mark\nLuke:Luke\nJohn:John\nActs:Acts\n"
            "Rom:Romans\n1Cor:First Corinthians\n2Cor:Second Corinthians\n"
            "Gal:Galatians\nEph:Ephesians\nPhil:Philippians\nCol:Colossians\n"
            "1Thess:First Thessalonians\n2Thess:Second Thessalonians\n"
            "1Tim:First Timothy\n2Tim:Second Timothy\nTitus:Titus\nPhilem:Philemon\n"
            "Heb:Hebrews\nJas:James\n"
            "1Pet:First Peter\n2Pet:Second Peter\n"
            "1John:First John\n2John:Second John\n3John:Third John\n"
            "Jude:Jude\nRev:Revelation\n"
            "e.g.:for example\ni.e.:that is\netc.:and so on\nvs.:versus\n"
        )
        OTHER_TEMPLATE = (
            f"# CORRECTIONS / JAVÍTÁSOK - {lang}\n"
            f"# Format / Formátum:  abbreviation:full_form\n"
            f"# Lines starting with # are comments.\n"
            f"# Example / Példa:\n"
            f"# Gen:Genesis\n"
            f"# etc.:and so on\n"
        )
        try:
            if lang == "HU":   content = HU_TEMPLATE
            elif lang == "EN": content = EN_TEMPLATE
            else:              content = OTHER_TEMPLATE
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"[WARN] Could not create {path}: {e}")

    def scan_models(self):
        found = []
        dirs = [get_data_path("models"), resource_path("models")]
        for d in dirs:
            if os.path.exists(d):
                found += [f for f in os.listdir(d) if f.endswith(".onnx")]
        piper_models = sorted(list(set(found))) if found else []
        return piper_models + SUPERTONIC_VOICES if piper_models else SUPERTONIC_VOICES

    def _is_supertonic(self, model_name=""):
        return str(model_name).startswith("ST: ")

    def find_model_path(self, model_name):
        ext = get_data_path(os.path.join("models", model_name))
        if os.path.exists(ext): return ext
        return resource_path(os.path.join("models", model_name))

    # ---------------------------------------------------------------- UI build
    def build_ui(self):
        self.m_bar  = tk.Menu(self.root)
        self.h_menu = tk.Menu(self.m_bar, tearoff=0)
        self.h_menu.add_command(label="Help / Súgó",       command=self.show_help)
        self.h_menu.add_command(label="About / Névjegy",   command=self.show_about)
        self.h_menu.add_separator()
        self.h_menu.add_command(label="⚙ Függőségek / Setup",
                                command=self._open_dep_wizard)
        self.h_menu.add_separator()
        self.h_menu.add_command(label="♻ Supertonic3 Update…",
                                command=self._update_supertonic)
        self.m_bar.add_cascade(label="Program", menu=self.h_menu)
        self.root.config(menu=self.m_bar)

        ctrl = tk.Frame(self.root, bg="#2a2a3e", pady=5)
        ctrl.pack(fill="x", padx=10)

        self.btn_lang = tk.Button(ctrl, text="HU", command=self.toggle_lang,
                                  bg="#555", fg="#fff", width=4)
        self.btn_lang.pack(side="left", padx=5)

        self.mod_dropdown = tk.OptionMenu(ctrl, self.model_var, *self.models)
        self.mod_dropdown.pack(side="left", padx=5)

        # Piper (alap) hangok beállító gombja
        self.btn_settings_pp = tk.Button(
            ctrl,
            text="⚙ Piper",
            command=self.toggle_settings,
            bg="#2b4c7e",
            fg="#fff"
        )
        self.btn_settings_pp.pack(side="left", padx=5)

        # Supertonic hangok külön beállító ablaka
        self.btn_settings_st = tk.Button(
            ctrl,
            text="⚙ Supertronic",
            command=self.toggle_settings_st,
            bg="#2b4c7e",
            fg="#fff"
        )
        self.btn_settings_st.pack(side="left", padx=5)

        self.btn_speak = tk.Button(ctrl, text="", command=self.quick_speak,
                                   bg="#8a2be2", fg="#fff",
                                   font=("Arial", 9, "bold"))
        self.btn_speak.pack(side="right", padx=5)

        tk.Button(ctrl, text="STOP", command=self.stop_all,
                  bg="#ff4444", fg="#fff", font=("Arial", 9, "bold")
                  ).pack(side="right", padx=5)

        # Beállítások panel
        self.sett_pnl = tk.Frame(self.root, bg="#1e1e2e", bd=1,
                                  relief="solid", pady=5)
        def add_s(def_v):
            f = tk.Frame(self.sett_pnl, bg="#1e1e2e")
            f.pack(fill="x", padx=20, pady=1)
            lbl = tk.Label(f, text="", bg="#1e1e2e", fg="#fff",
                           width=25, anchor="w")
            lbl.pack(side="left")
            ent = tk.Entry(f, width=25)
            ent.insert(0, def_v)
            ent.pack(side="left", padx=10)
            return lbl, ent

        self.l_sp,  self.e_speed   = add_s("1.3")
        self.l_ns,  self.e_nscale  = add_s("0.55")
        self.l_nw,  self.e_nw      = add_s("0.6")
        self.l_si,  self.e_silence = add_s("0.5")
        self.l_op,  self.e_opus    = add_s("--bitrate 64")
        self.l_bf,  self.e_buffer  = add_s("4096")

        self.btn_save_mod = tk.Button(self.sett_pnl, text="",
                                      command=self.save_model_settings,
                                      bg="#00a896", fg="#fff")
        self.btn_save_mod.pack(pady=5)

        # ══════════ SUPERTONIC INLINE BEÁLLÍTÁSOK ══════════
        self.sett_pnl_st = tk.Frame(self.root, bg="#1e1e2e", bd=1,
                                    relief="solid", pady=5)
        tk.Label(self.sett_pnl_st, text="🎙  SUPERTONIC BEÁLLÍTÁSAI / SETTINGS",
                 bg="#1e1e2e", fg="#ff88cc",
                 font=("Arial", 9, "bold")).pack(pady=(4, 2))
        self.lbl_st_current = tk.Label(self.sett_pnl_st, text="",
                                       bg="#1e1e2e", fg="#888",
                                       font=("Arial", 8, "italic"))
        self.lbl_st_current.pack(pady=(0, 4))

        _f_sp = tk.Frame(self.sett_pnl_st, bg="#1e1e2e")
        _f_sp.pack(fill="x", padx=20, pady=3)
        tk.Label(_f_sp, text="Higher speed = faster",
                 bg="#1e1e2e", fg="#fff", width=28, anchor="w").pack(side="left")
        self.lbl_st_speed_val = tk.Label(_f_sp, text="1.00x",
                                         bg="#1e1e2e", fg="#ffaa00",
                                         font=("Arial", 9, "bold"), width=6)
        self.lbl_st_speed_val.pack(side="right", padx=4)
        self.scale_st_speed = tk.Scale(_f_sp, from_=0.7, to=2.0,
                                       resolution=0.05, orient="horizontal",
                                       bg="#1e1e2e", fg="#fff",
                                       highlightthickness=0, troughcolor="#444",
                                       showvalue=False,
                                       command=lambda v: self.lbl_st_speed_val.config(
                                           text=f"{float(v):.2f}x"))
        self.scale_st_speed.set(1.0)
        self.scale_st_speed.pack(side="left", fill="x", expand=True, padx=10)

        def _add_st_field(label_text, default):
            f = tk.Frame(self.sett_pnl_st, bg="#1e1e2e")
            f.pack(fill="x", padx=20, pady=1)
            tk.Label(f, text=label_text, bg="#1e1e2e", fg="#fff",
                     width=28, anchor="w").pack(side="left")
            ent = tk.Entry(f, width=25)
            ent.insert(0, default)
            ent.pack(side="left", padx=10)
            return ent

        self.e_st_silence = _add_st_field("Silence (sec):",         "0.5")
        self.e_st_opus    = _add_st_field("Opus Bitrate:",          "--bitrate 64")
        self.e_st_buffer  = _add_st_field("Buffer size:",           "4096")

        self.btn_save_st = tk.Button(self.sett_pnl_st,
                                     text="💾 MENTÉS MODELBE",
                                     command=self.save_supertonic_settings,
                                     bg="#00a896", fg="#fff",
                                     font=("Arial", 9, "bold"))
        self.btn_save_st.pack(pady=5)
        # ══════════ END SUPERTONIC PANEL ══════════

        self.lbl_input_title = tk.Label(self.root, text="",
                                        bg="#1e1e2e", fg="#00d4ff")
        self.lbl_input_title.pack(anchor="w", padx=10)
        self.input_text = tk.Text(self.root, height=8, bg="#2a2a3e",
                                   fg="#e0e0e0", font=("Consolas", 11),
                                   undo=True, insertbackground="yellow")
        self.input_text.pack(fill="both", expand=True, padx=10, pady=2)
        self.setup_context_menu(self.input_text)
        self.input_text.bind("<ButtonRelease-1>", self.on_cursor_move)

        btns = tk.Frame(self.root, bg="#1e1e2e")
        btns.pack(fill="x", padx=10)
        self.btn_import = tk.Button(btns, text="", command=self.import_txt,
                                    bg="#6b8e23", fg="#fff", width=12)
        self.btn_import.pack(side="left", padx=2)
        self.btn_fix = tk.Button(btns, text="", command=self.do_convert,
                                 bg="#00d4ff", fg="#000",
                                 font=("Arial", 10, "bold"))
        self.btn_fix.pack(side="left", padx=5, expand=True, fill="x")
        self.btn_dict = tk.Button(btns, text="",
                                  command=lambda: os.startfile(self.get_fix_path()),
                                  bg="#ffcc00", fg="#000", width=10)
        self.btn_dict.pack(side="left", padx=2)
        self.btn_clear = tk.Button(btns, text="",
                                   command=lambda: self.input_text.delete("1.0", "end"),
                                   bg="#444", fg="#fff", width=12)
        self.btn_clear.pack(side="right", padx=2)

        self.lbl_output_title = tk.Label(self.root, text="",
                                         bg="#1e1e2e", fg="#00d4ff")
        self.lbl_output_title.pack(anchor="w", padx=10)
        self.output_text = tk.Text(self.root, height=8, bg="#2a2a3e",
                                   fg="#e0e0e0", font=("Consolas", 11),
                                   insertbackground="white")
        self.output_text.pack(fill="both", expand=True, padx=10, pady=2)
        self.setup_context_menu(self.output_text)
        self.output_text.bind("<ButtonRelease-1>", self.on_cursor_move)

        sbtns = tk.Frame(self.root, bg="#1e1e2e", pady=5)
        sbtns.pack(fill="x", padx=10)
        self.btn_wav = tk.Button(sbtns, text="",
                                 command=lambda: self.start_gen(False),
                                 bg="#00a896", fg="#fff",
                                 font=("Arial", 10, "bold"), height=2)
        self.btn_wav.pack(side="left", expand=True, fill="x", padx=5)
        self.btn_opus = tk.Button(sbtns, text="",
                                  command=lambda: self.start_gen(True),
                                  bg="#006b5f", fg="#fff",
                                  font=("Arial", 10, "bold"), height=2)
        self.btn_opus.pack(side="left", expand=True, fill="x", padx=5)

        self.canvas_bar = tk.Canvas(self.root, height=24, bg="#2a2a3e",
                                    highlightthickness=1,
                                    highlightbackground="#444466")
        self.canvas_bar.pack(fill="x", padx=10, pady=2)
        self.canvas_bar.bind("<Configure>",
                             lambda e: self._draw_bar(self._bar_pct))

        info_row = tk.Frame(self.root, bg="#13131f", pady=3)
        info_row.pack(fill="x", padx=10)
        self.lbl_charcount = tk.Label(info_row, text="Karakter: 0",
                                      bg="#13131f", fg="#aaaacc",
                                      font=("Consolas", 9))
        self.lbl_charcount.pack(side="left", padx=8)
        self.lbl_timer = tk.Label(info_row, text="⏱ --:--",
                                  bg="#13131f", fg="#555577",
                                  font=("Consolas", 9))
        self.lbl_timer.pack(side="right", padx=8)

        self.lbl_status = tk.Label(self.root, text="", bg="#2d2d44",
                                   fg="#00d4ff", pady=5)
        self.lbl_status.pack(fill="x", side="bottom")

        self.root.after(600, self._watch_charcount)

        # Kezdő gombállapotok beállítása
        self._on_model_change()

    def _open_dep_wizard(self):
        dep_mgr = DependencyManager()
        SetupWizard(self.root, dep_mgr, on_continue_cb=None)

    def _update_supertonic(self):
        """
        Supertonic3 modell frissítő dialógus.
        Megmutatja a jelenlegi fájlok állapotát, és lehetőséget ad
        az újratelepítésre (internethez kell).
        """
        if not SUPERTONIC_PKG_OK:
            messagebox.showinfo("Supertonic Package Missing",
                "The supertonic Python package is not installed.\n\n"
                "Solution:\n"
                "  pip install supertonic\n\nThen restart the program.")
            return

        st_ok, st_dir = find_supertonic_models()
        st_root  = get_data_path(os.path.join("models", "supertonic3"))
        onnx_dir = os.path.join(st_root, "onnx")

        # Fájlinformációk összegyűjtése
        # text_encoder.onnx és vocoder.onnx az onnx/ mappában van
        # tts.json a gyökérben VAGY az onnx/ mappában lehet
        file_infos = []
        import datetime as dt
        # Rekurzivan keresi a fajlokat
        def find_file_recursive(filename, search_root):
            for dirpath, dirnames, filenames in os.walk(search_root):
                if filename in filenames:
                    return os.path.join(dirpath, filename)
            return None

        for fname in ["text_encoder.onnx", "vocoder.onnx", "tts.json"]:
            fpath = find_file_recursive(fname, st_root)
            if fpath:
                size_mb = os.path.getsize(fpath) / (1024*1024)
                mtime = dt.datetime.fromtimestamp(os.path.getmtime(fpath))
                rel = os.path.relpath(fpath, st_root)
                file_infos.append(
                    f"  ✅ {fname}  ({rel})\n"
                    f"      Size: {size_mb:.1f} MB  |  Date: {mtime.strftime('%Y-%m-%d %H:%M')}"
                )
            else:
                file_infos.append(f"  ❌ {fname}  — NOT FOUND (searched recursively)")

        win = tk.Toplevel(self.root)
        win.title("♻ Supertonic3 Model Update")
        win.geometry("680x480")
        win.configure(bg="#1a1a2e")
        win.transient(self.root)
        win.grab_set()

        BG, FG = "#1a1a2e", "#e0e0e0"

        tk.Label(win, text="♻  Supertonic3 — Model Update / Replace",
                 bg=BG, fg="#00d4ff", font=("Arial", 11, "bold")).pack(
                 padx=15, pady=(12,4), anchor="w")

        tk.Label(win,
                 text="Supertonic3 model files (text_encoder.onnx, vocoder.onnx, tts.json)\n"
                      "are stored SEPARATELY from the EXE → replaceable and updatable without recompiling.",
                 bg=BG, fg="#aaa", font=("Arial", 9), justify="left"
                 ).pack(padx=15, pady=(0,6), anchor="w")

        tk.Frame(win, bg="#333355", height=1).pack(fill="x", padx=10)

        txt = tk.Text(win, bg="#111122", fg=FG, font=("Consolas", 9),
                      height=10, padx=10, pady=8, relief="flat", wrap="word")
        txt.pack(fill="both", expand=True, padx=10, pady=8)

        info_text = f"Model folder:\n  {st_root}\n\nCurrent files:\n"
        info_text += "\n".join(file_infos)
        info_text += "\n\n"
        if st_ok:
            info_text += "✅ All files present. Click 'Reinstall' to update."
        else:
            info_text += "❌ Missing files! Click 'Download / Install' to proceed."
        info_text += ("\n\nNote: Downloading the model requires ~305 MB of internet data.\n"
                      "To copy files manually: download only the onnx/ folder\n"
                      "from the Supertonic3 HuggingFace page and place it here.")
        txt.insert("1.0", info_text)
        txt.config(state="disabled")

        log_var = tk.StringVar(value="")
        tk.Label(win, textvariable=log_var, bg="#0a0a1a", fg="#aaffcc",
                 font=("Consolas", 8), anchor="w").pack(fill="x", padx=10, pady=(0,4))

        btn_row = tk.Frame(win, bg=BG)
        btn_row.pack(fill="x", padx=10, pady=8)

        def open_folder():
            os.makedirs(st_root, exist_ok=True)
            if sys.platform == "win32":
                os.startfile(st_root)

        def do_reinstall():
            if not messagebox.askyesno("Confirm",
                    "This will delete the existing Supertonic3 model files\n"
                    "and re-download them (~305 MB, internet required).\n\n"
                    "Continue?", parent=win):
                return
            btn_reinstall.config(state="disabled")
            log_var.set("Deleting and reinstalling… please wait!")
            win.update_idletasks()

            def _run():
                try:
                    import shutil
                    if os.path.isdir(st_root):
                        shutil.rmtree(st_root)
                    os.makedirs(st_root, exist_ok=True)

                    self.st_tts = None
                    self._st_style = None

                    st_cache = get_data_path(os.path.join("models", "supertonic3"))
                    os.environ["SUPERTONIC_CACHE_DIR"] = st_cache
                    os.environ.pop("TRANSFORMERS_OFFLINE", None)
                    os.environ.pop("HF_HUB_OFFLINE", None)
                    SupertonicTTS(auto_download=True)
                    win.after(0, lambda: _done(True, "✔ Supertonic3 successfully updated!"))
                except Exception as e:
                    win.after(0, lambda: _done(False, f"✖ Error: {e}"))

            def _done(ok, msg):
                log_var.set(msg)
                btn_reinstall.config(state="normal")
                if ok:
                    messagebox.showinfo("Done", "Supertonic3 updated!\n\n"
                        "The new model will load on next ST voice use.", parent=win)
                    win.destroy()
                else:
                    messagebox.showerror("Error", msg, parent=win)

            threading.Thread(target=_run, daemon=True).start()

        tk.Button(btn_row, text="📂 Open Folder",
                  command=open_folder, bg="#444", fg="#ddd", width=18,
                  relief="flat", pady=3).pack(side="left", padx=4)

        btn_reinstall = tk.Button(btn_row,
                  text="⬇ Reinstall (internet)" if st_ok else "⬇ Download (~305 MB)",
                  command=do_reinstall,
                  bg="#4a2070" if st_ok else "#006633", fg="#fff", width=24,
                  relief="flat", pady=3, font=("Arial", 9, "bold"))
        btn_reinstall.pack(side="left", padx=4)

        tk.Button(btn_row, text="Close", command=win.destroy,
                  bg="#333", fg="#aaa", width=10,
                  relief="flat", pady=3).pack(side="right", padx=4)

    def refresh_ui(self):
        l = LANGS.get(self.lang, LANGS["EN"])
        if hasattr(self, 'btn_settings_pp'):
            self.btn_settings_pp.config(text="⚙ Piper")
        if hasattr(self, 'btn_settings_st'):
            self.btn_settings_st.config(text="⚙ Supertronic")
        self.btn_speak.config(text=l["speak"])
        self.btn_save_mod.config(text=l["save_mod"])
        self.lbl_input_title.config(text=l["input_lbl"])
        self.lbl_output_title.config(text=l["out_lbl"])
        self.btn_import.config(text=l["import"])
        self.btn_fix.config(text=l["fix"])
        self.btn_dict.config(text=l["dict"])
        self.btn_clear.config(text=l["clear"])
        self.btn_wav.config(text=l["save_wav"])
        self.btn_opus.config(text=l["save_opus"])
        self.lbl_status.config(text=l["status_ready"])
        self.l_sp.config(text=l.get("lbl_speed",   "Speed:"))
        self.l_ns.config(text="Noise Scale:")
        self.l_nw.config(text="Noise Width:")
        self.l_si.config(text=l.get("lbl_silence", "Silence:"))
        self.l_bf.config(text=l.get("lbl_buffer",  "Buffer:"))
        self.l_op.config(text="Opus Bitrate:")

    # ────────────────────────── szám → szó konverterek ──────────────────────
    def _num_to_text_hu(self, n):
        if n == 0: return "nulla"
        ones     = ["","egy","kettő","három","négy","öt","hat","hét","nyolc","kilenc"]
        tens     = ["","tíz","húsz","harminc","negyven","ötven","hatvan","hetven","nyolcvan","kilencven"]
        tens_tie = ["","tizen","huszon","harminc","negyven","ötven","hatvan","hetven","nyolcvan","kilencven"]
        res = ""
        thousands = n // 1000; n %= 1000
        if thousands > 0:
            if thousands == 1:   res += "ezer"
            elif thousands == 2: res += "kétezer"
            else:                res += self._num_to_text_hu(thousands) + "ezer"
        hundreds = n // 100; n %= 100
        if hundreds > 0:
            if hundreds == 1:   res += "száz"
            elif hundreds == 2: res += "kétszáz"
            else:               res += ones[hundreds] + "száz"
        if n > 0:
            if n < 10: res += ones[n]
            elif n % 10 == 0: res += tens[n // 10]
            else:
                t = n // 10; o = n % 10
                if t == 1 or t == 2: res += tens_tie[t] + ones[o]
                else:                res += tens[t] + ones[o]
        return res

    def _num_to_text_en(self, n):
        n = int(n)
        if n < 0: return "minus " + self._num_to_text_en(-n)
        if n == 0: return "zero"
        _ones = ["","one","two","three","four","five","six","seven","eight","nine",
                 "ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen",
                 "seventeen","eighteen","nineteen"]
        _tens = ["","","twenty","thirty","forty","fifty","sixty","seventy","eighty","ninety"]
        res = ""
        if n >= 1000:
            th, n = divmod(n, 1000)
            res += self._num_to_text_en(th) + " thousand"
            if n: res += " "
        if n >= 100:
            h, n = divmod(n, 100)
            res += _ones[h] + " hundred"
            if n: res += " "
        if n >= 20:
            t, o = divmod(n, 10)
            res += _tens[t] + ("-" + _ones[o] if o else "")
        elif n > 0:
            res += _ones[n]
        return res.strip()

    def _num_to_text_ro(self, n):
        n = int(n)
        if n < 0: return "minus " + self._num_to_text_ro(-n)
        if n == 0: return "zero"
        _ones = ["","unu","doi","trei","patru","cinci","șase","șapte","opt","nouă",
                 "zece","unsprezece","doisprezece","treisprezece","paisprezece",
                 "cincisprezece","șaisprezece","șaptesprezece","optsprezece","nouăsprezece"]
        _tens = ["","","douăzeci","treizeci","patruzeci","cincizeci",
                 "șaizeci","șaptezeci","optzeci","nouăzeci"]
        res = ""
        if n >= 1000:
            th, n = divmod(n, 1000)
            if th == 1:   res += "o mie"
            elif th == 2: res += "două mii"
            else:         res += self._num_to_text_ro(th) + " mii"
            if n: res += " "
        if n >= 100:
            h, n = divmod(n, 100)
            if h == 1:   res += "o sută"
            elif h == 2: res += "două sute"
            else:        res += _ones[h] + " sute"
            if n: res += " "
        if n >= 20:
            t, o = divmod(n, 10)
            res += _tens[t] + (" și " + _ones[o] if o else "")
        elif n > 0:
            res += _ones[n]
        return res.strip()

    def _num_to_words(self, n):
        if   self.lang == "HU": return self._num_to_text_hu(int(n))
        elif self.lang == "EN": return self._num_to_text_en(int(n))
        elif self.lang == "RO": return self._num_to_text_ro(int(n))
        else:                   return str(int(n))

    def _get_tol_suffix_hu(self, word):
        back  = set('aáoóuú')
        front = set('eéiíöőüű')
        for ch in reversed(word.lower()):
            if ch in back:  return 'tól'
            if ch in front: return 'től'
        return 'től'

    def _detect_lang_from_model(self, model_name):
        if not model_name or model_name.startswith("ST: "):
            return None
        m = re.match(r'^([a-z]{2})_[A-Z]{2}', model_name)
        if m: return m.group(1).upper()
        low = model_name.lower()
        for kw, code in [('-hu-','HU'),('_hu_','HU'),('-en-','EN'),('_en_','EN'),
                         ('-ro-','RO'),('_ro_','RO'),('-de-','DE'),('_de_','DE'),
                         ('-fr-','FR'),('_fr_','FR'),('-es-','ES'),('_es_','ES'),
                         ('-pl-','PL'),('_pl_','PL')]:
            if kw in low: return code
        return None

    # ─────────────────────────── keresés / csere ────────────────────────────
    def open_search(self, widget=None):
        if self._search_win and self._search_win.winfo_exists():
            self._search_win.lift(); self._search_win.focus_force(); return
        self._search_widget = widget or self.output_text
        win = tk.Toplevel(self.root)
        win.title("Keresés / Csere")
        win.geometry("460x170")
        win.configure(bg="#1e1e2e")
        win.resizable(False, False)
        win.transient(self.root)
        self._search_win = win
        def on_close():
            try: self._search_widget.tag_remove("search_hl", "1.0", "end")
            except Exception: pass
            win.destroy(); self._search_win = None
        win.protocol("WM_DELETE_WINDOW", on_close)
        sw_frame = tk.Frame(win, bg="#1e1e2e"); sw_frame.pack(fill="x", padx=10, pady=(8,2))
        tk.Label(sw_frame, text="Szövegmező:", bg="#1e1e2e", fg="#aaa", font=("Arial",8)).pack(side="left")
        tk.Button(sw_frame, text="↑ Bemenet", bg="#444", fg="#fff", font=("Arial",8), relief="flat",
                  command=lambda: self._set_search_widget(self.input_text, win)).pack(side="left", padx=4)
        tk.Button(sw_frame, text="↓ Kimenet", bg="#444", fg="#fff", font=("Arial",8), relief="flat",
                  command=lambda: self._set_search_widget(self.output_text, win)).pack(side="left", padx=2)
        row1 = tk.Frame(win, bg="#1e1e2e"); row1.pack(fill="x", padx=10, pady=3)
        tk.Label(row1, text="Keresés:", bg="#1e1e2e", fg="#ccc", width=9, anchor="e").pack(side="left")
        e_find = tk.Entry(row1, width=30, bg="#2a2a3e", fg="#fff", insertbackground="white")
        e_find.pack(side="left", padx=4); e_find.focus_set()
        lbl_result = tk.Label(row1, text="", bg="#1e1e2e", fg="#ffcc00", font=("Consolas",8))
        lbl_result.pack(side="left", padx=4)
        row2 = tk.Frame(win, bg="#1e1e2e"); row2.pack(fill="x", padx=10, pady=3)
        tk.Label(row2, text="Csere:", bg="#1e1e2e", fg="#ccc", width=9, anchor="e").pack(side="left")
        e_replace = tk.Entry(row2, width=30, bg="#2a2a3e", fg="#fff", insertbackground="white")
        e_replace.pack(side="left", padx=4)
        btn_row = tk.Frame(win, bg="#1e1e2e"); btn_row.pack(pady=6)
        def do_find(start="1.0"):
            term = e_find.get()
            if not term: return None
            w = self._search_widget
            w.tag_remove("search_hl","1.0","end")
            w.tag_config("search_hl", background="#ffcc00", foreground="#000")
            pos="1.0"; count=0; first=None
            while True:
                idx = w.search(term, pos, stopindex="end", nocase=True)
                if not idx: break
                end_idx = f"{idx}+{len(term)}c"
                w.tag_add("search_hl", idx, end_idx)
                if first is None: first = idx
                count += 1; pos = end_idx
            if count:
                lbl_result.config(text=f"{count} találat", fg="#00ff88")
                if first: w.see(first)
            else:
                lbl_result.config(text="Nem található", fg="#ff6666")
            return count
        def do_replace_next():
            term=e_find.get(); repl=e_replace.get()
            if not term: return
            w=self._search_widget
            idx = w.search(term,"insert",stopindex="end",nocase=True)
            if not idx: idx = w.search(term,"1.0",stopindex="end",nocase=True)
            if idx:
                end_idx=f"{idx}+{len(term)}c"; w.delete(idx,end_idx)
                w.insert(idx,repl); w.mark_set("insert",f"{idx}+{len(repl)}c"); do_find()
        def do_replace_all():
            term=e_find.get(); repl=e_replace.get()
            if not term: return
            w=self._search_widget; content=w.get("1.0","end-1c")
            new_content=re.sub(re.escape(term),repl,content,flags=re.IGNORECASE)
            n=len(re.findall(re.escape(term),content,re.IGNORECASE))
            w.delete("1.0","end"); w.insert("1.0",new_content)
            lbl_result.config(text=f"{n} csere megtörtént", fg="#00ff88")
        tk.Button(btn_row, text="Keresés",    bg="#3d7bd9", fg="#fff", width=10, command=do_find).pack(side="left", padx=3)
        tk.Button(btn_row, text="Csere",      bg="#8a2be2", fg="#fff", width=10, command=do_replace_next).pack(side="left", padx=3)
        tk.Button(btn_row, text="Mind csere", bg="#b05000", fg="#fff", width=10, command=do_replace_all).pack(side="left", padx=3)
        tk.Button(btn_row, text="Bezár",      bg="#444",    fg="#fff", width=7,  command=on_close).pack(side="left", padx=3)
        e_find.bind("<Return>", lambda e: do_find())
        e_find.bind("<Escape>", lambda e: on_close())

    def _set_search_widget(self, widget, win):
        self._search_widget = widget
        win.title(f"Keresés – {'Bemenet' if widget==self.input_text else 'Kimenet'}")

    # ──────────────────────────── progress bar ──────────────────────────────
    def _draw_bar(self, pct, color="#00d4ff"):
        try:
            self.canvas_bar.delete("all")
            w = self.canvas_bar.winfo_width()
            h = self.canvas_bar.winfo_height()
            if w < 2: return
            fill_w = max(0, int(w * pct / 100))
            if fill_w > 0:
                self.canvas_bar.create_rectangle(0,0,fill_w,h, fill=color, outline="")
            if pct > 0:
                self.canvas_bar.create_text(w//2, h//2, text=f"{int(pct)}%",
                                            fill="#ffffff", font=("Consolas",9,"bold"))
        except Exception: pass

    def _bar_start_indeterminate(self):
        self._bar_pct=0; self._bar_anim_dir=1; self._bar_anim_running=True; self._anim_step()
    def _anim_step(self):
        if not self._bar_anim_running: return
        self._bar_pct += self._bar_anim_dir * 3
        if self._bar_pct >= 100: self._bar_pct=100; self._bar_anim_dir=-1
        elif self._bar_pct <= 0: self._bar_pct=0;   self._bar_anim_dir=1
        self._draw_bar(self._bar_pct, color="#8a2be2")
        self._bar_anim_id = self.root.after(40, self._anim_step)
    def _bar_stop(self):
        self._bar_anim_running = False
        if self._bar_anim_id:
            try: self.root.after_cancel(self._bar_anim_id)
            except Exception: pass
            self._bar_anim_id = None
        self._bar_pct = 0; self._draw_bar(0)
    def _bar_set(self, pct):
        self._bar_pct = max(0, min(100, pct))
        self._draw_bar(self._bar_pct, color="#00d4ff")

    # ──────────────────────────── timer / charcount ─────────────────────────
    def _watch_charcount(self):
        try:
            if not self._timer_running:
                txt   = self.output_text.get("1.0","end-1c")
                count = len(txt)
                if count > 0:
                    self.lbl_charcount.config(
                        text=f"Karakter: {count:,}".replace(",","\u00a0"), fg="#00d4ff")
                else:
                    self.lbl_charcount.config(text="Karakter: 0", fg="#aaaacc")
        except Exception: pass
        self.root.after(500, self._watch_charcount)

    def _start_conv_timer(self):
        self._conv_start_time = time.time(); self._timer_running = True
        total = getattr(self, "_total_chars", 0)
        self.lbl_charcount.config(
            text=f"⬇ {total:,}".replace(",","\u00a0"), fg="#ffaa00")
        self.lbl_timer.config(text="⏱ 00:00", fg="#ffcc00")
        self._tick_timer()
    def _tick_timer(self):
        if not getattr(self, "_timer_running", False): return
        elapsed = time.time() - self._conv_start_time
        self.lbl_timer.config(
            text=f"⏱ {int(elapsed)//60:02d}:{int(elapsed)%60:02d}", fg="#ffcc00")
        self.root.after(1000, self._tick_timer)
    def _stop_conv_timer(self, success=True):
        self._timer_running = False
        if success:
            self.lbl_charcount.config(text="✔ 0 karakter maradt", fg="#00ff88")
            if self._conv_start_time:
                elapsed = time.time() - self._conv_start_time
                self.lbl_timer.config(
                    text=f"✔ Kész: {int(elapsed)//60:02d}:{int(elapsed)%60:02d}",
                    fg="#00ff88")

    # ───────────────────────── modell / lang váltás ──────────────────────────
    def _on_model_change(self):
        self.tts = None; self._st_style = None
        m        = self.model_var.get()
        detected = self._detect_lang_from_model(m)
        if detected and detected != self.lang:
            self.lang = detected
            if hasattr(self, 'btn_lang'): self.btn_lang.config(text=detected)
            if hasattr(self, 'lbl_status'):
                self.lbl_status.config(
                    text=f"🌐 Nyelv auto-detektálva: {detected}  (javitasok_{detected}.txt)",
                    fg="#aaffcc")
            self.refresh_ui()
        elif hasattr(self, 'lbl_status'):
            ikon = "🎙" if self._is_supertonic(m) else "🔊"
            self.lbl_status.config(text=f"{ikon} Hang váltás: {m}", fg="#ffcc00")

        # Piper / Supertonic gombok állapota
        if hasattr(self, 'btn_settings_pp') and hasattr(self, 'btn_settings_st'):
            if self._is_supertonic(self.model_var.get()):
                self.btn_settings_pp.config(state="disabled")
                self.btn_settings_st.config(state="normal")
                if getattr(self, 'settings_visible', False):
                    self.sett_pnl.pack_forget()
                    self.settings_visible = False
                if getattr(self, 'settings_visible_st', False):
                    self._load_supertonic_settings()
            else:
                self.btn_settings_pp.config(state="normal")
                self.btn_settings_st.config(state="disabled")
                if getattr(self, 'settings_visible_st', False):
                    self.sett_pnl_st.pack_forget()
                    self.settings_visible_st = False


    def toggle_settings_st(self):
        """Supertonic beállítások inline panel ki/be kapcsolása."""
        if not self._is_supertonic(self.model_var.get()):
            messagebox.showinfo("Supertonic",
                "Ez a panel csak Supertonic (ST:) hangoknál érhető el."
                "Válassz egy 'ST: …' hangot a legördülő listából.")
            return
        if self.settings_visible:
            self.sett_pnl.pack_forget()
            self.settings_visible = False
        if self.settings_visible_st:
            self.sett_pnl_st.pack_forget()
            self.settings_visible_st = False
        else:
            self._load_supertonic_settings()
            self.sett_pnl_st.pack(fill="x", padx=10, pady=5,
                                  before=self.lbl_input_title)
            self.settings_visible_st = True

    def _load_supertonic_settings(self):
        """Betölti a kiválasztott ST hang beállításait a panelba."""
        cfg = self._get_st_config()
        current = self.model_var.get()
        self.lbl_st_current.config(text=f"Current voice:  {current}")
        try:
            self.scale_st_speed.set(float(cfg["speed"]))
        except Exception:
            self.scale_st_speed.set(1.0)
        self.lbl_st_speed_val.config(
            text=f"{float(self.scale_st_speed.get()):.2f}x")
        self.e_st_silence.delete(0, "end")
        self.e_st_silence.insert(0, str(cfg["silence"]))
        self.e_st_opus.delete(0, "end")
        self.e_st_opus.insert(0, str(cfg["opus"]))
        self.e_st_buffer.delete(0, "end")
        self.e_st_buffer.insert(0, str(cfg["buffer"]))

    def save_supertonic_settings(self):
        """Elmenti a Supertonic panel értékeit a modellhez tartozó JSON-ba."""
        current = self.model_var.get()
        if not self._is_supertonic(current):
            messagebox.showwarning("Hiba",
                "Nem Supertonic hang van kiválasztva.")
            return
        try:
            settings = {
                "speed":   float(self.scale_st_speed.get()),
                "silence": float(self.e_st_silence.get() or 0.5),
                "opus":    self.e_st_opus.get().strip() or "--bitrate 64",
                "buffer":  int(self.e_st_buffer.get() or 4096),
            }
        except ValueError as e:
            messagebox.showerror("Érvénytelen érték", f"Hibás szám: {e}")
            return
        model_base = os.path.splitext(current)[0]
        path = get_data_path(os.path.join("models", model_base + "_st.json"))
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            
            if self.settings_visible_st:
                self.sett_pnl_st.pack_forget()
                self.settings_visible_st = False
            
            # ITT A JAVÍTÁS:
            msg = (f"Beállítások mentve a(z) '{current}' hanghoz!\n"
                   f"→ {os.path.basename(path)}")
            
            messagebox.showinfo("Siker", msg)
            
        except Exception as e:
            messagebox.showerror("Hiba", f"Mentés sikertelen: {e}")

    def _get_st_config(self):
        """Visszaadja az aktuális ST hang beállításait (JSON vagy default)."""
        cfg = {"speed": 1.0, "silence": 0.5,
               "opus": "--bitrate 64", "buffer": 4096}
        current = self.model_var.get()
        if not self._is_supertonic(current):
            return cfg
        model_base = os.path.splitext(current)[0]
        path = get_data_path(os.path.join("models", model_base + "_st.json"))
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cfg["speed"]   = float(data.get("speed",   cfg["speed"]))
                cfg["silence"] = float(data.get("silence", cfg["silence"]))
                cfg["opus"]    = str(data.get("opus",      cfg["opus"]))
                cfg["buffer"]  = int(data.get("buffer",    cfg["buffer"]))
            except Exception:
                pass
        return cfg


    def toggle_lang(self):
        cycle = {"HU":"EN","EN":"RO","RO":"HU"}
        self.lang = cycle.get(self.lang,"HU")
        self.btn_lang.config(text=self.lang)
        search_key = self.lang.lower()
        for m in self.models:
            if search_key in m.lower():
                self.model_var.set(m); break
        self.refresh_ui()
        if hasattr(self,'lbl_status'):
            self.lbl_status.config(
                text=f"🌐 Nyelv: {self.lang}  |  szám→szó ✓  |  javitasok_{self.lang}.txt",
                fg="#00d4ff")

    def toggle_settings(self):
        # Bezárjuk a ST panelt, ha nyitva van
        if getattr(self, 'settings_visible_st', False):
            self.sett_pnl_st.pack_forget()
            self.settings_visible_st = False
        if self.settings_visible:
            self.sett_pnl.pack_forget()
        else:
            self.sett_pnl.pack(fill="x", padx=10, pady=5,
                               before=self.lbl_input_title)
        self.settings_visible = not self.settings_visible

    def save_model_settings(self):
        settings = {"speed":self.e_speed.get(),"n_scale":self.e_nscale.get(),
                    "n_w":self.e_nw.get(),"silence":self.e_silence.get(),
                    "opus":self.e_opus.get()}
        model_base = os.path.splitext(self.model_var.get())[0]
        path = get_data_path(os.path.join("models", model_base+".json"))
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
            self.tts = None
            if hasattr(self,'settings_visible') and self.settings_visible:
                self.toggle_settings()
            messagebox.showinfo("Siker", "Beállítások mentve és alkalmazva!")
        except Exception as e:
            messagebox.showerror("Hiba", f"Mentés sikertelen: {e}")

    def setup_context_menu(self, widget):
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Cut",    command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy",   command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste",  command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All",
                         command=lambda: widget.tag_add("sel","1.0","end"))
        menu.add_separator()
        menu.add_command(label="🔍 Keresés / Csere  (Ctrl+F)",
                         command=lambda: self.open_search(widget))
        widget.bind("<Button-3>",   lambda e: menu.post(e.x_root, e.y_root))
        widget.bind("<Button-1>",   lambda e: widget.focus_set())
        widget.bind("<Control-f>",  lambda e: self.open_search(widget))

    def import_txt(self):
        f = filedialog.askopenfilename(
            filetypes=[("Text fájl","*.txt"),("Minden fájl","*.*")])
        if f:
            with open(f,"r",encoding="utf-8",errors="ignore") as fh:
                self.input_text.delete("1.0","end")
                self.input_text.insert("1.0",fh.read())

    # ──────────────────────────── szöveg javítás ────────────────────────────
    def do_convert(self):
        text = self.input_text.get("1.0","end-1c").strip()
        if not text: return
        bad_chars = {'õ':'ő','û':'ű','Õ':'Ő','Û':'Ű'}
        for old_c, new_c in bad_chars.items():
            text = text.replace(old_c, new_c)
        text = re.sub(r'[„""]\s*\.{2,4}','',text)
        text = re.sub(r'[„""\u2018\u2019`\u00b4"\']','',text)
        text = re.sub(r'[#\*\_\[\]\(\)\{\}]','',text)
        text = text.replace('—',' ')
        fixes = {}
        path = self.get_fix_path()
        if os.path.exists(path):
            with open(path,"r",encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if ":" in line and not line.startswith("#"):
                        parts = line.split(":",1)
                        fixes[parts[0].strip()] = parts[1].strip()
        for book_key in list(fixes.keys()):
            m_abbr = re.match(r'^(\d+)\s*(.+)$', book_key)
            if m_abbr:
                num_part  = m_abbr.group(1)
                text_part = m_abbr.group(2).strip()
                if text_part:
                    text = re.sub(
                        rf'(?<!\w){re.escape(num_part)}\s+{re.escape(text_part)}(?!\w)',
                        book_key, text)
        def bible_replace(match):
            book_key, chapter, v_start, trail_letter, _sep, v_end = match.groups()
            full_book_name = fixes.get(book_key, book_key)
            trail_suffix   = (", "+trail_letter) if trail_letter else ""
            if self.lang == "HU":
                ch_word = self._num_to_text_hu(int(chapter))
                vs_word = self._num_to_text_hu(int(v_start))
                res = f"{full_book_name} {ch_word}, {vs_word}{trail_suffix}"
                if v_end:
                    ve_word = self._num_to_text_hu(int(v_end))
                    tol     = self._get_tol_suffix_hu(vs_word)
                    return f"{full_book_name} {ch_word}, {vs_word}{tol} {ve_word}ig"
                return res
            elif self.lang == "EN":
                ch_word = self._num_to_text_en(int(chapter))
                vs_word = self._num_to_text_en(int(v_start))
                res = f"{full_book_name} {ch_word}, {vs_word}{trail_suffix}"
                if v_end:
                    ve_word = self._num_to_text_en(int(v_end))
                    return f"{full_book_name} {ch_word}, {vs_word} through {ve_word}"
                return res
            elif self.lang == "RO":
                ch_word = self._num_to_text_ro(int(chapter))
                vs_word = self._num_to_text_ro(int(v_start))
                res = f"{full_book_name} {ch_word}, {vs_word}{trail_suffix}"
                if v_end:
                    ve_word = self._num_to_text_ro(int(v_end))
                    return f"{full_book_name} {ch_word}, {vs_word} până la {ve_word}"
                return res
            else:
                if v_end: return f"{full_book_name} {chapter}:{v_start}-{v_end}"
                return f"{full_book_name} {chapter}:{v_start}{trail_suffix}"

        short_names = [re.escape(k) for k in fixes.keys() if len(k) >= 2]
        if short_names:
            books_re = "|".join(short_names)
            def chain_fix(match):
                book    = match.group(1)
                content = match.group(2)
                fixed   = re.sub(rf';\s*(?=\d+[,:])', f'; {book} ', content)
                return f"{book} {fixed}"
            chain_pat = rf'(?<![A-Za-záéíóöőúüűÁÉÍÓÖŐÚÜŰ])({books_re})\s+([\d][,:.\ \d\s;–\-]+?)(?=[.!?\n]|$)'
            text = re.sub(chain_pat, chain_fix, text, flags=re.MULTILINE)
            pattern = rf'(?<![A-Za-záéíóöőúüűÁÉÍÓÖŐÚÜŰ])({books_re})\s+(\d+)[,:]\s*(\d+)([a-z]?)(?:\s*([-–—])\s*(\d+))?'
            text = re.sub(pattern, bible_replace, text)
            szamszavak_pat = (
                r'((?:nulla|egy|kettő|három|négy|öt|hat|hét|nyolc|kilenc|tíz|tizenegy|tizenkettő|tizenhárom|'
                r'tizennégy|tizenöt|tizenhat|tizenhét|tizennyolc|tizenkilenc|húsz|huszon\w+|harminc\w*|'
                r'negyven\w*|ötven\w*|hatvan\w*|hetven\w*|nyolcvan\w*|kilencven\w*|száz\w*|ezer\w*|\w+ig|\w+tól|\w+től))'
                r'(?=[ ]+[A-ZÁÉÍÓÖŐÚÜŰ])')
            text = re.sub(szamszavak_pat, lambda m: m.group(0)+',', text)
        # ── Segédfüggvény: tisztán betűs Bibliai rövidítés-e? (pl. Ez, Jer, Jn) ──
        # Ezeket CSAK szám szomszédságában cseréljük, nehogy pl. "Ez" (ez a szó)
        # Ezékiellé változzon, vagy "Ex" Exodussá, "Job" Jóbbá stb.
        _LETTER_ONLY = re.compile(
            r'^[A-Za-záéíóöőúüűÁÉÍÓÖŐÚÜŰ]{2,}$'
        )
        def _is_bible_only_abbr(key):
            """Igaz, ha a rövidítés csak betűkből áll (nincs benne pont vagy szám)."""
            return bool(_LETTER_ONLY.match(key))

        for old in sorted(fixes.keys(), key=len, reverse=True):
            val = fixes[old]

            if _is_bible_only_abbr(old):
                # ── Bibliai könyv rövidítés (pl. Ez, Jer, Én, Ex, Job, Rev) ──
                # Csak akkor cseréljük, ha KÖZVETLENÜL szám van utána (esetleg szóközzel),
                # VAGY az előző karakter szám (pl. "1 Ez" normalizálás után).
                #
                # Elfogadott minták (HU/RO/EN):
                #   Ez 2         → Ezékiel 2
                #   Ez 2,5       → már bible_replace kezeli, de biztonság kedvéért:
                #   Ez2          → Ezékiel 2  (szóköz nélkül, ritka de előfordul)
                #   1 Ez         → az elő-normalizálás után ez "1Ez" lesz
                #
                # NEM cseréljük:
                #   "Ez a mondat"   → marad "Ez"
                #   "Ex-presidente" → marad "Ex"
                #   "Job description"→ marad "Job"
                text = re.sub(
                    rf'(?<!\w){re.escape(old)}(?=\s*\d)',   # utána (szóközzel is) szám
                    val, text
                )
            elif len(old) == 1:
                text = re.sub(rf'(?<!\d){re.escape(old)}(?!\d)', val, text)
            elif re.search(r'\w', old):
                if old.endswith('.'):
                    text = re.sub(rf'\b{re.escape(old)}(?![\w])', val, text)
                else:
                    text = re.sub(rf'\b{re.escape(old)}\b', val, text)
            else:
                text = text.replace(old, val)
        if self.lang in ("HU","EN","RO"):
            def replace_remaining(m):
                try:
                    val = int(m.group(0))
                    if 0 <= val <= 999999:
                        return self._num_to_words(val)
                except Exception: pass
                return m.group(0)
            text = re.sub(r'(?<![.,\d])(\d+)(?![.,]\d)(?!\d)', replace_remaining, text)
        self.output_text.delete("1.0","end")
        self.output_text.insert("1.0",text)

    # ──────────────────────────── STOP ──────────────────────────────────────
    def stop_all(self):
        if hasattr(self,'stop_event'): self.stop_event.set()
        if SD_OK: sd.stop()
        self.is_speaking = False
        self._stop_conv_timer(success=False)
        self._bar_stop()
        self._clear_all_highlights()
        if hasattr(self,'lbl_status'):
            self.lbl_status.config(text="LEÁLLÍTVA / STOPPED", fg="red")

    def on_cursor_move(self, event):
        if self.is_speaking:
            self.root.after(10, self.quick_speak)

    # ──────────────────────────── gyors felolvasás ──────────────────────────
    def quick_speak(self):
        if not SD_OK or not SHERPA_OK or not NUMPY_OK:
            messagebox.showwarning("Hiányzó csomagok",
                "Telepítsd a hiányzó csomagokat!\nProgram → Függőségek ellenőrzése")
            return
        if self.is_speaking:
            self.stop_all(); self.root.after(50, self.quick_speak); return
        selected = self.model_var.get()
        if self._is_supertonic(selected):
            if not self.init_supertonic(): return
        else:
            if self.tts is None:
                if not self.init_sherpa(): return
        target_widget = self.root.focus_get()
        if target_widget not in [self.input_text, self.output_text]:
            target_widget = (self.output_text
                             if self.output_text.get("1.0",tk.END).strip()
                             else self.input_text)
        text = target_widget.get("1.0",tk.END).strip()
        if not text: return
        sentences = [s.strip() for s in re.split(r'(?<=[.!?…])\s+', text) if s.strip()]
        cursor_pos = target_widget.index(tk.INSERT)
        if target_widget.compare(cursor_pos,">=",target_widget.index("end-1c")):
            start_idx = 0
        else:
            start_idx = 0; curr_ptr = "1.0"
            for i, s in enumerate(sentences):
                found = target_widget.search(s, curr_ptr, stopindex=tk.END)
                if found:
                    if target_widget.compare(cursor_pos,">=",found): start_idx = i
                    curr_ptr = target_widget.index(f"{found} + {len(s)} chars")
        self.stop_event = threading.Event()
        self.is_speaking = True
        audio_queue = queue.Queue(maxsize=5)
        use_st  = self._is_supertonic(selected)
        st_lang = "hu" if self.lang == "HU" else "en"
        def producer():
            for i in range(start_idx, len(sentences)):
                if self.stop_event.is_set(): break
                try:
                    if use_st:
                        if self._st_style is None:
                            self.init_supertonic()
                        st_cfg = self._get_st_config()
                        wav, _ = self.st_tts.synthesize(
                            sentences[i],
                            voice_style=self._st_style,
                            lang=st_lang,
                            speed=float(st_cfg["speed"])
                        )
                        sr = getattr(self.st_tts,'sample_rate',24000)
                        samples = wav.flatten().tolist() if hasattr(wav,'flatten') else list(wav)
                        audio_queue.put((samples,sr,i,sentences[i]))
                    else:
                        audio = self.tts.generate(sentences[i])
                        if audio and audio.samples:
                            audio_queue.put((audio.samples,audio.sample_rate,i,sentences[i]))
                except Exception as e:
                    print(f"Producer hiba ({i}): {e}")
            audio_queue.put(None)
        def consumer():
            while not self.stop_event.is_set():
                try:
                    item = audio_queue.get(timeout=0.1)
                    if item is None: break
                    samples, rate, gen_id, s_text = item
                    self.root.after(0, lambda w=target_widget,t=s_text:
                                    self._apply_highlight(w,t))
                    pct = int(((gen_id+1)/len(sentences))*100)
                    self.root.after(0, lambda p=pct, idx=gen_id: [
                        self._bar_set(p),
                        self.lbl_status.config(
                            text=f"Olvasás: {idx+1}/{len(sentences)}", fg="lightgreen")])
                    sd.play(np.array(samples,dtype=np.float32), samplerate=rate)
                    sd.wait()
                except: continue
            self.is_speaking = False
            self.root.after(0, lambda: [self._clear_all_highlights(), self._bar_stop()])
        threading.Thread(target=producer, daemon=True).start()
        threading.Thread(target=consumer, daemon=True).start()

    def _apply_highlight(self, widget, s_text):
        self._clear_all_highlights()
        start_pos = widget.search(s_text, "1.0", stopindex=tk.END)
        if start_pos:
            end_pos = widget.index(f"{start_pos} + {len(s_text)} chars")
            widget.tag_add("active_sentence", start_pos, end_pos)
            widget.tag_config("active_sentence", background="yellow", foreground="black")
            widget.see(start_pos)

    def _clear_all_highlights(self):
        try:
            self.input_text.tag_remove("active_sentence","1.0",tk.END)
            self.output_text.tag_remove("active_sentence","1.0",tk.END)
        except: pass

    def _highlight_sentence(self, widget, full_text):
        self._clear_highlight()
        start_pos = widget.search(full_text,"1.0",stopindex=tk.END)
        if start_pos:
            end_pos = widget.index(f"{start_pos} + {len(full_text)} chars")
            widget.tag_add("active_sentence",start_pos,end_pos)
            widget.tag_config("active_sentence",background="#4a4a00",foreground="yellow")
            widget.see(start_pos)

    def _clear_highlight(self):
        try: self.output_text.tag_remove(self._hl_tag,"1.0","end")
        except Exception: pass

    # ──────────────────────────── fájl generálás ────────────────────────────
    def start_gen(self, is_opus):
        if not SHERPA_OK or not NUMPY_OK:
            messagebox.showwarning("Hiányzó csomagok",
                "Program → Függőségek ellenőrzése")
            return
        txt = self.output_text.get("1.0","end-1c").strip()
        if not txt:
            messagebox.showwarning("Warning","Üres a kimeneti mező! Kattints a JAVÍTÁS-ra.")
            return
        if is_opus:
            opus_exe = find_opusenc()
            if not opus_exe:
                if messagebox.askyesno("opusenc.exe hiányzik",
                        "Az opusenc.exe nincs meg — OPUS mentés nem lehetséges.\n\n"
                        "Megnyissuk a Függőségek ablakot a letöltéshez?"):
                    self._open_dep_wizard()
                return
        selected = self.model_var.get()
        if self._is_supertonic(selected):
            if not self.init_supertonic(): return
        else:
            if not self.init_sherpa(): return
        self._total_chars = len(txt)
        self.lbl_charcount.config(
            text=f"Karakter: {self._total_chars:,}".replace(",","\u00a0"), fg="#00d4ff")
        self._start_conv_timer()
        threading.Thread(target=self.gen_proc, args=(txt,is_opus), daemon=True).start()

    def gen_proc(self, txt, is_opus):
        if hasattr(self,'stop_event'): self.stop_event.clear()
        try:
            self.root.after(0, lambda: self.lbl_status.config(
                text=LANGS[self.lang]["status_gen"], fg="yellow"))
            ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir  = get_data_path("output_audio")
            wav_path = os.path.join(out_dir, f"audio_{ts}.wav")
            sentences   = [s.strip() for s in re.split(r'(?<=[.!?…])\s+',txt) if s.strip()]
            all_samples = []
            sample_rate = 22050
            use_st  = self._is_supertonic(self.model_var.get())
            st_lang = "hu" if self.lang == "HU" else "en"
            max_p   = 80 if is_opus else 100
            for i, s in enumerate(sentences):
                if hasattr(self,'stop_event') and self.stop_event.is_set(): return
                if use_st:
                    if self._st_style is None:
                        self.init_supertonic()
                    st_cfg = self._get_st_config()
                    wav, _ = self.st_tts.synthesize(
                        s,
                        voice_style=self._st_style,
                        lang=st_lang,
                        speed=float(st_cfg["speed"])
                    )
                    sample_rate = getattr(self.st_tts, 'sample_rate', 24000)
                    samples = wav.flatten().tolist() if hasattr(wav, 'flatten') else list(wav)
                    all_samples.extend(samples)
                    silence_sec = float(st_cfg["silence"])
                else:
                    audio = self.tts.generate(s)
                    if audio and audio.samples:
                        all_samples.extend(audio.samples)
                        sample_rate = audio.sample_rate
                    silence_sec = float(self.e_silence.get() or 0.5)
                all_samples.extend([0.0] * int(sample_rate * silence_sec))
                pct       = int(((i+1)/len(sentences))*max_p)
                remaining = max(0, self._total_chars-int(self._total_chars*(i+1)/len(sentences)))
                self.root.after(0, lambda p=pct, r=remaining: [
                    self._bar_set(p),
                    self.lbl_charcount.config(
                        text=f"⬇ {r:,}".replace(",","\u00a0"), fg="#ffaa00")])
            audio_np    = np.array(all_samples, dtype=np.float32)
            audio_int16 = (audio_np*32767).clip(-32768,32767).astype(np.int16)
            with wave.open(wav_path,'w') as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sample_rate)
                wf.writeframes(audio_int16.tobytes())
            final_path = wav_path
            if is_opus:
                self.root.after(0, lambda: [
                    self.lbl_status.config(text="Opus kódolás...", fg="#ffaa00"),
                    self._bar_set(85)])
                opus_path = wav_path.replace(".wav", ".opus")
                opus_exe = find_opusenc()
                if use_st:
                    opus_args = self._get_st_config()["opus"].split()
                else:
                    opus_args = self.e_opus.get().split()
                subprocess.run(
                    [opus_exe] + opus_args + [wav_path, opus_path],
                    check=True, creationflags=CREATE_NO_WINDOW)
                if os.path.exists(wav_path): os.remove(wav_path)
                final_path = opus_path
            self.root.after(0, lambda p=final_path: [
                self._stop_conv_timer(success=True),
                self._bar_set(100),
                self.lbl_status.config(
                    text=f"KÉSZ: {os.path.basename(p)}", fg="lightgreen"),
                os.startfile(os.path.dirname(p))])
        except Exception as e:
            self.root.after(0, lambda msg=str(e): self._show_error("Hiba",msg))
            self.root.after(0, lambda: self._stop_conv_timer(success=False))

    # ──────────────────────────── help / about ──────────────────────────────
    def show_help(self):
        h_win = tk.Toplevel(self.root)
        h_win.title("HELP / SÚGÓ")
        h_win.geometry("850x800")
        h_win.configure(bg="#1e1e2e")
        if self.lang == "HU":
            h_txt = ("HASZNÁLATI ÚTMUTATÓ (HU) - v1.3 PORTABLE\n"
                     "==================================================\n\n"
                     "1. SZÖVEG BEVITELE ÉS GYORSBILLENTYŰK\n"
                     "   - Másolás/Beillesztés: Ctrl+C / Ctrl+V vagy Jobb gomb.\n"                  
                     "   - Importálás: Az 'Import .txt' gombbal tölthetsz be fájlokat.\n\n"
                     "2. JAVÍTÁS ÉS KONVERTÁLÁS\n"
                     "   - A kék gomb (JAVÍTÁS) felkészíti a szöveget a felolvasásra.\n"
                     "   - Kicseréli a rövidítéseket és Bibliai hivatkozásokat stb.\n"
                     "   - Magyar/Angol/Román nyelven a számokat szavakká alakítja!\n"
                     "   - Javitás nélküli konvertálásra használd Kimeneti szövegrészt.\n\n"
                     "3. HORDOZHATÓ MÓD (PENDRIVE)\n"
                     "   - A program mappáját teljes egészében átmásolhatod pendrive-ra.\n"
                     "   - Tartalmazza: models/, opusenc.exe, javitasok_*.txt fájlokat.\n"
                     "   - Internet nélkül is teljes mértékben működik!\n\n"
                     "4. HIÁNYZÓ KOMPONENSEK\n"
                     "   - A program két tipusu hangmodelt használ: Piper és Supertonic\n"
                     "   - Program → Függőségek ellenőrzése megnyitásával\n"
                     "     letöltheted a hiányzó modelleket, opusenc.exe-t stb.\n\n"
                     "5. MODELLEK LETÖLTÉSE\n"
                     "   - Piper TTS modellek: https://huggingface.co/rhasspy/piper-voices\n"
                     "   - A .onnx és .onnx.json fájlokat másold a models/ mappába.\n\n"
                     "6. INTELLIGENS FUNKCIÓK\n"
                     "   - Kattintásra ugrás: Felolvasás közben kattints bármelyik\n"
                     "     mondatra, és a program azonnal onnan folytatja!\n"
                     "   - STOP: Megállítja a felolvasást ÉS a fájlmentést is.\n\n"
                     "7. KIMENETI FORMÁTUMOK\n"
                     "   - WAV: Legjobb minőség / OPUS: Kis méret, jó minőség.\n\n"
                     "Soli Deo Gloria")
        else:
            h_txt = ("USER GUIDE (EN) - v1.3 PORTABLE\n"
                     "==================================================\n\n"
                     "1. TEXT INPUT & HOTKEYS\n"
                     "   - Copy/Paste: Ctrl+C / Ctrl+V or Right-click.\n"
                     "   - Import: Load .txt files via the 'Import .txt' button.\n\n"
                     "2. FIX & CONVERT\n"
                     "   - Blue button (FIX): Prepares text for speech.\n"
                     "   - Expands abbreviations and formats Bible verses.\n"
                     "   - Converts numbers to words for HU/EN/RO!\n"
                     "   - Use the Output section for conversion without correction.\n\n"
                     "3. PORTABLE MODE (USB DRIVE)\n"
                     "   - Copy the entire program folder to a USB drive.\n"
                     "   - Include: models/, opusenc.exe, javitasok_*.txt files.\n"
                     "   - Works completely offline!\n\n"
                     "4. MISSING COMPONENTS\n"
                     "   - The program uses two types of voice models: Piper and Supertonic.\n"
                     "   - Open Program → Dependencies to download missing\n"
                     "     models, opusenc.exe, etc.\n\n"
                     "5. DOWNLOADING MODELS\n"
                     "   - Piper TTS voices: https://huggingface.co/rhasspy/piper-voices\n"
                     "   - Copy .onnx and .onnx.json files to the models/ folder.\n\n"
                     "6. SMART FEATURES\n"
                     "   - Click-to-Jump: Click any sentence while speaking\n"
                     "     to resume from that point.\n"
                     "   - STOP: Stops both speech AND file generation.\n\n"
                     "7. OUTPUT FORMATS\n"
                     "   - WAV: Studio quality / OPUS: Small size, high fidelity.\n\n"
                     "Soli Deo Gloria")
        txt_widget = tk.Text(h_win, bg="#2a2a3e", fg="#e0e0e0",
                             font=("Consolas",10), padx=15, pady=15, wrap="word")
        txt_widget.insert("1.0", h_txt)
        txt_widget.config(state="disabled")
        txt_widget.pack(fill="both", expand=True, padx=10, pady=10)
        l = LANGS.get(self.lang, LANGS["EN"])
        tk.Button(h_win, text=l["close_btn"], command=h_win.destroy,
                  bg="#444", fg="#fff", width=20).pack(pady=10)

    def show_about(self):
        l = LANGS.get(self.lang, LANGS["EN"])
        about_text = (
            f"{APP_NAME} v{VERSION} — Portable Edition\n"
            "Ultimate Edition - 2026\n\n"
            "CREDITS & TECHNOLOGY:\n"
            "------------------------------------------\n"
            "• Voice Models (Piper): Community-contributed Piper TTS models\n"
            "  based on open datasets, incl. Mozilla Common Voice.\n"
            "  rhasspy/piper-voices (HuggingFace)\n\n"
            "• Voice Engine (Piper): Sherpa-ONNX Runtime\n"
            "  by k2-fsa / Next-gen Kaldi — Apache 2.0\n\n"
            "• Voice Engine (Supertonic): Supertonic TTS\n"
            "  by Resemble AI — Apache 2.0\n\n"
            "• Audio Playback: SoundDevice (PortAudio)\n"
            "  by Matthias Geier — MIT License\n\n"
            "• Numerical Processing: NumPy\n"
            "  numpy.org — BSD License\n\n"
            "• Audio Compression: Opus Tools (opusenc)\n"
            "  by Xiph.Org Foundation — BSD License\n\n"
            "• GUI Framework: Tkinter (Python Standard Library)\n\n"
            "• Development Assistance: AI-assisted development.\n\n"
            "PORTABLE / OFFLINE SUPPORT:\n"
            "------------------------------------------\n"
            "• All features work without internet after setup.\n"
            "• Copy the full program folder to a USB drive.\n"
            "• Missing components auto-detected at startup.\n\n"
            "SPECIAL THANKS:\n"
            "------------------------------------------\n"
            "• The open-source community: rhasspy, k2-fsa,\n"
            "  Resemble AI, Xiph.Org, and all contributors.\n\n"
            "------------------------------------------\n"
            "Developer: szabiz\n"
            "Contact: szabiz@yahoo.com\n"
            "License: MIT License (Open Source)\n\n"
            "Soli Deo Gloria"
        )
        win = tk.Toplevel(self.root)
        win.title(l.get("about_btn","About"))
        win.configure(bg="#1e1e2e")
        win.geometry("640x520")
        win.transient(self.root)
        win.grab_set()
        win.resizable(False,False)
        frame = tk.Frame(win, bg="#1e1e2e")
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        txt = tk.Text(frame, bg="#2a2a3e", fg="#e0e0e0", font=("Consolas",10),
                      padx=12, pady=12, wrap="word", relief="flat", bd=0,
                      yscrollcommand=scrollbar.set)
        txt.insert("1.0", about_text)
        txt.config(state="disabled")
        txt.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=txt.yview)
        btn_frame = tk.Frame(win, bg="#1e1e2e")
        btn_frame.pack(fill="x", pady=8)
        tk.Button(btn_frame, text=l.get("close_btn","CLOSE"),
                  command=lambda: (win.grab_release(), win.destroy()),
                  bg="#444", fg="#fff", width=16).pack(side="right", padx=10)


# ════════════════════════════════════════════════════════════════════════════
#  BELÉPÉSI PONT
# ════════════════════════════════════════════════════════════════════════════

def main():
    root = tk.Tk()
    root.withdraw()           # Elrejti a főablakot az ellenőrzés idejére
    root.configure(bg="#1e1e2e")

    dep_mgr = DependencyManager()

    # Ha valami hiányzik, megmutatjuk a SetupWizard-ot
    if not dep_mgr.all_ok():
        wizard_done = threading.Event()

        def on_wizard_continue():
            wizard_done.set()

        wizard = SetupWizard(root, dep_mgr, on_continue_cb=on_wizard_continue)

        def wait_for_wizard():
            if wizard.winfo_exists():
                root.after(100, wait_for_wizard)
            else:
                start_app()

        def start_app():
            root.deiconify()
            App(root)

        root.after(100, wait_for_wizard)
    else:
        root.deiconify()
        App(root)

    root.mainloop()


if __name__ == "__main__":
    main()