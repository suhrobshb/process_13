import os
import zipfile
import requests

def zip_dir(dir_path: str) -> str:
    """
    Zip the entire recording folder into dir_path.zip
    """
    zip_path = f"{dir_path.rstrip(os.sep)}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(dir_path):
            for fname in files:
                full_path = os.path.join(root, fname)
                arcname = os.path.relpath(full_path, dir_path)
                zf.write(full_path, arcname)
    return zip_path

def upload_recording(dir_path: str, upload_url: str):
    """
    Zip + POST the recording to the server.
    """
    zip_path = zip_dir(dir_path)
    print(f"[Uploader] Zipped to {zip_path}, uploading to {upload_url} …")
    with open(zip_path, "rb") as f:
        files = {"file": (os.path.basename(zip_path), f, "application/zip")}
        resp = requests.post(upload_url, files=files)
    resp.raise_for_status()
    print("[Uploader] Upload response:", resp.json()) 