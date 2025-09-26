import os
import sys
import subprocess
import shutil
from pathlib import Path


def _application_root():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def resource_path(relative_path):
    return str(_application_root() / relative_path)


def _resolve_ffmpeg_binary(binary_name):
    exe = f"{binary_name}.exe" if os.name == "nt" else binary_name
    env_override = os.environ.get(f"{binary_name.upper()}_PATH")
    if env_override and Path(env_override).is_file():
        return str(Path(env_override))
    bundle_candidate = _application_root() / "ffmpeg-bin" / exe
    if bundle_candidate.is_file():
        return str(bundle_candidate)
    system_candidate = shutil.which(exe)
    if system_candidate:
        return system_candidate
    raise FileNotFoundError(f"{exe} not found. Expected it at {bundle_candidate}")



def format_for_ffmpeg_concat(path: str) -> str:
    formatted = Path(path).resolve().as_posix()
    return formatted.replace("'", "'\\''")

def get_ffmpeg_path():
    return _resolve_ffmpeg_binary("ffmpeg")


def get_ffprobe_path():
    return _resolve_ffmpeg_binary("ffprobe")


def get_video_resolution(filepath):
    ffprobe_path = get_ffprobe_path()
    cmd = [
        ffprobe_path, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0", filepath
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        res = result.stdout.strip()
        if "x" in res:
            return res
    except Exception:
        pass
    return ""


def get_video_duration(filepath):
    ffprobe_path = get_ffprobe_path()
    cmd = [
        ffprobe_path, "-v", "error", "-show_entries",
        "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", filepath
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # DIAGNOSTICS!
        with open("duration_diag.log", "a", encoding="utf-8") as f:
            f.write(f"\n--- Checking: {filepath}\nCMD: {' '.join(cmd)}\nRET: {result.returncode}\nOUT: {result.stdout}\nERR: {result.stderr}\n")
        if result.returncode != 0:
            return 0.0
        return float(result.stdout.strip())
    except Exception as e:
        with open("duration_diag.log", "a", encoding="utf-8") as f:
            f.write(f"\nEXC for {filepath}: {e}\n")
        return 0.0


def concat_and_trim_videos(file_list, output_path, duration_sec=120):
    ffmpeg_path = get_ffmpeg_path()
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        list_file_path = os.path.join(tmpdir, "files.txt")
        with open(list_file_path, "w", encoding="utf-8") as f:
            for file in file_list:
                f.write(f"file '{format_for_ffmpeg_concat(file)}'\n")
        merged_path = os.path.join(tmpdir, "merged.mp4")
        cmd_concat = [
            ffmpeg_path, "-y", "-f", "concat", "-safe", "0",
            "-i", list_file_path, "-c", "copy", merged_path
        ]
        result_concat = subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # DIAGNOSTICS!
        with open("ffmpeg_concat_diag.log", "a", encoding="utf-8") as f:
            f.write(f"\nCMD: {' '.join(cmd_concat)}\nRET: {result_concat.returncode}\nOUT: {result_concat.stdout}\nERR: {result_concat.stderr}\n")
        if result_concat.returncode != 0:
            raise RuntimeError(f"Error during concatenation:\n{result_concat.stderr}")

        cmd_trim = [
            ffmpeg_path, "-y",
            "-i", merged_path,
            "-t", str(duration_sec),
            "-c", "copy",
            output_path
        ]
        result_trim = subprocess.run(cmd_trim, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        with open("ffmpeg_trim_diag.log", "a", encoding="utf-8") as f:
            f.write(f"\nCMD: {' '.join(cmd_trim)}\nRET: {result_trim.returncode}\nOUT: {result_trim.stdout}\nERR: {result_trim.stderr}\n")
        if result_trim.returncode != 0:
            raise RuntimeError(f"Error during trimming:\n{result_trim.stderr}")


def ensure_folder_for_export(first_file_path, folder_name=None):
    base_dir = os.path.dirname(first_file_path)
    if folder_name:
        folder = os.path.join(base_dir, folder_name)
        os.makedirs(folder, exist_ok=True)
        return folder
    return base_dir


def safe_filename(name):
    return "".join(c for c in name if c.isalnum() or c in ('_', '-', ' ')).rstrip()
