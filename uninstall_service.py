import sys
import subprocess
import ctypes
from pathlib import Path

SERVICE_NAME = "MT5TelegramMonitor"
NSSM_EXE     = Path(__file__).parent / "nssm" / "nssm.exe"


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def nssm(args: list):
    result = subprocess.run([str(NSSM_EXE)] + args, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())


if __name__ == "__main__":
    if not is_admin():
        print("[ERROR] Jalankan sebagai Administrator!")
        input("Tekan Enter untuk keluar...")
        sys.exit(1)

    print(f"[...] Stop service {SERVICE_NAME}...")
    nssm(["stop", SERVICE_NAME])

    print(f"[...] Remove service {SERVICE_NAME}...")
    nssm(["remove", SERVICE_NAME, "confirm"])

    print(f"[OK] Service '{SERVICE_NAME}' berhasil dihapus.")
    input("Tekan Enter untuk keluar...")
