from fastapi import FastAPI
from fastapi.responses import FileResponse
import os
import re

app = FastAPI()

FIRMWARE_DIR = "/home/pil/pil-hub-server/firmware"


# ===== hub status =====
@app.get("/status")
def status():
    return {"hub": "alive"}


# ===== 최신 firmware 자동 탐색 =====
def get_latest_version():

    files = os.listdir(FIRMWARE_DIR)

    versions = []

    for file in files:
        match = re.match(r"firmware_v(\d+\.\d+\.\d+)\.sh", file)
        if match:
            versions.append(match.group(1))

    if not versions:
        return None

    versions.sort(key=lambda s: list(map(int, s.split("."))))
    return versions[-1]


# ===== firmware version check =====
@app.get("/firmware/latest")
def check_latest(device_id: str, version: str):

    latest_version = get_latest_version()

    if latest_version is None:
        return {"update": False}

    if version != latest_version:
        return {
            "update": True,
            "latest_version": latest_version,
            "download_url": f"http://10.1.184.1:8000/firmware/download/{latest_version}",
            "filename": f"firmware_v{latest_version}.sh"
        }

    return {"update": False}


# ===== firmware download =====
@app.get("/firmware/download/{version}")
def download_firmware(version: str):

    file_path = f"{FIRMWARE_DIR}/firmware_v{version}.sh"

    if os.path.exists(file_path):
        return FileResponse(
            path=file_path,
            filename=f"firmware_v{version}.sh",
            media_type='application/octet-stream'
        )

    return {"error": "Firmware not found"}
