"""
Utility helpers for packaging a recorded session and uploading it to the
backend.  Supports:

* Zipping a directory (custom compression level)
* Progress-aware uploads
* Chunked uploads for large files
* Simple retry logic
* Optional status-callback for UI updates / logs
"""

from __future__ import annotations

import math
import os
import time
import zipfile
from typing import Callable, Optional

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

def _stream_with_progress(
    file_obj, total_size: int, chunk_size: int, callback: Optional[Callable[[float], None]]
):
    """
    Generator that yields file chunks while reporting progress.
    """
    bytes_sent = 0
    while True:
        data = file_obj.read(chunk_size)
        if not data:
            break
        bytes_sent += len(data)
        if callback:
            callback(min(bytes_sent / total_size * 100, 100.0))
        yield data


def upload_recording(
    dir_path: str,
    upload_url: str,
    *,
    chunk_size: int = 5 * 1024 * 1024,
    retries: int = 3,
    callback: Optional[Callable[[float], None]] = None,
) -> dict:
    """
    Compress *dir_path* and upload it to *upload_url*.

    For files larger than *chunk_size* bytes this method switches to a simple
    chunked-upload protocol compatible with the `/upload_chunk` endpoint
    defined in *ai_engine/routers/task_router.py*.

    Parameters
    ----------
    dir_path : str
        Directory containing the recording.
    upload_url : str
        Endpoint accepting `multipart/form-data` with field ``file`` *or*
        chunked uploads (see backend).
    chunk_size : int
        Threshold and chunk size for chunked uploads.
    retries : int
        Max number of retry attempts on transient network errors.
    callback : Callable[[float], None] | None
        Optional function receiving current upload progress (0-100 float).
    """

    zip_path = zip_dir(dir_path)
    total_size = os.path.getsize(zip_path)
    print(f"[Uploader] Created archive {zip_path} ({total_size/1_048_576:.2f} MB)")

    # Helper for request with retries
    def _do_request(**kwargs):
        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                return requests.post(**kwargs, timeout=60)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
                print(f"[Uploader] Network error (attempt {attempt}/{retries}) – retrying…")
                time.sleep(2**attempt)  # exponential backoff
        raise last_exc  # type: ignore[arg-type]

    if total_size <= chunk_size:
        # Simple single-request upload with progress reporting
        with open(zip_path, "rb") as fp:
            # `files` has to be a tuple (filename, file-obj, mimetype)
            files = {
                "file": (
                    os.path.basename(zip_path),
                    _stream_with_progress(fp, total_size, 64 * 1024, callback),
                    "application/zip",
                )
            }
            resp = _do_request(url=upload_url, files=files)
    else:
        # Chunked upload
        total_chunks = math.ceil(total_size / chunk_size)
        with open(zip_path, "rb") as fp:
            for idx in range(total_chunks):
                chunk_data = fp.read(chunk_size)
                params = {"chunk_index": idx, "total_chunks": total_chunks}
                files = {
                    "file": (
                        os.path.basename(zip_path),
                        chunk_data,
                        "application/octet-stream",
                    )
                }
                resp = _do_request(url=upload_url, params=params, files=files)
                if callback:
                    callback((idx + 1) / total_chunks * 100)

    resp.raise_for_status()
    json_resp = resp.json()
    print("[Uploader] Upload success:", json_resp)
    if callback:
        callback(100.0)
    return json_resp