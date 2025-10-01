import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import re
from utils import (
    get_video_resolution,
    get_video_duration,
    concat_and_trim_videos,
    ensure_folder_for_export,
    resolve_export_roots,
    safe_filename,
    get_ffmpeg_path,
    format_for_ffmpeg_concat
)

H_SEGMENT_PATTERN = re.compile(r"H(\d+[a-z]?|\([^)]*\))", re.IGNORECASE)
VARIANT_SEGMENT_PATTERN = re.compile(r"V(\d+[A-Za-z]?)", re.IGNORECASE)
INTRO_SUFFIX_PATTERN = re.compile(r"I\d+$", re.IGNORECASE)


def determine_sequence_base_name(project_code, primary_file, fallback_hook_idx, variant_idx=0):
    raw_project = (project_code or "E000").strip() or "E000"
    project_filtered = ''.join(ch for ch in raw_project if ch.isalnum() or ch == '_') or 'E000'
    project_code_clean = project_filtered.upper()
    fallback_variant = f"V{variant_idx}"
    fallback_hook = f"H{fallback_hook_idx}"

    variant_segment = fallback_variant
    hook_segment = fallback_hook
    extra_tokens = []

    base_name = ''
    if primary_file:
        base_name = os.path.splitext(os.path.basename(primary_file))[0].strip()

    variant_match = VARIANT_SEGMENT_PATTERN.search(base_name) if base_name else None
    if variant_match:
        variant_segment = f"V{variant_match.group(1)}"

    hook_match = H_SEGMENT_PATTERN.search(base_name) if base_name else None
    if hook_match:
        hook_segment = f"H{hook_match.group(1)}"

    if base_name:
        tokens = [token for token in base_name.split('_') if token]
        project_pattern = re.compile(re.escape(project_filtered), re.IGNORECASE)
        for token in tokens:
            cleaned = token.strip()
            if not cleaned:
                continue
            cleaned = project_pattern.sub('', cleaned, count=1)
            if variant_match:
                cleaned = cleaned.replace(variant_match.group(0), '', 1)
            if hook_match:
                cleaned = cleaned.replace(hook_match.group(0), '', 1)
            cleaned = cleaned.strip('_')
            cleaned = cleaned.strip()
            if not cleaned or cleaned.upper() == 'T_EN':
                continue
            extra_tokens.append(cleaned)

    if not variant_segment or len(variant_segment) == 1:
        variant_segment = f"V{variant_idx}"
    if not variant_segment.upper().startswith('V'):
        variant_segment = f"V{variant_segment}"

    if not hook_segment or not hook_segment.upper().startswith('H'):
        hook_segment = f"H{fallback_hook_idx}"

    combined_segment = f"{variant_segment}{hook_segment}"
    parts = [project_code_clean, combined_segment]
    parts.extend(extra_tokens)
    if not any(part.upper() == 'T_EN' for part in parts):
        parts.append('T_EN')

    candidate = '_'.join(part for part in parts if part)

    if not VARIANT_SEGMENT_PATTERN.search(candidate):
        candidate = candidate.replace(project_code_clean, f"{project_code_clean}_V{variant_idx}", 1)

    if not H_SEGMENT_PATTERN.search(candidate):
        candidate = candidate.replace('_T_EN', f"_H{fallback_hook_idx}_T_EN")

    return candidate


