"""Media and file-system utilities for the LegoPy application."""

import os
import sys
import subprocess
import shutil
import re
import stat
from pathlib import Path


def _application_root():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def resource_path(relative_path):
    return str(_application_root() / relative_path)


def _resolve_ffmpeg_binary(binary_name):
    exe = f"{binary_name}.exe" if os.name == "nt" else binary_name
    env_override = os.environ.get(f"{binary_name.upper()}_PATH")
    if env_override:
        env_path = Path(env_override)
        if env_path.is_file():
            return _ensure_executable(env_path, allow_fix=False)
    bundle_candidate = _application_root() / "ffmpeg-bin" / exe
    if bundle_candidate.is_file():
        return _ensure_executable(bundle_candidate)
    system_candidate = shutil.which(exe)
    if system_candidate:
        return _ensure_executable(system_candidate, allow_fix=False)
    raise FileNotFoundError(f"{exe} not found. Expected it at {bundle_candidate}")


def _ensure_executable(binary_path, allow_fix=True):
    """Make sure the bundled FFmpeg binary has execute permission on POSIX."""
    binary_path = Path(binary_path)
    candidate = str(binary_path)
    if os.name == "nt":
        return candidate
    if os.access(candidate, os.X_OK):
        return candidate
    if not allow_fix:
        raise PermissionError(
            f"{candidate} is not executable. Run 'chmod +x \"{candidate}\"' or "
            "choose another FFmpeg binary with execute permission."
        )
    try:
        current_mode = binary_path.stat().st_mode
        new_mode = current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        os.chmod(candidate, new_mode)
    except OSError as exc:
        raise PermissionError(
            f"Could not set execute permission on {candidate}. "
            "Run 'chmod +x' manually or provide an external FFmpeg binary."
        ) from exc
    if not os.access(candidate, os.X_OK):
        raise PermissionError(
            f"{candidate} is not executable even after chmod. "
            "Run 'chmod +x' manually or provide an external FFmpeg binary."
        )
    return candidate



def format_for_ffmpeg_concat(path: str) -> str:
    formatted = Path(path).resolve().as_posix()
    return formatted.replace("'", "'\\''")

TIP_VARIANT_PATTERN = re.compile(r"T\d+(?:\.[A-Za-z0-9]+)*[A-Za-z]?", re.IGNORECASE)

PARTS_REAL_LENGTH_SUFFIX = "_Parts_RealLength"
SUFFIXES_FOR_PROJECT = (
    PARTS_REAL_LENGTH_SUFFIX,
    "_Sequences_RealLength",
    "_Parts_2min",
)


def _remove_suffix_casefold(name: str, suffix: str):
    if len(name) < len(suffix):
        return None
    if name.lower().endswith(suffix.lower()):
        return name[:-len(suffix)]
    return None



def select_preferred_tip_variants(filepaths, return_extras=False, keep_all_variants=False):
    """Return a list filtered according to the Gotcha! naming rules.

    When `keep_all_variants` is True, only duplicate *paths* are removed.
    Otherwise the first alphabetical lowercase variant is preferred for each
    Tip id while uppercase variants are kept alongside to support pairing."""
    if not filepaths:
        return ([], []) if return_extras else []

    if keep_all_variants:
        ordered_unique = []
        seen_paths = set()
        for path in filepaths:
            if path in seen_paths:
                continue
            ordered_unique.append(path)
            seen_paths.add(path)
        return (ordered_unique, []) if return_extras else ordered_unique

    selected = {}
    extras = []

    for idx, path in enumerate(filepaths):
        base = os.path.splitext(os.path.basename(path))[0]
        match = TIP_VARIANT_PATTERN.search(base)
        if match:
            tip_token = match.group(0)
            number_match = re.match(r"T(\d+)", tip_token, re.IGNORECASE)
            tip_number = number_match.group(1) if number_match else None
            suffix = tip_token[1 + len(tip_number or ""):]
            variant_letter = ""
            if suffix:
                first_char = suffix[0]
                if first_char.isalpha():
                    variant_letter = first_char
            remainder = base[match.end():] or ""
            is_upper_variant = variant_letter.isupper()
            variant_key = (tip_number, remainder)
            if is_upper_variant:
                # Uppercase variants have pairing semantics; keep them all but deduplicate identical entries.
                key = ("UPPER", tip_number, variant_letter, remainder, suffix)
                info = selected.get(key)
                if info is None or idx < info['index']:
                    if info:
                        extras.append((info['index'], info['path']))
                    selected[key] = {'letter': variant_letter, 'path': path, 'index': idx}
                else:
                    extras.append((idx, path))
                continue
        else:
            tip_number = None
            variant_letter = ""
            remainder = ""
            is_upper_variant = False
            variant_key = base.upper()

        if is_upper_variant:
            continue  # already handled above

        info = selected.get(variant_key)
        letter_cmp = variant_letter or ""
        if info is None:
            selected[variant_key] = {'letter': letter_cmp, 'path': path, 'index': idx}
            continue

        should_replace = (
            letter_cmp < info['letter']
            or (letter_cmp == info['letter'] and idx < info['index'])
        )
        if should_replace:
            extras.append((info['index'], info['path']))
            selected[variant_key] = {'letter': letter_cmp, 'path': path, 'index': idx}
        else:
            extras.append((idx, path))

    ordered = sorted(selected.values(), key=lambda item: item['index'])
    preferred = [item['path'] for item in ordered]
    if return_extras:
        extras_sorted = [item[1] for item in sorted(extras, key=lambda pair: pair[0])]
        return preferred, extras_sorted
    return preferred





