"""Interface Tkinter para montar compilacoes manuais nas entregas seguintes."""

from legopy.ui.compilation_widgets import ScrollableFrame, FileItem, determine_sequence_base_name, build_sequence_name, infer_intro_token
from legopy.services.media import get_video_resolution, safe_filename, get_ffmpeg_path, resolve_export_roots, select_preferred_tip_variants, format_for_ffmpeg_concat
from tkinter import ttk, messagebox, filedialog
import tkinter as tk
import os
import tempfile
import subprocess

class ManualCompilationFrame(ttk.LabelFrame):
    def __init__(self, parent, title, files, on_delete_callback, allow_rename=True, duplicate_callback=None, export_checkbox=True):
        super().__init__(parent)
        self.configure(style='Section.TLabelframe')
        self.on_delete_callback = on_delete_callback
        self.files = [os.path.abspath(f) for f in files if f]
        self.file_items = []
        self.allow_rename = allow_rename
        self.duplicate_callback = duplicate_callback
        self.export_var = tk.BooleanVar(value=True) if export_checkbox else None
        self.name_var = tk.StringVar(value=title)
        ttk.Label(self, text="Name:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        self.name_entry = ttk.Entry(self, textvariable=self.name_var, width=28)
        self.name_entry.grid(row=0, column=1, padx=2, pady=4, sticky="ew")
        ttk.Button(self, text="Clear Compilation", command=self.delete_this_compilation).grid(row=0, column=2, padx=2, pady=4, sticky="e")
        if duplicate_callback:
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

    def export(self):
        if not self.files or not self.should_export():
            return False
        try:
            first_file = self.files[0]
            _, sequences_dir = resolve_export_roots(first_file)
            os.makedirs(sequences_dir, exist_ok=True)
            name = self.get_name() or "compilation"
            safe_name = safe_filename(name) + ".mp4"
            output_path = os.path.join(sequences_dir, safe_name)
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
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode != 0:
                    error_log = os.path.join(sequences_dir, "manual_export_error.log")
                    with open(error_log, "a", encoding="utf-8") as logf:
                        logf.write(f"CMD: {' '.join(cmd)}\n")
                        logf.write(f"RET: {result.returncode}\n")
                        logf.write(f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}")
                    return False
            return True
        except Exception as e:
            error_log = os.path.join(sequences_dir if 'sequences_dir' in locals() else os.path.dirname(self.files[0]), "manual_export_error.log")
            with open(error_log, "a", encoding="utf-8") as logf:
                logf.write(str(e))
            return False
import tkinter as tk
from tkinter import ttk
import platform

class NextBatchFrame(ttk.Frame):
    def __init__(self, parent, back_callback, get_project_code):
        super().__init__(parent)
        self.configure(style='App.TFrame')
        self.get_project_code = get_project_code
        self.compilation_frames = []
        self.hooks_compilation_frames = []
        self.tips_files = []
        self.hooks_files = []
        self.intro_files = []
        self._intro_file_items = []
        self.generated_from_table = []

        # Main container split into three columns
        main = ttk.Frame(self, style='App.TFrame')
        main.pack(fill="both", expand=True, padx=10, pady=10)
        main.columnconfigure(0, weight=1)  # Side panel
        main.columnconfigure(1, weight=3)  # Without Hooks
        main.columnconfigure(2, weight=3)  # With Hooks
        main.rowconfigure(0, weight=1)

        # Left column - control panel
        left = ttk.Frame(main, style='Section.TFrame')
        left.grid(row=0, column=0, sticky="nsew")
        ttk.Button(left, text="Back to Menu", command=back_callback, style='Accent.TButton').pack(anchor="nw", padx=8, pady=(10, 2))
        ttk.Label(left, text="Next Batch Tools", font=("Arial", 15, "bold"), style='SectionHeading.TLabel').pack(pady=(8, 8))
        self.btn_load_tips = ttk.Button(left, text="Load Tips Files", command=self.load_tips_files, style='Accent.TButton')
        self.btn_load_tips.pack(pady=5, fill="x")
        self.btn_load_hooks = ttk.Button(left, text="Load Hooks Files", command=self.load_hooks_files, style='Accent.TButton')
        self.btn_load_hooks.pack(pady=5, fill="x")

        intros_frame = ttk.LabelFrame(left, text="Intros", style='Section.TLabelframe')
        intros_frame.pack(fill="both", expand=False, padx=8, pady=(10, 6))
        ttk.Button(intros_frame, text="Load Intro Files", command=self.load_intro_files, style='Accent.TButton').pack(fill="x", padx=6, pady=(6, 4))
        ttk.Button(intros_frame, text="Clear Intros", command=self.clear_intro_files).pack(fill="x", padx=6, pady=(0, 6))
        self.intros_container = ScrollableFrame(intros_frame, style='Section.TFrame', frame_style='Section.TFrame')
        self.intros_container.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        self.btn_add_manual = ttk.Button(left, text="Add Empty Compilation", command=self.add_empty_compilation)
        self.btn_add_manual.pack(pady=5, fill="x")
        self.btn_export_sequences = ttk.Button(left, text="Export All", command=self.export_sequences, style='Accent.TButton')
        self.btn_export_sequences.pack(pady=10, fill="x")
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(left, variable=self.progress_var, maximum=100, style='Accent.Horizontal.TProgressbar')
        self.progress_bar.pack(fill="x", padx=2, pady=(0, 10))
        self.columns_var = tk.StringVar(value="2")  # default to 2 columns
        ttk.Label(left, text="Columns (Without Hooks):").pack(pady=(10, 0))
        self.columns_entry = ttk.Entry(left, textvariable=self.columns_var, width=4, justify="center")
        self.columns_entry.pack(pady=(0, 8))
        ttk.Button(left, text="Apply Columns", command=self.on_change_columns).pack(pady=(0, 10))

        # Middle column - without hooks
        center = ttk.Frame(main, style='Section.TFrame', relief="solid", borderwidth=1)
        center.grid(row=0, column=1, sticky="nsew", padx=(8, 4), pady=4)
        center.rowconfigure(0, weight=1)
        center.columnconfigure(0, weight=1)
        self.label_no_hooks = ttk.Label(center, text="Without Hooks", font=("Arial", 16, "bold"), style='SectionHeading.TLabel')
        self.label_no_hooks.grid(row=0, column=0, padx=8, pady=(10, 3), sticky="w")
        self.container = ttk.Frame(center, style='Section.TFrame')
        self.container.grid(row=0, column=0, sticky="nsew", padx=10, pady=4)

        # Right column - with hooks
        right = ttk.Frame(main, style='Section.TFrame', relief="solid", borderwidth=1)
        right.grid(row=0, column=2, sticky="nsew", padx=(4, 8), pady=4)
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)
        self.label_with_hooks = ttk.Label(right, text="With Hooks", font=("Arial", 16, "bold"), style='SectionHeading.TLabel')
        self.label_with_hooks.pack(padx=8, pady=(10, 3))
        self.hooks_container = ScrollableFrame(right, style='Section.TFrame', frame_style='Section.TFrame')
        self.hooks_container.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        # (opcjonalnie: guzik do dodawania pustej kompilacji do "With Hooks")
        # self.btn_add_empty_hook_comp = ttk.Button(right, text="Add Empty Compilation (With Hook)", command=self.add_empty_hook_compilation)
        # self.btn_add_empty_hook_comp.pack(pady=4, fill="x", padx=10)

        self.reset_compilations()


       # ttk.Label(left, text="1. Copy table from Excel (Ctrl+C)\n2. Click 'Paste' or paste manually:", font=("Arial", 10), foreground="#008").pack(pady=(12,2))
       # self.excel_text = tk.Text(left, height=8, width=30, wrap="none")
       # self.excel_text.pack(padx=2, pady=(2,2))
       # buttons_frame = ttk.Frame(left)
       # buttons_frame.pack(fill="x", pady=(1,3))
       # self.btn_paste = ttk.Button(buttons_frame, text="Paste", width=9, command=self.paste_from_clipboard)
       # self.btn_paste.pack(side="left", padx=(0,4))
       # self.btn_clear_table = ttk.Button(buttons_frame, text="Clear table", width=12, command=self.clear_excel_table)
       # self.btn_clear_table.pack(side="left", padx=(2,0))
       # self.btn_generate = ttk.Button(left, text="Generate compilations from table", command=self.paste_excel_table)
       # self.btn_generate.pack(pady=5, fill="x")
    def on_change_columns(self):
        try:
            num_cols = int(self.columns_var.get())
            if num_cols < 1:
                num_cols = 1
            self.columns_var.set(str(num_cols))
        except ValueError:
            self.columns_var.set("2")
        self.relayout_compilations()

    def _project_code_value(self):
        if callable(self.get_project_code):
            return (self.get_project_code() or "").strip()
        return ""

    def _format_tip_name(self, idx):
        code = self._project_code_value()
        descriptor = f"T{idx+1}"
        return f"{code}_{descriptor}_T_EN" if code else f"{descriptor}_T_EN"

    def relayout_compilations(self):
        for widget in self.container.winfo_children():
            widget.grid_forget()
        try:
            num_columns = int(self.columns_var.get())
            if num_columns < 1:
                num_columns = 1
        except Exception:
            num_columns = 2
        for idx, frame in enumerate(self.compilation_frames):
            row = idx // num_columns
            col = idx % num_columns
            frame.set_name(self._format_tip_name(idx))
            frame.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

    def load_tips_files(self):
        filepaths = filedialog.askopenfilenames(filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi *.flv *.wmv")])
        if not filepaths:
            return
        all_paths = [os.path.abspath(path) for path in filepaths]
        filtered_paths = select_preferred_tip_variants(all_paths, keep_all_variants=True)
        if not filtered_paths:
            messagebox.showwarning("Warning", "No Tips files selected after applying naming rules.")
            return
        skipped = len(all_paths) - len(filtered_paths)
        self.tips_files = filtered_paths
        self.reset_compilations()
        if self.tips_files:
            self.add_compilation_from_files(self.tips_files)
        self.rebuild_hook_combinations()
        if skipped:
            messagebox.showinfo("Loaded", f"Loaded {len(self.tips_files)} Tips files (skipped {skipped} due to naming rules).")
        else:
            messagebox.showinfo("Loaded", f"Loaded {len(self.tips_files)} Tips files.")

    def load_hooks_files(self):
        filepaths = filedialog.askopenfilenames(filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi *.flv *.wmv")])
        if not filepaths:
            return
        for path in filepaths:
            abspath = os.path.abspath(path)
            if abspath not in self.hooks_files:
                self.hooks_files.append(abspath)
        self.rebuild_hook_combinations()
        messagebox.showinfo("Loaded", f"Loaded {len(filepaths)} new Hooks files (total: {len(self.hooks_files)})")

    def load_intro_files(self):
        filepaths = filedialog.askopenfilenames(filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi *.flv *.wmv")])
        if not filepaths:
            return
        self.intro_files = [os.path.abspath(path) for path in filepaths]
        self._refresh_intro_items()

    def _refresh_intro_items(self):
        for item in getattr(self, '_intro_file_items', []):
            item.destroy()
        self._intro_file_items = []
        for idx, path in enumerate(self.intro_files):
            item = FileItem(
                self.intros_container.scrollable_frame,
                path,
                lambda i=idx: self.move_intro_up(i),
                lambda i=idx: self.move_intro_down(i),
                lambda i=idx: self.delete_intro(i)
            )
            item.grid(row=idx, column=0, sticky="w")
            self._intro_file_items.append(item)

    def move_intro_up(self, index):
        if index > 0:
            self.intro_files[index - 1], self.intro_files[index] = self.intro_files[index], self.intro_files[index - 1]
            self._refresh_intro_items()

    def move_intro_down(self, index):
        if index < len(self.intro_files) - 1:
            self.intro_files[index + 1], self.intro_files[index] = self.intro_files[index], self.intro_files[index + 1]
            self._refresh_intro_items()

    def delete_intro(self, index):
        if 0 <= index < len(self.intro_files):
            del self.intro_files[index]
            self._refresh_intro_items()

    def clear_intro_files(self):
        if not self.intro_files:
            return
        self.intro_files = []
        self._refresh_intro_items()

    # def paste_from_clipboard(self):
    #     try:
    #         self.excel_text.delete("1.0", tk.END)
    #         raw = self.clipboard_get()
    #         self.excel_text.insert("1.0", raw)
    #     except tk.TclError:
    #         messagebox.showwarning("Clipboard error", "Clipboard error.")

    # def clear_excel_table(self):
    #     self.excel_text.delete("1.0", tk.END)
    #     for cf in self.generated_from_table:
    #         cf.destroy()
    #     self.generated_from_table = []
    #     self.rebuild_hook_combinations()

    # def paste_excel_table(self):
    #     raw = self.excel_text.get("1.0", tk.END).strip()
    #     if not raw:
    #         messagebox.showwarning("No table", "No table to paste.")
    #         return
    #     if not self.tips_files or len(self.tips_files) == 0:
    #         messagebox.showwarning("No tips", "Load Tips files first!")
    #         return
    #     try:
    #         rows = [r for r in raw.strip().split('\n') if r]
    #         data = [row.split('\t') for row in rows]
    #         if not data or len(data) < 2:
    #             messagebox.showwarning("Table error", "Table error!")
    #             return
    #         headers = data[0]
    #         columns = list(zip(*data[1:]))
    #         alias_to_path = {}
    #         for path in self.tips_files:
    #             base = os.path.basename(path)
    #             idx = self.tips_files.index(path)
    #             alias = f"T{idx+1}"
    #             alias_to_path[alias.upper()] = path
    #         self.generated_from_table = []
    #         for col_idx, col_name in enumerate(headers):
    #             files_aliases = columns[col_idx]
    #             files_real = []
    #             for alias in files_aliases:
    #                 alias_lc = alias.strip().upper()
    #                 if alias_lc in alias_to_path:
    #                     files_real.append(alias_to_path[alias_lc])
    #             cf = self.add_compilation_from_files(files_real, table_label=col_name)
    #             self.generated_from_table.append(cf)
    #         self.rebuild_hook_combinations()
    #     except Exception as e:
    #         messagebox.showwarning("Table error", f"Error: {e}")

    def add_compilation_from_files(self, files, table_label=None):
        idx = len(self.compilation_frames)
        name = self._format_tip_name(idx)
        frame = ManualCompilationFrame(
            self.container,
            title=name,
            files=[f for f in files if f],
            on_delete_callback=self.remove_compilation_frame,
            allow_rename=True,
            duplicate_callback=self.duplicate_compilation,
            export_checkbox=True
        )
       # frame.pack(fill="x", pady=6)
        self.compilation_frames.append(frame)
        self.relayout_compilations()
       # self.update_compilation_names()
        return frame

    def add_empty_compilation(self):
        self.add_compilation_from_files([])

    def remove_compilation_frame(self, frame):
        frame.destroy()
        if frame in self.generated_from_table:
            self.generated_from_table.remove(frame)
        self.compilation_frames.remove(frame)
        self.update_compilation_names()
        self.rebuild_hook_combinations()
        self.relayout_compilations()

    def duplicate_compilation(self, frame):
        idx = self.compilation_frames.index(frame)
        project_code = self._project_code_value()
        old_name = frame.get_name()
        if project_code and old_name.startswith(project_code + "_"):
            base_name = old_name[len(project_code) + 1:]  # +1 to "_"
        else:
            base_name = old_name
        new_name = f"{project_code}_{base_name}_copy" if project_code else f"{base_name}_copy"
        cf = ManualCompilationFrame(
            self.container,
            title=new_name,
            files=frame.files.copy(),
            on_delete_callback=self.remove_compilation_frame,
            allow_rename=True,
            duplicate_callback=self.duplicate_compilation,
            export_checkbox=True
        )
       # cf.pack_forget()
        self.compilation_frames.insert(idx+1, cf)
        # for f in self.compilation_frames:
        #     f.pack_forget()
        #     f.pack(fill="x", pady=6)
        self.update_compilation_names()
        self.relayout_compilations()
        self.rebuild_hook_combinations()

    def update_compilation_names(self):
        for idx, frame in enumerate(self.compilation_frames):
            frame.set_name(self._format_tip_name(idx))

    def rebuild_hook_combinations(self):
        for cf in getattr(self, "hooks_compilation_frames", []):
            cf.destroy()
        self.hooks_compilation_frames = []

        if not self.hooks_files or not self.compilation_frames:
            return

        project_code = self._project_code_value()
        for hook_idx, hook_path in enumerate(self.hooks_files, start=1):
            hook_abs = os.path.abspath(hook_path)
            for idx, base_comp in enumerate(self.compilation_frames):
                base_files = list(base_comp.files)
                if not base_files:
                    continue
                base_name = determine_sequence_base_name(project_code, hook_abs, fallback_hook_idx=hook_idx, variant_idx=idx)
                frame_name = build_sequence_name(base_name, None, project_code)
                files = [hook_abs] + base_files
                cf = ManualCompilationFrame(
                    self.hooks_container.scrollable_frame,
                    title=frame_name,
                    files=files,
                    on_delete_callback=lambda f: f.destroy(),
                    allow_rename=True,
                    duplicate_callback=None,
                    export_checkbox=True
                )
                cf.pack(fill="x", pady=4)
                cf.hook_path = hook_abs
                cf.variant_index = idx
                cf.hook_index = hook_idx
                self.hooks_compilation_frames.append(cf)



    def reset_compilations(self):
        for cf in getattr(self, "compilation_frames", []):
            cf.destroy()
        self.compilation_frames = []
        for cf in getattr(self, "hooks_compilation_frames", []):
            cf.destroy()
        self.hooks_compilation_frames = []
        self.generated_from_table = []
        if hasattr(self, "excel_text"):
            self.excel_text.delete("1.0", tk.END)

    def _export_sequence(self, files, sequence_name):
        if not files:
            return False
        try:
            first_file = files[0]
            _, sequences_dir = resolve_export_roots(first_file)
            os.makedirs(sequences_dir, exist_ok=True)
            safe_name = safe_filename(sequence_name) + ".mp4"
            output_path = os.path.join(sequences_dir, safe_name)
            with tempfile.TemporaryDirectory() as tmpdir:
                concat_list = os.path.join(tmpdir, "files.txt")
                with open(concat_list, "w", encoding="utf-8") as f:
                    for video_path in files:
                        f.write(f"file '{format_for_ffmpeg_concat(video_path)}'\n")
                ffmpeg_path = get_ffmpeg_path()
                cmd = [
                    ffmpeg_path, "-y", "-f", "concat", "-safe", "0",
                    "-i", concat_list,
                    "-c", "copy", output_path
                ]
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode != 0:
                    error_log = os.path.join(sequences_dir, "sequence_export_error.log")
                    with open(error_log, "a", encoding="utf-8") as logf:
                        logf.write(f"CMD: {' '.join(cmd)}\n")
                        logf.write(f"RET: {result.returncode}\n")
                        logf.write(f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}")
                    return False
            return True
        except Exception as e:
            fallback_dir = sequences_dir if 'sequences_dir' in locals() else os.path.dirname(files[0])
            error_log = os.path.join(fallback_dir, "sequence_export_error.log")
            with open(error_log, "a", encoding="utf-8") as logf:
                logf.write(str(e))
            return False


    def export_sequences(self):
        intro_files = list(self.intro_files)
        intro_entries = [
            (idx, intro_path, infer_intro_token(intro_path, idx))
            for idx, intro_path in enumerate(intro_files, start=1)
        ]
        base_entries = [(idx, frame) for idx, frame in enumerate(self.compilation_frames) if frame.should_export()]
        hook_entries = [frame for frame in self.hooks_compilation_frames if frame.should_export()]
        if not base_entries and not hook_entries:
            messagebox.showinfo("Export", "No compilations to export (none selected for export).")
            return

        project_code = self._project_code_value()
        intro_count = len(intro_files)
        total = sum(1 + intro_count for _, _ in base_entries) + sum(1 + intro_count for _ in hook_entries)
        if total == 0:
            messagebox.showinfo("Export", "No compilations to export (none selected for export).")
            return

        base_res = None

        def check_resolution(path):
            nonlocal base_res
            res = get_video_resolution(path)
            if not res:
                return True
            if base_res is None:
                base_res = res
                return True
            return res == base_res

        for frame in [f for _, f in base_entries] + hook_entries:
            for video_path in frame.files:
                if not check_resolution(video_path):
                    messagebox.showerror("Resolution mismatch", "Not all files in all compilations have the same resolution!")
                    return
        for intro_path in intro_files:
            if not check_resolution(intro_path):
                messagebox.showerror("Resolution mismatch", "Not all files in all compilations have the same resolution!")
                return

        errors = []
        processed = 0
        success = 0

        for idx, frame in base_entries:
            base_name_seed = determine_sequence_base_name(
                project_code,
                frame.files[0] if frame.files else None,
                fallback_hook_idx=0,
                variant_idx=idx,
            )
            sequences = []
            base_display = build_sequence_name(base_name_seed, None, project_code)
            sequences.append((base_display, list(frame.files)))
            for intro_idx, intro_path, intro_token in intro_entries:
                seq_files = [intro_path] + list(frame.files)
                seq_name = build_sequence_name(
                    base_name_seed,
                    intro_idx,
                    project_code,
                    intro_token=intro_token,
                )
                sequences.append((seq_name, seq_files))
            for name, files in sequences:
                if self._export_sequence(files, name):
                    success += 1
                else:
                    errors.append(name)
                processed += 1
                self.progress_var.set(100 * processed / total)
                self.update()

        for frame in hook_entries:
            hook_abs = getattr(frame, 'hook_path', frame.files[0] if frame.files else None)
            if not hook_abs:
                continue
            hook_abs = os.path.abspath(hook_abs)
            tips = []
            hook_consumed = False
            for path in frame.files:
                abs_path = os.path.abspath(path)
                if not hook_consumed and abs_path == hook_abs:
                    hook_consumed = True
                    continue
                tips.append(path)
            base_name_seed = determine_sequence_base_name(
                project_code,
                hook_abs,
                fallback_hook_idx=getattr(frame, 'hook_index', 0),
                variant_idx=getattr(frame, 'variant_index', 0),
            )
            name_override = (frame.get_name() or "").strip()
            if name_override:
                base_display_name = name_override
                build_seed = name_override
            else:
                base_display_name = build_sequence_name(base_name_seed, None, project_code)
                build_seed = base_name_seed
            sequences = []
            sequences.append((base_display_name, [hook_abs] + list(tips)))
            for intro_idx, intro_path, intro_token in intro_entries:
                seq_name = build_sequence_name(
                    build_seed,
                    intro_idx,
                    project_code,
                    intro_token=intro_token,
                )
                seq_files = [hook_abs, intro_path] + list(tips)
                sequences.append((seq_name, seq_files))
            for name, files in sequences:
                if self._export_sequence(files, name):
                    success += 1
                else:
                    errors.append(name)
                processed += 1
                self.progress_var.set(100 * processed / total)
                self.update()

        self.progress_var.set(0)
        if errors:
            messagebox.showerror("Export error", "\n".join(errors))
        else:
            messagebox.showinfo("Export", f"Exported {success} compilations to Sequences_RealLength folders.")
