"""Widgets reutilizaveis e logica de exportacao de videos."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import re
from dataclasses import dataclass
from legopy.services.media import (
    get_video_resolution,
    get_video_duration,
    concat_and_trim_videos,
    ensure_folder_for_export,
    resolve_export_roots,
    safe_filename,
    get_ffmpeg_path,
    format_for_ffmpeg_concat,
    infer_project_prefix,
)

H_SEGMENT_PATTERN = re.compile(r"H(\d+[a-z]?|\([^)]*\)|[A-Za-z0-9+]+)", re.IGNORECASE)
VARIANT_SEGMENT_PATTERN = re.compile(r"V(\d+[A-Za-z]?)", re.IGNORECASE)
SEGMENT_PATTERN = re.compile(
    r"([VHIT](?:\([^)]*\)|[A-Za-z0-9.]+(?:\+[A-Za-z0-9.]+)*))",
    re.IGNORECASE,
)
INTRO_SUFFIX_PATTERN = re.compile(r"I(?:\([^)]*\)|[A-Za-z0-9]+)$", re.IGNORECASE)
HOOK_INTRO_PATTERN = re.compile(r"I\d+[A-Za-z0-9.]*")


def _ensure_prefix(token: str, prefix: str, default_suffix: str = "0") -> str:
    token = (token or "").strip()
    if not token:
        return f"{prefix}{default_suffix}"
    head = token[0]
    rest = token[1:] if len(token) > 1 else ""
    if head.upper() == prefix:
        return f"{prefix}{rest}"
    return f"{prefix}{token}"


def _extract_implicit_intro_tokens(hook_body: str) -> list[str]:
    return HOOK_INTRO_PATTERN.findall(hook_body or "")


def _compose_hook_combo(hook_token: str, intro_token: str | None) -> str:
    cleaned = (hook_token or "").strip()
    if not cleaned:
        return "H0"
    if cleaned.startswith("H(") and cleaned.endswith(")"):
        inner = cleaned[2:-1]
    elif cleaned.startswith("H("):
        inner = cleaned[2:]
    else:
        inner = cleaned
    if intro_token:
        intro_token = intro_token.strip()
        if intro_token and intro_token not in inner.split("+"):
            inner = f"{inner}+{intro_token}"
    return f"H({inner})"


def sanitize_project_slug(value):
    if not value:
        return "E000"
    slug = value.strip().upper()
    slug = re.sub(r"(?i)_TEST$", "", slug)
    slug = slug.rstrip("_")
    return slug or "E000"


def normalize_variant_token(token, variant_idx):
    if token:
        return _ensure_prefix(token, "V", str(variant_idx))
    return f"V{variant_idx}"


def normalize_hook_token(token, fallback_idx):
    if token:
        prefixed = _ensure_prefix(token, "H", str(fallback_idx))
        body = prefixed[1:]
        implicit_intros = tuple(_extract_implicit_intro_tokens(body))
        combo_token = None
        if body.startswith("("):
            combo_token = f"H{body}"
        elif "+" in body or implicit_intros:
            combo_token = f"H({body})"
        return prefixed, True, combo_token, implicit_intros
    return f"H{fallback_idx}", False, None, tuple()


def normalize_intro_token(token, fallback=None):
    candidate = (token or "").strip()
    if not candidate and fallback:
        candidate = (fallback or "").strip()
    if not candidate:
        return None
    return _ensure_prefix(candidate, "I", "0")


def _extract_segments(base_name):
    segments = {"V": [], "H": [], "I": [], "T": []}
    for segment in SEGMENT_PATTERN.findall(base_name or ""):
        key = segment[0].upper()
        normalized = f"{key}{segment[1:]}"
        segments.setdefault(key, []).append(normalized)
    return segments


def infer_intro_token(intro_path, fallback_idx=None):
    if not intro_path:
        if fallback_idx is None:
            return None
        return normalize_intro_token(None, f"I{fallback_idx}")
    base_name = os.path.splitext(os.path.basename(intro_path))[0]
    segments = _extract_segments(base_name)
    intro_segments = segments.get("I") or []
    if intro_segments:
        return normalize_intro_token(intro_segments[0])
    tip_segments = segments.get("T") or []
    if tip_segments:
        derived_intro = f"I({tip_segments[0]})"
        return normalize_intro_token(derived_intro)
    if fallback_idx is None:
        return None
    return normalize_intro_token(None, f"I{fallback_idx}")


@dataclass(frozen=True)
class SequenceBaseName:
    project_slug: str
    variant_token: str
    hook_token: str
    base_intro_token: str | None
    hook_combo_token: str | None = None

    def as_string(self) -> str:
        return self.with_intro(None)

    def with_intro(self, intro_token: str | None) -> str:
        default_intro = self.base_intro_token
        token = normalize_intro_token(intro_token, default_intro)
        hook = self.hook_token
        if self.hook_combo_token and (token or intro_token is not None):
            hook = self.hook_combo_token
        body = f"{self.project_slug}_{self.variant_token}{hook}"
        if token:
            body += token
        return f"{body}_T_EN"

    def __str__(self) -> str:
        return self.as_string()


def determine_sequence_base_name(project_code, primary_file, fallback_hook_idx, variant_idx=0):
    project_slug = infer_project_prefix(primary_file, project_code)
    if project_code:
        project_slug = project_code
    project_slug = sanitize_project_slug(project_slug)

    base_name = ''
    if primary_file:
        base_name = os.path.splitext(os.path.basename(primary_file))[0].strip()

    segments = _extract_segments(base_name)
    variant_raw = None
    hook_raw = None
    intro_segments = []
    tip_segments = []
    if segments:
        variant_entries = segments.get("V") or []
        hook_entries = segments.get("H") or []
        intro_segments = segments.get("I") or []
        tip_segments = segments.get("T") or []
        variant_raw = variant_entries[0] if variant_entries else None
        hook_raw = hook_entries[0] if hook_entries else None

    variant_code = normalize_variant_token(variant_raw, variant_idx)
    hook_code_raw, hook_from_file, hook_combo_candidate, implicit_intro_tokens = normalize_hook_token(
        hook_raw, fallback_hook_idx
    )

    hook_combo_token = hook_combo_candidate
    hook_token = hook_combo_candidate or hook_code_raw
    base_intro_token = None

    if hook_from_file and intro_segments:
        intro_token = normalize_intro_token(intro_segments[0])
        base_intro_token = intro_token
        if hook_combo_token is None:
            hook_combo_token = _compose_hook_combo(hook_code_raw, intro_token)
        hook_token = hook_combo_token or hook_token
    elif hook_from_file and implicit_intro_tokens:
        base_intro_token = "I0"
        if hook_combo_token is None:
            hook_combo_token = _compose_hook_combo(hook_code_raw, None)
        hook_token = hook_combo_token or hook_token
    elif not hook_from_file:
        hook_token = hook_code_raw
        base_intro_token = None

    if not hook_from_file and tip_segments:
        derived_hook = f"H({tip_segments[0]})"
        hook_token = derived_hook
        hook_combo_token = derived_hook

    if not base_intro_token and not intro_segments and not implicit_intro_tokens:
        base_intro_token = None

    return SequenceBaseName(
        project_slug=project_slug,
        variant_token=variant_code,
        hook_token=hook_token,
        base_intro_token=base_intro_token,
        hook_combo_token=hook_combo_token,
    )


def build_sequence_name(base_name, intro_idx=None, project_code=None, intro_token=None):
    if isinstance(base_name, SequenceBaseName):
        token_candidate = intro_token
        if token_candidate is None:
            if intro_idx is None:
                token_candidate = base_name.base_intro_token
            else:
                try:
                    token_candidate = f"I{int(intro_idx)}"
                except (TypeError, ValueError):
                    token_candidate = base_name.base_intro_token
        return base_name.with_intro(token_candidate)

    fallback_project = sanitize_project_slug(project_code or "E000")
    name = (base_name or '').strip()
    if not name:
        token_candidate = intro_token
        if token_candidate is None and intro_idx is not None:
            token_candidate = f"I{intro_idx}"
        token = normalize_intro_token(token_candidate)
        core = f"{fallback_project}_V0H0"
        if token:
            core += token
        return f"{core}_T_EN"

    token_candidate = intro_token
    if token_candidate is None and intro_idx is not None:
        try:
            token_candidate = f"I{int(intro_idx)}"
        except (TypeError, ValueError):
            token_candidate = None
    token = normalize_intro_token(token_candidate)
    if name.endswith('_T_EN'):
        base = INTRO_SUFFIX_PATTERN.sub('', name[:-5])
        if token:
            return f"{base}{token}_T_EN"
        return f"{base}_T_EN"
    base = INTRO_SUFFIX_PATTERN.sub('', name)
    if token:
        return f"{base}_{token}"
    return base


class FileItem(tk.Frame):
    def __init__(self, parent, filepath, move_up_cb, move_down_cb, delete_cb):
        super().__init__(parent)
        style = ttk.Style()
        bg = style.lookup('Section.TFrame', 'background') or style.lookup('TFrame', 'background') or parent.winfo_toplevel().cget('bg')
        self.configure(bg=bg)
        self.filepath = filepath
        self.label = ttk.Label(self, text=os.path.basename(filepath), width=40, anchor="w")
        self.label.grid(row=0, column=0, sticky="w")
        self.btn_up = ttk.Button(self, text="↑", width=3, command=move_up_cb)
        self.btn_up.grid(row=0, column=1)
        self.btn_down = ttk.Button(self, text="↓", width=3, command=move_down_cb)
        self.btn_down.grid(row=0, column=2)
        self.btn_delete = ttk.Button(self, text="Delete", width=6, command=delete_cb)
        self.btn_delete.grid(row=0, column=3)

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        frame_style = kwargs.pop("frame_style", None)
        canvas_bg = kwargs.pop("canvas_bg", None)
        requested_style = kwargs.get("style")
        super().__init__(container, *args, **kwargs)

        style = ttk.Style()
        if canvas_bg is None and frame_style:
            canvas_bg = style.lookup(frame_style, 'background')
        if canvas_bg is None:
            base_style = requested_style or frame_style or 'TFrame'
            canvas_bg = style.lookup(base_style, 'background') or style.lookup('TFrame', 'background') or self.winfo_toplevel().cget('bg')

        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, background=canvas_bg)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")

        self.scrollable_frame = ttk.Frame(self.canvas, style=frame_style) if frame_style else ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self._mousewheel_bound = False
        self.scrollable_frame.bind("<Enter>", self._bind_mousewheel)
        self.scrollable_frame.bind("<Leave>", self._unbind_mousewheel)
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def _on_mousewheel(self, event):
        if event.delta:
            self.canvas.yview_scroll(int(-event.delta / 120), "units")
        elif getattr(event, 'num', None) == 4:
            self.canvas.yview_scroll(-1, "units")
        elif getattr(event, 'num', None) == 5:
            self.canvas.yview_scroll(1, "units")
        return "break"

    def _bind_mousewheel(self, _event=None):
        if not self._mousewheel_bound:
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
            self.canvas.bind_all("<Button-4>", self._on_mousewheel)
            self.canvas.bind_all("<Button-5>", self._on_mousewheel)
            self._mousewheel_bound = True

    def _unbind_mousewheel(self, _event=None):
        if self._mousewheel_bound:
            self.canvas.unbind_all("<MouseWheel>")
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")
            self._mousewheel_bound = False


class BaseCompilationFrame(ttk.LabelFrame):
    def __init__(self, parent, index, on_delete_callback, files=None, allow_rename=True, name=None, duplicate_callback=None, export_checkbox=False):
        super().__init__(parent)
        self.configure(style='Section.TLabelframe')
        self.files = [os.path.abspath(f) for f in files] if files else []
        self.on_delete_callback = on_delete_callback
        self.duplicate_callback = duplicate_callback
        self.export_var = tk.BooleanVar(value=True) if export_checkbox else None
        # Use classic naming
        self.name_var = tk.StringVar(value=name or f"Compilation {index+1}")
        self.name_entry = ttk.Entry(self, textvariable=self.name_var, width=28)
        self.name_entry.grid(row=0, column=1, padx=2, pady=4, sticky="ew")
        if not allow_rename:
            self.name_entry.config(state='readonly')
        ttk.Label(self, text="Name:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        ttk.Button(self, text="Clear", command=self.delete_this_compilation).grid(row=0, column=2, padx=2, pady=4, sticky="e")
        if self.duplicate_callback:
            ttk.Button(self, text="Duplicate", command=self.duplicate).grid(row=0, column=3, padx=2, pady=4, sticky="e")
        if export_checkbox:
            ttk.Checkbutton(self, text="Export", variable=self.export_var).grid(row=0, column=4, padx=2, pady=4)
        self.files_frame = ttk.Frame(self, style='Section.TFrame')
        self.files_frame.grid(row=1, column=0, columnspan=5, sticky="ew")
        self._refresh_file_items()
        self.btn_add = ttk.Button(self, text="Add files", command=self.add_files_dialog)
        self.btn_add.grid(row=2, column=0, sticky="w", padx=(5,0), pady=(2,5))

    def set_name(self, name):
        self.name_var.set(name)

    def get_name(self):
        return self.name_var.get().strip()

    def add_file(self, filepath):
        filepath = os.path.abspath(filepath)
        if filepath not in self.files:
            self.files.append(filepath)
            self._refresh_file_items()

    def add_files(self, filepaths):
        for fp in filepaths:
            self.add_file(fp)

    def add_files_dialog(self):
        paths = filedialog.askopenfilenames(filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi *.flv *.wmv")])
        self.add_files(paths)

    def _refresh_file_items(self):
        for item in getattr(self, "file_items", []):
            item.destroy()
        self.file_items = []
        for idx, f in enumerate(self.files):
            item = FileItem(self.files_frame, f, lambda i=idx: self.move_up(i),
                            lambda i=idx: self.move_down(i),
                            lambda i=idx: self.delete_file(i))
            item.grid(row=idx, column=0, sticky="w")
            self.file_items.append(item)

    def move_up(self, index):
        if index > 0:
            self.files[index], self.files[index-1] = self.files[index-1], self.files[index]
            self._refresh_file_items()

    def move_down(self, index):
        if index < len(self.files) - 1:
            self.files[index], self.files[index+1] = self.files[index+1], self.files[index]
            self._refresh_file_items()

    def delete_file(self, index):
        del self.files[index]
        self._refresh_file_items()

    def delete_this_compilation(self):
        self.on_delete_callback(self)

    def duplicate(self):
        if self.duplicate_callback:
            self.duplicate_callback(self)

    def should_export(self):
        return self.export_var.get() if self.export_var is not None else True

    # --- Tips Compilation export to '2min'
    def export(self, duration_sec=120):
        if not self.files or not self.should_export():
            return False
        try:
            name = self.get_name() or "compilation"
            safe_name = safe_filename(name) + ".mp4"
            first_file = self.files[0]
            # --- tips always to 2min folder
            out_dir = ensure_folder_for_export(first_file, folder_name="2min")
            output_path = os.path.join(out_dir, safe_name)
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                concat_list = os.path.join(tmpdir, "files.txt")
                with open(concat_list, "w", encoding="utf-8") as f:
                    for video_path in self.files:
                        f.write(f"file '{format_for_ffmpeg_concat(video_path)}'\n")
                ffmpeg_path = get_ffmpeg_path()
                cmd = [
                    ffmpeg_path, "-y", "-f", "concat", "-safe", "0",
                    "-i", concat_list,
                    "-c", "copy", output_path
                ]
                import subprocess
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode != 0:
                    with open(os.path.join(out_dir, "tips_export_error.log"), "w", encoding="utf-8") as logf:
                        logf.write(f"CMD: {' '.join(cmd)}\n")
                        logf.write(f"RET: {result.returncode}\n")
                        logf.write(f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}")
                    return False
            return True
        except Exception as e:
            with open(os.path.join(out_dir, "tips_export_error.log"), "a", encoding="utf-8") as logf:
                logf.write(str(e))
            return False

class CompilationFrame(ttk.LabelFrame):
    def __init__(self, parent, index, on_delete_callback, files=None, allow_rename=True, name=None, duplicate_callback=None, export_checkbox=False, prefix_files_provider=None, insert_prefix_after_first=False):
        super().__init__(parent)
        self.configure(style='Section.TLabelframe')
        self.files = [os.path.abspath(f) for f in files] if files else []
        self.on_delete_callback = on_delete_callback
        self.duplicate_callback = duplicate_callback
        self.export_var = tk.BooleanVar(value=True) if export_checkbox else None
        self.prefix_files_provider = prefix_files_provider
        self.insert_prefix_after_first = insert_prefix_after_first
        # Nazwa do edycji, ale nie jest używana przy eksporcie tipsów!
        self.name_var = tk.StringVar(value=name or f"Compilation {index+1}")
        self.name_entry = ttk.Entry(self, textvariable=self.name_var, width=28)
        self.name_entry.grid(row=0, column=1, padx=2, pady=4, sticky="ew")
        if not allow_rename:
            self.name_entry.config(state='readonly')
        ttk.Label(self, text="Name:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        ttk.Button(self, text="Clear", command=self.delete_this_compilation).grid(row=0, column=2, padx=2, pady=4, sticky="e")
        if self.duplicate_callback:
            ttk.Button(self, text="Duplicate", command=self.duplicate).grid(row=0, column=3, padx=2, pady=4, sticky="e")
        if export_checkbox:
            ttk.Checkbutton(self, text="Export", variable=self.export_var).grid(row=0, column=4, padx=2, pady=4)
        self.files_frame = ttk.Frame(self, style='Section.TFrame')
        self.files_frame.grid(row=1, column=0, columnspan=5, sticky="ew")
        self._refresh_file_items()
        self.btn_add = ttk.Button(self, text="Add files", command=self.add_files_dialog)
        self.btn_add.grid(row=2, column=0, sticky="w", padx=(5,0), pady=(2,5))

    def set_name(self, name):
        self.name_var.set(name)
    def get_name(self):
        return self.name_var.get().strip()
    def add_file(self, filepath):
        filepath = os.path.abspath(filepath)
        if filepath not in self.files:
            self.files.append(filepath)
            self._refresh_file_items()
    def add_files(self, filepaths):
        for fp in filepaths:
            self.add_file(fp)
    def add_files_dialog(self):
        paths = filedialog.askopenfilenames(filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi *.flv *.wmv")])
        self.add_files(paths)
    def _refresh_file_items(self):
        for item in getattr(self, "file_items", []):
            item.destroy()
        self.file_items = []
        for idx, f in enumerate(self.files):
            item = FileItem(self.files_frame, f, lambda i=idx: self.move_up(i),
                            lambda i=idx: self.move_down(i),
                            lambda i=idx: self.delete_file(i))
            item.grid(row=idx, column=0, sticky="w")
            self.file_items.append(item)
    def move_up(self, index):
        if index > 0:
            self.files[index], self.files[index-1] = self.files[index-1], self.files[index]
            self._refresh_file_items()
    def move_down(self, index):
        if index < len(self.files) - 1:
            self.files[index], self.files[index+1] = self.files[index+1], self.files[index]
            self._refresh_file_items()
    def delete_file(self, index):
        del self.files[index]
        self._refresh_file_items()
    def delete_this_compilation(self):
        self.on_delete_callback(self)
    def duplicate(self):
        if self.duplicate_callback:
            self.duplicate_callback(self)
    def should_export(self):
        return self.export_var.get() if self.export_var is not None else True

    def export(self, duration_sec=120):
        if not self.files or not self.should_export():
            return False
        try:
            first_file = self.files[0]
            # Nazwa pliku wynikowego: nazwa pliku + _(MM'SS).mp4
            total_duration = get_video_duration(first_file)
            mm = int(total_duration // 60)
            ss = int(total_duration % 60)
            base_name = os.path.splitext(os.path.basename(first_file))[0]
            output_name = f"{base_name}_({mm:02d}'{ss:02d}).mp4"
            out_dir = ensure_folder_for_export(first_file, folder_name="2min")
            output_path = os.path.join(out_dir, output_name)

            export_sequence = list(self.files)
            prefix_files = []
            if callable(self.prefix_files_provider):
                try:
                    prefix_files = [os.path.abspath(p) for p in (self.prefix_files_provider() or []) if p]
                except Exception:
                    prefix_files = []
            if prefix_files:
                existing = {os.path.abspath(p) for p in export_sequence}
                ordered_prefix = [p for p in prefix_files if os.path.abspath(p) not in existing]
                if ordered_prefix:
                    if self.insert_prefix_after_first and export_sequence:
                        export_sequence = [export_sequence[0]] + ordered_prefix + export_sequence[1:]
                    else:
                        export_sequence = ordered_prefix + export_sequence

            concat_and_trim_videos(export_sequence, output_path, duration_sec=duration_sec)
            return True
        except Exception as e:
            with open(os.path.join(os.path.dirname(self.files[0]), "tips_export_error.log"), "a", encoding="utf-8") as logf:
                logf.write(str(e))
            return False


class SequenceCompilationFrame(BaseCompilationFrame):
    def __init__(self, *args, export_checkbox=True, **kwargs):
        super().__init__(*args, export_checkbox=export_checkbox, **kwargs)

    # --- Sequence Compilation export to Sequences_RealLength folder
    def export(self, duration_sec=120):
        if not self.files or not self.should_export():
            return False
        try:
            name = self.get_name() or "sequence"
            safe_name = safe_filename(name) + ".mp4"
            first_file = self.files[0]
            _, sequences_dir = resolve_export_roots(first_file)
            os.makedirs(sequences_dir, exist_ok=True)
            output_path = os.path.join(sequences_dir, safe_name)
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                concat_list = os.path.join(tmpdir, "files.txt")
                with open(concat_list, "w", encoding="utf-8") as f:
                    for video_path in self.files:
                        f.write(f"file '{format_for_ffmpeg_concat(video_path)}'\n")
                ffmpeg_path = get_ffmpeg_path()
                cmd = [
                    ffmpeg_path, "-y", "-f", "concat", "-safe", "0",
                    "-i", concat_list,
                    "-c", "copy", output_path
                ]
                import subprocess
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode != 0:
                    error_log = os.path.join(sequences_dir, "sequence_export_error.log")
                    with open(error_log, "w", encoding="utf-8") as logf:
                        logf.write(f"CMD: {' '.join(cmd)}\n")
                        logf.write(f"RET: {result.returncode}\n")
                        logf.write(f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}")
                    return False
            return True
        except Exception as e:
            error_base = sequences_dir if 'sequences_dir' in locals() else os.path.dirname(self.files[0])
            with open(os.path.join(error_base, "sequence_export_error.log"), "a", encoding="utf-8") as logf:
                logf.write(str(e))
            return False

class SequenceCompilationsManager:
    def __init__(self, parent, get_global_resolution_ref, get_hooks_compilations, get_tips_compilations, get_project_code, get_intro_files=None, export_tips_callback=None, get_sequence_tip_files=None):
        self.parent = parent
        self.get_global_resolution_ref = get_global_resolution_ref
        self.get_hooks_compilations = get_hooks_compilations
        self.get_tips_compilations = get_tips_compilations
        self.get_project_code = get_project_code
        self.get_intro_files = get_intro_files or (lambda: [])
        self.get_sequence_tip_files = get_sequence_tip_files
        self.sequence_frames = []
        self.progress_var = tk.DoubleVar()

        self.export_tips_callback = export_tips_callback

        button_frame = ttk.Frame(parent, style='Section.TFrame')
        button_frame.pack(fill="x", pady=(10, 0))
        ttk.Label(button_frame, text="Sequence Compilations", font=("Arial", 15, "bold"), style='SectionHeading.TLabel').pack(anchor="center")
        self.btn_add_empty_sequence = ttk.Button(button_frame, text="Add Empty Sequence Compilation", command=self.add_empty_sequence, style='Accent.TButton')
        self.btn_add_empty_sequence.pack(pady=5, fill="x")
        self.container_sequences = ScrollableFrame(parent, style='Section.TFrame', frame_style='Section.TFrame')
        self.container_sequences.pack(fill="both", expand=True, padx=5, pady=5)
        self.progress_bar = ttk.Progressbar(parent, variable=self.progress_var, maximum=100, style='Accent.Horizontal.TProgressbar')
        self.progress_bar.pack(side="bottom", fill="x", padx=20, pady=(0,2))
        export_frame = ttk.Frame(parent, style='Section.TFrame')
        export_frame.pack(side="bottom", fill="x", padx=20, pady=(2, 12))
        if callable(self.export_tips_callback):
            self.btn_export_tips = ttk.Button(export_frame, text="Export Tips Compilations", command=self.export_tips_compilations, style='Accent.TButton')
            self.btn_export_tips.pack(anchor="center", pady=(0, 4), fill="x")
        self.btn_export_sequences = ttk.Button(export_frame, text="Export Sequence Compilations", command=self.export_sequences, style='Accent.TButton')
        self.btn_export_sequences.pack(anchor="center", fill="x")

    def _determine_sequence_base_name(self, primary_file, fallback_hook_idx, variant_idx=0):
        project_code = self.get_project_code()
        return determine_sequence_base_name(project_code, primary_file, fallback_hook_idx, variant_idx)



    def _build_sequence_name(self, base_name, intro_idx=None, intro_token=None):
        project_code = self.get_project_code()
        return build_sequence_name(base_name, intro_idx, project_code, intro_token=intro_token)





    def add_empty_sequence(self):
        idx = len(self.sequence_frames)
        base_name = self._determine_sequence_base_name(None, idx, variant_idx=idx)
        name = self._build_sequence_name(base_name)
        seq = SequenceCompilationFrame(
            self.container_sequences.scrollable_frame,
            index=idx,
            on_delete_callback=self.remove_sequence,
            duplicate_callback=self.duplicate_sequence,
            allow_rename=True,
            name=name,
            files=[],
            export_checkbox=True
        )
        seq.pack(fill="x", pady=5)
        self.sequence_frames.append(seq)


    def remove_sequence(self, frame):
        idx = self.sequence_frames.index(frame)
        frame.destroy()
        self.sequence_frames.pop(idx)
        for i, seq in enumerate(self.sequence_frames):
            fallback_name = self._determine_sequence_base_name(None, i, variant_idx=i)
            seq.set_name(self._build_sequence_name(fallback_name))


    def duplicate_sequence(self, frame):
        idx = self.sequence_frames.index(frame)
        new_frame = SequenceCompilationFrame(
            self.container_sequences.scrollable_frame,
            index=idx+1,
            on_delete_callback=self.remove_sequence,
            duplicate_callback=self.duplicate_sequence,
            allow_rename=True,
            name=self._build_sequence_name(self._determine_sequence_base_name(None, idx + 1, variant_idx=idx + 1)),
            files=frame.files.copy(),
            export_checkbox=True
        )
        new_frame.pack_forget()
        self.sequence_frames.insert(idx+1, new_frame)
        for cf in self.sequence_frames:
            cf.pack_forget()
            cf.pack(fill="x", pady=5)
        for i, seq in enumerate(self.sequence_frames):
            fallback_name = self._determine_sequence_base_name(None, i, variant_idx=i)
            seq.set_name(self._build_sequence_name(fallback_name))


    def load_sequences(self):
        for frame in getattr(self, "sequence_frames", []):
            frame.destroy()
        self.sequence_frames = []

        tips_compilations = self.get_tips_compilations()
        hooks_compilations = self.get_hooks_compilations()
        intro_files = list(self.get_intro_files() or [])
        intro_entries = []
        for intro_idx, intro_path in enumerate(intro_files, start=1):
            intro_token = infer_intro_token(intro_path, intro_idx)
            intro_entries.append((intro_idx, intro_path, intro_token))

        base_tip_files = []
        if callable(getattr(self, "get_sequence_tip_files", None)):
            try:
                base_tip_files = list(self.get_sequence_tip_files() or [])
            except Exception:
                base_tip_files = []
        if not base_tip_files and tips_compilations and tips_compilations[0].files:
            base_tip_files = list(tips_compilations[0].files)

        if not base_tip_files:
            return

        def append_sequence(name: str, files):
            seq_frame = SequenceCompilationFrame(
                self.container_sequences.scrollable_frame,
                index=len(self.sequence_frames),
                on_delete_callback=self.remove_sequence,
                duplicate_callback=self.duplicate_sequence,
                allow_rename=True,
                name=name,
                files=list(files),
                export_checkbox=True
            )
            seq_frame.pack(fill="x", pady=5)
            self.sequence_frames.append(seq_frame)

        def add_sequence_variants(base_name, tip_files, hook_file=None):
            tip_list = list(tip_files)
            default_intro_token = None
            if intro_entries:
                if isinstance(base_name, SequenceBaseName):
                    default_intro_token = base_name.base_intro_token or "I0"
                else:
                    default_intro_token = "I0"
            if hook_file:
                base_sequence = [hook_file] + tip_list
                append_sequence(self._build_sequence_name(base_name, None, intro_token=default_intro_token), base_sequence)
                for intro_idx, intro_path, intro_token in intro_entries:
                    sequence_files = [hook_file, intro_path] + tip_list
                    append_sequence(
                        self._build_sequence_name(base_name, intro_idx, intro_token=intro_token),
                        sequence_files,
                    )
            else:
                base_sequence = list(tip_list)
                append_sequence(self._build_sequence_name(base_name, None, intro_token=default_intro_token), base_sequence)
                for intro_idx, intro_path, intro_token in intro_entries:
                    sequence_files = [intro_path] + tip_list
                    append_sequence(
                        self._build_sequence_name(base_name, intro_idx, intro_token=intro_token),
                        sequence_files,
                    )

        primary_tip = base_tip_files[0] if base_tip_files else None
        base_name = self._determine_sequence_base_name(primary_tip, fallback_hook_idx=0)
        add_sequence_variants(base_name, base_tip_files, hook_file=None)

        for idx, hook_comp in enumerate(hooks_compilations, start=1):
            if not hook_comp.files:
                continue
            hook_primary = hook_comp.files[0]
            sequence_name = self._determine_sequence_base_name(hook_primary, fallback_hook_idx=idx)
            add_sequence_variants(sequence_name, base_tip_files, hook_file=hook_primary)



    def export_tips_compilations(self):
        if callable(self.export_tips_callback):
            self.export_tips_callback()


    def export_sequences(self):
        if not self.sequence_frames:
            messagebox.showinfo("Export", "No sequences to export.")
            return
        base_res = None
        for cf in self.sequence_frames:
            for f in cf.files:
                if not base_res:
                    base_res = get_video_resolution(f)
                elif get_video_resolution(f) != base_res:
                    messagebox.showerror("Resolution mismatch", "Not all files in all sequences have the same resolution!")
                    return
        errors = []
        count = 0
        total = len(self.sequence_frames)
        for idx, cf in enumerate(self.sequence_frames):
            if hasattr(cf, "should_export") and not cf.should_export():
                continue
            if not cf.files:
                continue
            try:
                ok = cf.export()
                if not ok:
                    errors.append(cf.get_name())
                else:
                    count += 1
            except Exception as e:
                errors.append(cf.get_name())
            progress_percent = ((idx + 1) / total) * 100
            self.progress_var.set(progress_percent)
        self.progress_var.set(0)
        if errors:
            messagebox.showerror("Export error", f"Failed to export: {', '.join(errors)}")
        else:
            messagebox.showinfo("Export", f"Exported {count} sequence compilations to Sequences_RealLength folders.")