def build_sequence_name(base_name, intro_idx=None, project_code=None):
    fallback_project = (project_code or "E000").strip() or "E000"
    name = (base_name or '').strip()
    if not name:
        name = f"{fallback_project}_V0H0_T_EN"
    try:
        intro_value = 0 if intro_idx is None else int(intro_idx)
    except (TypeError, ValueError):
        intro_value = 0
    if name.endswith('_T_EN'):
        base = INTRO_SUFFIX_PATTERN.sub('', name[:-5])
        return f"{base}I{intro_value}_T_EN"
    base = INTRO_SUFFIX_PATTERN.sub('', name)
    return f"{base}_I{intro_value}"


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
    def __init__(self, parent, index, on_delete_callback, files=None, allow_rename=True, name=None, duplicate_callback=None, export_checkbox=False):
        super().__init__(parent)
        self.configure(style='Section.TLabelframe')
        self.files = [os.path.abspath(f) for f in files] if files else []
        self.on_delete_callback = on_delete_callback
        self.duplicate_callback = duplicate_callback
        self.export_var = tk.BooleanVar(value=True) if export_checkbox else None
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
            from utils import get_video_duration, concat_and_trim_videos, ensure_folder_for_export
            total_duration = get_video_duration(first_file)
            mm = int(total_duration // 60)
            ss = int(total_duration % 60)
            base_name = os.path.splitext(os.path.basename(first_file))[0]
            output_name = f"{base_name}_({mm:02d}'{ss:02d}).mp4"
            out_dir = ensure_folder_for_export(first_file, folder_name="2min")
            output_path = os.path.join(out_dir, output_name)
            concat_and_trim_videos(self.files, output_path, duration_sec=120)
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
    def __init__(self, parent, get_global_resolution_ref, get_hooks_compilations, get_tips_compilations, get_project_code, get_intro_files=None, export_tips_callback=None):
        self.parent = parent
        self.get_global_resolution_ref = get_global_resolution_ref
        self.get_hooks_compilations = get_hooks_compilations
        self.get_tips_compilations = get_tips_compilations
        self.get_project_code = get_project_code
        self.get_intro_files = get_intro_files or (lambda: [])
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



    def _build_sequence_name(self, base_name, intro_idx=None):
        project_code = self.get_project_code()
        return build_sequence_name(base_name, intro_idx, project_code)





    def add_empty_sequence(self):
        idx = len(self.sequence_frames)
        base_name = self._determine_sequence_base_name(None, idx)
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
            fallback_name = self._determine_sequence_base_name(None, i)
            seq.set_name(self._build_sequence_name(fallback_name))


    def duplicate_sequence(self, frame):
        idx = self.sequence_frames.index(frame)
        new_frame = SequenceCompilationFrame(
            self.container_sequences.scrollable_frame,
            index=idx+1,
            on_delete_callback=self.remove_sequence,
            duplicate_callback=self.duplicate_sequence,
            allow_rename=True,
            name=self._build_sequence_name(self._determine_sequence_base_name(None, idx + 1)),
            files=frame.files.copy(),
            export_checkbox=True
        )
        new_frame.pack_forget()
        self.sequence_frames.insert(idx+1, new_frame)
        for cf in self.sequence_frames:
            cf.pack_forget()
            cf.pack(fill="x", pady=5)
        for i, seq in enumerate(self.sequence_frames):
            fallback_name = self._determine_sequence_base_name(None, i)
            seq.set_name(self._build_sequence_name(fallback_name))


    def load_sequences(self):
        for frame in getattr(self, "sequence_frames", []):
            frame.destroy()
        self.sequence_frames = []

        tips_compilations = self.get_tips_compilations()
        hooks_compilations = self.get_hooks_compilations()
        intro_files = list(self.get_intro_files() or [])

        if not tips_compilations or not tips_compilations[0].files:
            return

        base_tip_files = list(tips_compilations[0].files)

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

        def add_sequence_variants(base_name: str, tip_files, hook_file=None):
            tip_list = list(tip_files)
            if hook_file:
                base_sequence = [hook_file] + tip_list
                append_sequence(self._build_sequence_name(base_name, 0), base_sequence)
                for intro_idx, intro_path in enumerate(intro_files, start=1):
                    sequence_files = [hook_file, intro_path] + tip_list
                    append_sequence(self._build_sequence_name(base_name, intro_idx), sequence_files)
            else:
                base_sequence = list(tip_list)
                append_sequence(self._build_sequence_name(base_name, 0), base_sequence)
                for intro_idx, intro_path in enumerate(intro_files, start=1):
                    sequence_files = [intro_path] + tip_list
                    append_sequence(self._build_sequence_name(base_name, intro_idx), sequence_files)

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
