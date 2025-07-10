import argparse
import time
from recorder.multi_monitor_capture import MultiMonitorCapture
from uploader import upload_recording

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoOps Desktop Agent")
    parser.add_argument("--output-dir", default=f"recordings/{int(time.time())}")
    parser.add_argument("--upload-url", help="API endpoint for upload (e.g. http://localhost:8000/api/tasks/upload)")
    args = parser.parse_args()

    cap = MultiMonitorCapture(args.output_dir, fps=2)
    cap.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cap.stop()
        if args.upload_url:
            upload_recording(args.output_dir, args.upload_url) 