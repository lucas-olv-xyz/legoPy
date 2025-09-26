from compilations import (
    ScrollableFrame, CompilationFrame, SequenceCompilationsManager,
    get_video_duration, FileItem
)
from tkinter import ttk, messagebox, filedialog
import tkinter as tk
import threading
import os

def format_first_file_duration(duration):
    m = int(duration // 60)
    s = int(duration % 60)
    return f"{m:02d}'{s:02d}"

class FirstBatchFrame(ttk.Frame):
    def __init__(self, parent, back_callback, get_project_code):
        super().__init__(parent)
        self.get_project_code = get_project_code

        ttk.Button(self, text="Back to Menu", command=back_callback).pack(anchor="nw", padx=8, pady=(10, 2))

        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=4, pady=4)
        main_frame.columnconfigure(0, weight=2)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)

        left_col = ttk.Frame(main_frame)
        left_col.grid(row=0, column=0, sticky="nsew")
        right_col = ttk.Frame(main_frame, relief="solid", borderwidth=1)
        right_col.grid(row=0, column=1, sticky="nsew")

        ttk.Label(left_col, text="Tips Compilations", font=("Arial", 17, "bold"), anchor="center").pack(anchor="center", padx=8, pady=(15, 8))
        self.global_resolution_ref = {"value": None}
        self.compilations = []
        self.hooks_compilations = []
        self.intro_files = []
        self._intro_file_items = []

        ttk.Label(left_col, text="Load Tips:").pack(anchor="w", padx=5, pady=(5,0))
        ttk.Button(left_col, text="Load Tips Files", command=self.load_tips_files).pack(padx=5, pady=5)
        ttk.Button(left_col, text="Add empty Tips compilation", command=self.add_empty_tips_compilation).pack(padx=5, pady=(0,5))
        self.container_tips = ScrollableFrame(left_col)
        self.container_tips.pack(fill="both", expand=True, padx=5, pady=5)

        ttk.Separator(left_col, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(left_col, text="Load Hooks:").pack(anchor="w", padx=5, pady=(5,0))
        ttk.Button(left_col, text="Load Hooks Files", command=self.load_hooks_files).pack(padx=5, pady=5)
        ttk.Button(left_col, text="Add empty Hooks compilation", command=self.add_empty_hooks_compilation).pack(padx=5, pady=(0,5))
        self.container_hooks = ScrollableFrame(left_col)
        self.container_hooks.pack(fill="both", expand=True, padx=5, pady=5)

        ttk.Separator(left_col, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(left_col, text="Load Intros:").pack(anchor="w", padx=5, pady=(5,0))
        ttk.Button(left_col, text="Load Intro Files", command=self.load_intro_files).pack(padx=5, pady=5)
        self.container_intros = ScrollableFrame(left_col)
        self.container_intros.pack(fill="both", expand=True, padx=5, pady=5)

        export_frame = ttk.Frame(left_col)
        export_frame.pack(fill="x", pady=(12, 0))
        self.btn_process_all = ttk.Button(export_frame, text="Export Tips Compilations", command=self.start_processing_thread)
        self.btn_process_all.pack(anchor="center", pady=(0, 4))
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(export_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", padx=14, pady=(0, 8))

        # PRAWA KOLUMNA: SequenceCompilationsManager
        self.sequence_manager = SequenceCompilationsManager(
            right_col,
            get_global_resolution_ref=lambda: self.global_resolution_ref,
            get_hooks_compilations=lambda: self.hooks_compilations,
            get_tips_compilations=lambda: self.compilations,
            get_project_code=self.get_project_code,
            get_intro_files=lambda: self.intro_files
        )

        # --- DODAJ TO: --- (po sequence_manager!)
        # Global progress bar (na samym dole)
        self.global_progress_var = tk.DoubleVar()
        self.global_progress_bar = ttk.Progressbar(self, variable=self.global_progress_var, maximum=100)
        self.global_progress_bar.pack(side="bottom", fill="x", padx=24, pady=(0, 2))

        # Export All Compilations button (na dole, środek)
        all_export_frame = ttk.Frame(self)
        all_export_frame.pack(side="bottom", fill="x", padx=20, pady=(5, 12))
        self.btn_export_all = ttk.Button(all_export_frame, text="Export All Compilations", command=self.export_all_compilations)
        self.btn_export_all.pack(anchor="center")
        # --- KONIEC DODAWANIA ---

    def add_empty_tips_compilation(self):
        comp = CompilationFrame(
            self.container_tips.scrollable_frame,
            len(self.compilations),
            on_delete_callback=self.remove_tips_compilation,
            allow_rename=True
        )
        comp.pack(fill="x", pady=5)
        self.compilations.append(comp)
        self.update_compilation_numbers()

    def add_empty_hooks_compilation(self):
        comp = CompilationFrame(
            self.container_hooks.scrollable_frame,
            len(self.hooks_compilations),
            on_delete_callback=self.remove_hooks_compilation,
            allow_rename=True
        )
        comp.pack(fill="x", pady=5)
        self.hooks_compilations.append(comp)
        self.update_compilation_numbers()
        self.sequence_manager.load_sequences()

    def load_tips_files(self):
        filepaths = filedialog.askopenfilenames(filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi *.flv *.wmv")])
        if not filepaths:
            return
        self.clear_all_compilations()
        n = len(filepaths)
        for i in range(n):
            # ROTACJA (ważne!)
            rotated = filepaths[i:] + filepaths[:i]
            comp = CompilationFrame(
                self.container_tips.scrollable_frame, i,
                on_delete_callback=self.remove_tips_compilation,
                allow_rename=False
            )
            comp.add_files(rotated)
            comp.pack(fill="x", pady=5)
            self.compilations.append(comp)
        self.sync_hooks_with_tips1()
        self.update_compilation_numbers()
        self.sequence_manager.load_sequences()

    def load_hooks_files(self):
        filepaths = filedialog.askopenfilenames(filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi *.flv *.wmv")])
        if not filepaths:
            return
        for comp in self.hooks_compilations:
            comp.destroy()
        self.hooks_compilations.clear()
        if not self.compilations or len(self.compilations[0].files) == 0:
            messagebox.showwarning("Warning", "Load Tips first before loading Hooks.")
            self.update_compilation_numbers()
            self.sequence_manager.load_sequences()
            return
        for i, hook_file in enumerate(filepaths):
            comp = CompilationFrame(
                self.container_hooks.scrollable_frame, i,
                on_delete_callback=self.remove_hooks_compilation,
                allow_rename=False
            )
            comp.add_file(hook_file)
            comp.pack(fill="x", pady=5)
            self.hooks_compilations.append(comp)
        self.sync_hooks_with_tips1()
        self.update_compilation_numbers()
        self.sequence_manager.load_sequences()

    def load_intro_files(self):
        filepaths = filedialog.askopenfilenames(filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi *.flv *.wmv")])
        if not filepaths:
            return
        self.intro_files = [os.path.abspath(fp) for fp in filepaths]
        self._refresh_intro_items()
        self.sequence_manager.load_sequences()

    def _refresh_intro_items(self):
        for item in self._intro_file_items:
            item.destroy()
        self._intro_file_items = []
        for idx, path in enumerate(self.intro_files):
            item = FileItem(
                self.container_intros.scrollable_frame,
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
            self.sequence_manager.load_sequences()

    def move_intro_down(self, index):
        if index < len(self.intro_files) - 1:
            self.intro_files[index + 1], self.intro_files[index] = self.intro_files[index], self.intro_files[index + 1]
            self._refresh_intro_items()
            self.sequence_manager.load_sequences()

    def delete_intro(self, index):
        if 0 <= index < len(self.intro_files):
            del self.intro_files[index]
            self._refresh_intro_items()
            self.sequence_manager.load_sequences()

    def clear_intro_files(self, trigger_reload=True):
        if not self.intro_files and not self._intro_file_items:
            return
        self.intro_files = []
        self._refresh_intro_items()
        if trigger_reload:
            self.sequence_manager.load_sequences()

    def sync_hooks_with_tips1(self):
        if not self.compilations:
            return
        tips1_files = self.compilations[0].files.copy()
        for hooks_comp in self.hooks_compilations:
            if hooks_comp.files:
                hook = hooks_comp.files[0]
                hooks_comp.files = [hook] + tips1_files
            else:
                hooks_comp.files = tips1_files.copy()
            hooks_comp._refresh_file_items()

    def clear_all_compilations(self):
        for comp in self.compilations + self.hooks_compilations:
            comp.destroy()
        self.compilations.clear()
        self.hooks_compilations.clear()
        self.clear_intro_files(trigger_reload=False)
        self.global_resolution_ref["value"] = None
        self.update_compilation_numbers()
        self.sequence_manager.load_sequences()

    def remove_tips_compilation(self, frame):
        idx = self.compilations.index(frame)
        frame.destroy()
        self.compilations.remove(frame)
        self.update_compilation_numbers()
        if idx == 0:
            self.sync_hooks_with_tips1()
        if not self.compilations and not self.hooks_compilations:
            self.global_resolution_ref["value"] = None
        self.sequence_manager.load_sequences()

    def remove_hooks_compilation(self, frame):
        frame.destroy()
        self.hooks_compilations.remove(frame)
        self.update_compilation_numbers()
        if not self.compilations and not self.hooks_compilations:
            self.global_resolution_ref["value"] = None
        self.sequence_manager.load_sequences()

    def update_compilation_numbers(self):
        for idx, comp in enumerate(self.compilations):
            comp.set_name(f"Compilation {idx+1}")
        for idx, comp in enumerate(self.hooks_compilations):
            comp.set_name(f"Compilation {idx+1}")
        self.sequence_manager.load_sequences()

    def start_processing_thread(self):
        self.btn_process_all.config(state="disabled")
        self.progress_var.set(0)
        threading.Thread(target=self.process_all, daemon=True).start()

    def process_all(self):
        all_compilations = self.compilations + self.hooks_compilations
        if not all_compilations:
            messagebox.showinfo("Info", "No compilations to process.")
            self.btn_process_all.config(state="normal")
            return
        for comp in all_compilations:
            total_duration = sum(get_video_duration(f) for f in comp.files)
            if total_duration < 120:
                messagebox.showerror("Error",
                    f"Compilation '{comp.get_name()}' total duration less than 2 minutes.")
                self.btn_process_all.config(state="normal")
                return
        total = len(all_compilations)
        for idx, comp in enumerate(all_compilations):
            try:
                comp.export()
            except Exception as e:
                messagebox.showerror("Error", f"Error processing compilation '{comp.get_name()}':\n{e}")
                self.btn_process_all.config(state="normal")
                return
            progress_percent = ((idx + 1) / total) * 100
            self.progress_var.set(progress_percent)
        messagebox.showinfo("Info", "Exported Tips and Hooks Compilations.")
        self.btn_process_all.config(state="normal")
        self.progress_var.set(0)

    # --- DODAJ TO NA KOŃCU ---
    def export_all_compilations(self):
        self.global_progress_var.set(0)
        def tips_export():
            self.start_processing_thread()
            self.global_progress_var.set(50)
        def sequences_export():
            self.sequence_manager.export_sequences()
            self.global_progress_var.set(100)
        threading.Thread(target=tips_export, daemon=True).start()
        threading.Thread(target=sequences_export, daemon=True).start()
