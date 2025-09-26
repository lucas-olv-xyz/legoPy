import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from utils import (
    get_video_resolution,
    get_video_duration,
    concat_and_trim_videos,
    ensure_folder_for_export,
    safe_filename,
    get_ffmpeg_path,
    format_for_ffmpeg_concat
)

class FileItem(tk.Frame):
    def __init__(self, parent, filepath, move_up_cb, move_down_cb, delete_cb):
        super().__init__(parent)
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
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

class BaseCompilationFrame(ttk.LabelFrame):
    def __init__(self, parent, index, on_delete_callback, files=None, allow_rename=True, name=None, duplicate_callback=None, export_checkbox=False):
        super().__init__(parent)
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
        self.files_frame = ttk.Frame(self)
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
        self.files_frame = ttk.Frame(self)
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

    # --- Sequence Compilation export to 'sequences/comp1'
    def export(self, duration_sec=120):
        if not self.files or not self.should_export():
            return False
        try:
            name = self.get_name() or "sequence"
            safe_name = safe_filename(name) + ".mp4"
            first_file = self.files[0]
            base_dir = os.path.dirname(first_file)
            out_dir = os.path.join(base_dir, "sequences", "comp1")
            os.makedirs(out_dir, exist_ok=True)
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
                    with open(os.path.join(out_dir, "sequence_export_error.log"), "w", encoding="utf-8") as logf:
                        logf.write(f"CMD: {' '.join(cmd)}\n")
                        logf.write(f"RET: {result.returncode}\n")
                        logf.write(f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}")
                    return False
            return True
        except Exception as e:
            with open(os.path.join(out_dir, "sequence_export_error.log"), "a", encoding="utf-8") as logf:
                logf.write(str(e))
            return False

class SequenceCompilationsManager:
    def __init__(self, parent, get_global_resolution_ref, get_hooks_compilations, get_tips_compilations, get_project_code, get_intro_files=None):
        self.parent = parent
        self.get_global_resolution_ref = get_global_resolution_ref
        self.get_hooks_compilations = get_hooks_compilations
        self.get_tips_compilations = get_tips_compilations
        self.get_project_code = get_project_code
        self.get_intro_files = get_intro_files or (lambda: [])
        self.sequence_frames = []
        self.progress_var = tk.DoubleVar()

        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", pady=(10, 0))
        ttk.Label(button_frame, text="Sequence Compilations", font=("Arial", 15, "bold")).pack(anchor="center")
        self.btn_add_empty_sequence = ttk.Button(button_frame, text="Add Empty Sequence Compilation", command=self.add_empty_sequence)
        self.btn_add_empty_sequence.pack(pady=5)
        self.container_sequences = ScrollableFrame(parent)
        self.container_sequences.pack(fill="both", expand=True, padx=5, pady=5)
        self.progress_bar = ttk.Progressbar(parent, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side="bottom", fill="x", padx=20, pady=(0,2))
        export_frame = ttk.Frame(parent)
        export_frame.pack(side="bottom", fill="x", padx=20, pady=(2, 12))
        self.btn_export_sequences = ttk.Button(export_frame, text="Export Sequence Compilations", command=self.export_sequences)
        self.btn_export_sequences.pack(anchor="center")

    def _build_sequence_name(self, variant_idx, hook_idx, intro_idx=None):
        project_code = self.get_project_code() or "E000"
        descriptor = f"V{variant_idx}H{hook_idx}"
        if intro_idx is not None:
            descriptor += f"I{intro_idx}"
        return f"{project_code}_{descriptor}_T_EN"

    def add_empty_sequence(self):
        idx = len(self.sequence_frames)
        name = self._build_sequence_name(idx, 0)
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
            seq.set_name(self._build_sequence_name(i, 0))

    def duplicate_sequence(self, frame):
        idx = self.sequence_frames.index(frame)
        new_frame = SequenceCompilationFrame(
            self.container_sequences.scrollable_frame,
            index=idx+1,
            on_delete_callback=self.remove_sequence,
            duplicate_callback=self.duplicate_sequence,
            allow_rename=True,
            name=self._build_sequence_name(idx + 1, 0),
            files=frame.files.copy(),
            export_checkbox=True
        )
        new_frame.pack_forget()
        self.sequence_frames.insert(idx+1, new_frame)
        for cf in self.sequence_frames:
            cf.pack_forget()
            cf.pack(fill="x", pady=5)
        for i, seq in enumerate(self.sequence_frames):
            seq.set_name(self._build_sequence_name(i, 0))

    def load_sequences(self):
        for frame in getattr(self, "sequence_frames", []):
            frame.destroy()
        self.sequence_frames = []

        tips_compilations = self.get_tips_compilations()
        hooks_compilations = self.get_hooks_compilations()
        intro_files = list(self.get_intro_files() or [])

        if not tips_compilations or not tips_compilations[0].files:
            return

        base_tip_files = tips_compilations[0].files
        base_sequences = [(0, 0, base_tip_files.copy())]

        for idx, hook_comp in enumerate(hooks_compilations, start=1):
            if not hook_comp.files:
                continue
            combined_files = hook_comp.files[:1] + base_tip_files
            base_sequences.append((0, idx, combined_files))

        def append_sequence(name: str, files):
            seq_frame = SequenceCompilationFrame(
                self.container_sequences.scrollable_frame,
                index=len(self.sequence_frames),
                on_delete_callback=self.remove_sequence,
                duplicate_callback=self.duplicate_sequence,
                allow_rename=True,
                name=name,
                files=files,
                export_checkbox=True
            )
            seq_frame.pack(fill="x", pady=5)
            self.sequence_frames.append(seq_frame)

        for variant_idx, hook_idx, files in base_sequences:
            if intro_files:
                for intro_idx, intro_path in enumerate(intro_files):
                    name = self._build_sequence_name(variant_idx, hook_idx, intro_idx)
                    append_sequence(name, [intro_path] + files)
            else:
                name = self._build_sequence_name(variant_idx, hook_idx)
                append_sequence(name, files)

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
            messagebox.showinfo("Export", f"Exported {count} sequence compilations to sequences/comp1 folders.")
