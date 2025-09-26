from compilations import ScrollableFrame, FileItem
from utils import get_video_resolution, ensure_folder_for_export, safe_filename, get_ffmpeg_path
from tkinter import ttk, messagebox, filedialog
import tkinter as tk
import os
import tempfile
import subprocess

class ManualCompilationFrame(ttk.LabelFrame):
    def __init__(self, parent, title, files, on_delete_callback, allow_rename=True, duplicate_callback=None, export_checkbox=True):
        super().__init__(parent)
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

    def export(self):
        if not self.files or not self.should_export():
            return False
        try:
            first_file = self.files[0]
            base_dir = os.path.dirname(first_file)
            out_dir = os.path.join(base_dir, "sequences", "comp2")
            os.makedirs(out_dir, exist_ok=True)
            name = self.get_name() or "compilation"
            safe_name = safe_filename(name) + ".mp4"
            output_path = os.path.join(out_dir, safe_name)
            with tempfile.TemporaryDirectory() as tmpdir:
                concat_list = os.path.join(tmpdir, "files.txt")
                with open(concat_list, "w", encoding="utf-8") as f:
                    for video_path in self.files:
                        f.write(f"file '{video_path}'\n")
                ffmpeg_path = get_ffmpeg_path()
                cmd = [
                    ffmpeg_path, "-y", "-f", "concat", "-safe", "0",
                    "-i", concat_list,
                    "-c", "copy", output_path
                ]
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode != 0:
                    with open(os.path.join(out_dir, "export_error.log"), "a", encoding="utf-8") as logf:
                        logf.write(f"CMD: {' '.join(cmd)}\n")
                        logf.write(f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\n")
                    return False
            return True
        except Exception as e:
            with open(os.path.join(out_dir, "export_error.log"), "a", encoding="utf-8") as logf:
                logf.write(str(e))
            return False
import tkinter as tk
from tkinter import ttk
import platform

class NextBatchFrame(ttk.Frame):
    def __init__(self, parent, back_callback, get_project_code):
        super().__init__(parent)
        self.get_project_code = get_project_code
        self.compilation_frames = []
        self.hooks_compilation_frames = []
        self.tips_files = []
        self.hooks_files = []
        self.generated_from_table = []

        # Główna ramka na 3 kolumny
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        main.columnconfigure(0, weight=1)  # Panel boczny
        main.columnconfigure(1, weight=3)  # Without Hooks
        main.columnconfigure(2, weight=3)  # With Hooks
        main.rowconfigure(0, weight=1)

        # LEWA kolumna - panel sterowania
        left = ttk.Frame(main)
        left.grid(row=0, column=0, sticky="nsew")
        ttk.Button(left, text="Back to Menu", command=back_callback).pack(anchor="nw", padx=8, pady=(10, 2))
        ttk.Label(left, text="Next Batch Tools", font=("Arial", 15, "bold")).pack(pady=(8,8))
        self.btn_load_tips = ttk.Button(left, text="Load Tips Files", command=self.load_tips_files)
        self.btn_load_tips.pack(pady=5, fill="x")
        self.btn_load_hooks = ttk.Button(left, text="Load Hooks Files", command=self.load_hooks_files)
        self.btn_load_hooks.pack(pady=5, fill="x")
        self.btn_add_manual = ttk.Button(left, text="Add Empty Compilation", command=self.add_empty_compilation)
        self.btn_add_manual.pack(pady=5, fill="x")
        self.btn_export_sequences = ttk.Button(left, text="Export All", command=self.export_sequences)
        self.btn_export_sequences.pack(pady=10, fill="x")
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(left, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", padx=2, pady=(0,10))
        # ...panel boczny left...
        self.columns_var = tk.StringVar(value="2")  # domyślnie 2 kolumny
        ttk.Label(left, text="Columns (Without Hooks):").pack(pady=(10, 0))
        self.columns_entry = ttk.Entry(left, textvariable=self.columns_var, width=4, justify="center")
        self.columns_entry.pack(pady=(0, 8))

        # Dodaj guzik do zatwierdzania, ale możesz też wykonać relayout przy każdej zmianie
        ttk.Button(left, text="Apply Columns", command=self.on_change_columns).pack(pady=(0, 10))

        # ŚRODKOWA kolumna - WITHOUT HOOKS
        center = ttk.Frame(main, relief="solid", borderwidth=1)
        center.grid(row=0, column=1, sticky="nsew", padx=(8,4), pady=4)
        center.rowconfigure(0, weight=1)
        center.columnconfigure(0, weight=1)
        self.label_no_hooks = ttk.Label(center, text="Without Hooks", font=("Arial", 16, "bold"))
        self.label_no_hooks.grid(row=0, column=0, padx=8, pady=(10, 3), sticky="w")
        self.container = ttk.Frame(center)
        self.container.grid(row=0, column=0, sticky="nsew", padx=10, pady=4)

        # PRAWA kolumna - WITH HOOKS
        right = ttk.Frame(main, relief="solid", borderwidth=1)
        right.grid(row=0, column=2, sticky="nsew", padx=(4,8), pady=4)
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)
        self.label_with_hooks = ttk.Label(right, text="With Hooks", font=("Arial", 16, "bold"))
        self.label_with_hooks.pack(padx=8, pady=(10, 3))
        self.hooks_container = ScrollableFrame(right)
        self.hooks_container.pack(fill="both", expand=True, padx=10, pady=(4,10))

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

    def _format_hook_name(self, variant_idx, hook_idx):
        code = self._project_code_value()
        descriptor = f"V{variant_idx}H{hook_idx}"
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
        self.tips_files = []
        self.reset_compilations()
        for path in filepaths:
            self.tips_files.append(os.path.abspath(path))
        if self.tips_files:
            self.add_compilation_from_files(self.tips_files)
        self.rebuild_hook_combinations()
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

        for hook_idx, hook_path in enumerate(self.hooks_files, start=1):
            for idx, base_comp in enumerate(self.compilation_frames):
                files = [hook_path] + base_comp.files
                name = self._format_hook_name(idx, hook_idx)
                cf = ManualCompilationFrame(
                    self.hooks_container.scrollable_frame,
                    title=name,
                    files=files,
                    on_delete_callback=lambda f: f.destroy(),
                    allow_rename=True,
                    duplicate_callback=None,
                    export_checkbox=True
                )
                cf.pack(fill="x", pady=4)
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

    def export_sequences(self):
        export_list = [cf for cf in self.compilation_frames if cf.should_export()]
        hooks_list = [cf for cf in self.hooks_compilation_frames if cf.should_export()]
        total = len(export_list) + len(hooks_list)
        if not total:
            messagebox.showinfo("Export", "No compilations to export (none selected for export).")
            return
        base_res = None
        for cf in export_list + hooks_list:
            for f in cf.files:
                if not base_res:
                    base_res = get_video_resolution(f)
                elif get_video_resolution(f) != base_res:
                    messagebox.showerror("Resolution mismatch", "Not all files in all compilations have the same resolution!")
                    return
        self.progress_var.set(0)
        errors = []
        all_frames = export_list + hooks_list
        for idx, cf in enumerate(all_frames):
            try:
                ok = cf.export()
                if not ok:
                    errors.append(f"{cf.get_name()}")
            except Exception as e:
                errors.append(f"{cf.get_name()}: {e}")
            self.progress_var.set(100*(idx+1)/total)
            self.update()
        if errors:
            messagebox.showerror("Export error", "\n".join(errors))
        else:
            messagebox.showinfo("Export", f"Exported {len(all_frames)} compilations to sequences/comp2 folders.")
