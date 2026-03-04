"""
Auto-install mt5_monitor.py sebagai Windows Service menggunakan NSSM.
Jalankan sebagai Administrator.
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
from pathlib import Path

SERVICE_NAME    = "MT5TelegramMonitor"
SERVICE_DISPLAY = "MT5 Telegram Monitor"
SERVICE_DESC    = "Monitor MT5 orders dan kirim notifikasi ke Telegram"

SCRIPT_DIR  = Path(__file__).parent.resolve()
SCRIPT_PATH = SCRIPT_DIR / "mt5_monitor.py"
PYTHON_PATH = Path(sys.executable)
NSSM_DIR    = SCRIPT_DIR / "nssm"
NSSM_EXE    = NSSM_DIR / "nssm.exe"
LOG_FILE    = SCRIPT_DIR / "mt5_monitor.log"

NSSM_DOWNLOAD_URL = "https://nssm.cc/release/nssm-2.24.zip"


def is_admin() -> bool:
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def download_nssm():
    if NSSM_EXE.exists():
        print(f"[OK] NSSM sudah ada: {NSSM_EXE}")
        return

    print("[...] Download NSSM...")
    zip_path = SCRIPT_DIR / "nssm.zip"

    urllib.request.urlretrieve(NSSM_DOWNLOAD_URL, zip_path)
    print("[OK] Download selesai.")

    NSSM_DIR.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        for member in z.namelist():
            if "win64/nssm.exe" in member:
                with z.open(member) as src, open(NSSM_EXE, "wb") as dst:
                    dst.write(src.read())
                break

    zip_path.unlink()
    print(f"[OK] NSSM diekstrak ke: {NSSM_EXE}")


def nssm(args: list) -> int:
    result = subprocess.run([str(NSSM_EXE)] + args, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    return result.returncode


def service_exists() -> bool:
    result = subprocess.run(
        ["sc", "query", SERVICE_NAME],
        capture_output=True, text=True
    )
    return result.returncode == 0


def install():
    print(f"\n=== Install Service: {SERVICE_NAME} ===\n")

    if not is_admin():
        print("[ERROR] Jalankan script ini sebagai Administrator!")
        input("Tekan Enter untuk keluar...")
        sys.exit(1)

    if not SCRIPT_PATH.exists():
        print(f"[ERROR] File tidak ditemukan: {SCRIPT_PATH}")
        sys.exit(1)

    download_nssm()

    if service_exists():
        print(f"[!] Service '{SERVICE_NAME}' sudah ada. Stop dan hapus dulu...")
        nssm(["stop", SERVICE_NAME])
        nssm(["remove", SERVICE_NAME, "confirm"])

    print(f"[...] Install service...")
    nssm(["install", SERVICE_NAME, str(PYTHON_PATH), str(SCRIPT_PATH)])

    nssm(["set", SERVICE_NAME, "AppDirectory",   str(SCRIPT_DIR)])
    nssm(["set", SERVICE_NAME, "DisplayName",    SERVICE_DISPLAY])
    nssm(["set", SERVICE_NAME, "Description",    SERVICE_DESC])
    nssm(["set", SERVICE_NAME, "Start",          "SERVICE_AUTO_START"])
    nssm(["set", SERVICE_NAME, "AppStdout",      str(LOG_FILE)])
    nssm(["set", SERVICE_NAME, "AppStderr",      str(LOG_FILE)])
    nssm(["set", SERVICE_NAME, "AppRotateFiles", "1"])
    nssm(["set", SERVICE_NAME, "AppRotateBytes", "5242880"])  # 5MB

    print(f"\n[...] Start service...")
    nssm(["start", SERVICE_NAME])

    print(f"""
=== Selesai ===

Service   : {SERVICE_NAME}
Status    : Running
Auto-start: Ya (nyala otomatis saat Windows boot)
Log file  : {LOG_FILE}

Commands:
  Lihat status : nssm status {SERVICE_NAME}
  Stop         : nssm stop {SERVICE_NAME}
  Restart      : nssm restart {SERVICE_NAME}
  Uninstall    : python uninstall_service.py
""")


if __name__ == "__main__":
    install()
    input("Tekan Enter untuk keluar...")