def infer_project_prefix(source_path, fallback=''):
    if source_path:
        directory = os.path.dirname(os.path.abspath(source_path))
        base_name = os.path.basename(directory).rstrip('/\\')
        for suffix in SUFFIXES_FOR_PROJECT:
            stripped = _remove_suffix_casefold(base_name, suffix)
            if stripped is not None:
                return stripped.rstrip('_')
    fallback_clean = ''.join(ch for ch in (fallback or '') if ch.isalnum() or ch in {'_', '-'})
    fallback_clean = fallback_clean.rstrip('_')
    if fallback_clean:
        return fallback_clean.upper()
    return 'E000'



def resolve_export_roots(first_file_path):
    """Return tuple of (parts_2min_dir, sequences_real_length_dir)."""
    if not first_file_path:
        raise ValueError('first_file_path must be provided')
    absolute = os.path.abspath(first_file_path)
    base_dir = os.path.dirname(absolute)
    base_name = os.path.basename(base_dir).rstrip('/\\')
    root_dir = base_dir
    prefix_candidate = None
    for suffix in (PARTS_REAL_LENGTH_SUFFIX, "_Sequences_RealLength"):
        stripped = _remove_suffix_casefold(base_name, suffix)
        if stripped is not None:
            prefix_candidate = stripped.rstrip('_')
            root_dir = os.path.dirname(base_dir)
            break
    if prefix_candidate is None:
        prefix_candidate = base_name.rstrip('_')
    if not prefix_candidate:
        prefix_candidate = 'Export'
    parts_dir = os.path.join(root_dir, f"{prefix_candidate}_Parts_2min")
    sequences_dir = os.path.join(root_dir, f"{prefix_candidate}_Sequences_RealLength")
    return parts_dir, sequences_dir




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


def export_clip_to_2min(source_path, output_basename=None, duration_sec=120):
    """Create a 2-minute version of a single clip, saving it to the Parts_2min folder."""
    if not source_path:
        raise ValueError("source_path must be provided")
    absolute = os.path.abspath(source_path)
    out_dir = ensure_folder_for_export(absolute, folder_name="2min")
    base_name = output_basename or f"{os.path.splitext(os.path.basename(absolute))[0]}_2min"
    safe_name = f"{safe_filename(base_name)}.mp4"
    output_path = os.path.join(out_dir, safe_name)
    concat_and_trim_videos([absolute], output_path, duration_sec=duration_sec)
    return output_path


def ensure_folder_for_export(first_file_path, folder_name=None):
    if folder_name == "2min":
        parts_dir, _ = resolve_export_roots(first_file_path)
        os.makedirs(parts_dir, exist_ok=True)
        return parts_dir
    if folder_name in {"sequence", "sequences"}:
        _, sequences_dir = resolve_export_roots(first_file_path)
        os.makedirs(sequences_dir, exist_ok=True)
        return sequences_dir
    base_dir = os.path.dirname(first_file_path)
    if folder_name:
        folder = os.path.join(base_dir, folder_name)
        os.makedirs(folder, exist_ok=True)
        return folder
    return base_dir


def safe_filename(name):
    allowed = ('_', '-', ' ', '(', ')')
    return ''.join(c for c in name if c.isalnum() or c in allowed).rstrip()

__all__ = [
    "resource_path",
    "format_for_ffmpeg_concat",
    "TIP_VARIANT_PATTERN",
    "PARTS_REAL_LENGTH_SUFFIX",
    "SUFFIXES_FOR_PROJECT",
    "select_preferred_tip_variants",
    "infer_project_prefix",
    "resolve_export_roots",
    "get_ffmpeg_path",
    "get_ffprobe_path",
    "get_video_resolution",
    "get_video_duration",
    "concat_and_trim_videos",
    "ensure_folder_for_export",
    "safe_filename",
    "export_clip_to_2min",
]
