"""Main application window for the LegoPy toolkit."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from legopy.ui.first_batch import FirstBatchFrame
from legopy.ui.next_batch import NextBatchFrame


class BatchSwitcherApp(tk.Tk):
    """Tkinter application that lets the user switch between batch workflows."""

    def __init__(self) -> None:
        super().__init__()
        self._apply_dark_theme()
        self.title("Tips Compilation")
        self.geometry("1240x900")
        self.resizable(True, True)

        self.main_frame = ttk.Frame(self, style="App.TFrame")
        self.main_frame.pack(fill="both", expand=True)

        self.project_code_prefix = tk.StringVar(value="E")
        self.project_code_digits = tk.StringVar()

        self.show_batch_menu()

    def clear_main(self) -> None:
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def get_project_code(self) -> str:
        prefix = (self.project_code_prefix.get() or "").strip().upper()
        prefix = "".join(ch for ch in prefix if ch.isalpha()) or "E"
        digits = "".join(filter(str.isdigit, self.project_code_digits.get() or ""))[:3]
        digits = digits.zfill(3)
        return f"{prefix}{digits}"

    def show_batch_menu(self) -> None:
        self.clear_main()
        label = ttk.Label(
            self.main_frame,
            text="Choose Batch",
            font=("Arial", 22, "bold"),
            style="AppHeading.TLabel",
        )
        label.pack(pady=(40, 10))

        proj_frame = ttk.Frame(self.main_frame, style="App.TFrame")
        proj_frame.pack(pady=(12, 20))
        ttk.Label(
            proj_frame,
            text="Project Code:",
            font=("Arial", 13),
            style="App.TLabel",
        ).pack(side="left", padx=(0, 6))
        prefix_entry = ttk.Entry(
            proj_frame,
            textvariable=self.project_code_prefix,
            font=("Arial", 13),
            width=4,
            justify="center",
        )
        prefix_entry.pack(side="left", padx=(0, 4))
        entry_digits = ttk.Entry(
            proj_frame,
            textvariable=self.project_code_digits,
            font=("Arial", 13),
            width=5,
            justify="center",
        )
        entry_digits.pack(side="left")

        btn_first = ttk.Button(
            self.main_frame,
            text="First Batch",
            width=25,
            command=self.show_first_batch,
            style="Accent.TButton",
        )
        btn_first.pack(pady=8)
        btn_next = ttk.Button(
            self.main_frame,
            text="Next Batch",
            width=25,
            command=self.show_next_batch,
            style="Accent.TButton",
        )
        btn_next.pack(pady=8)

    def show_first_batch(self) -> None:
        self.clear_main()
        FirstBatchFrame(
            self.main_frame,
            back_callback=self.show_batch_menu,
            get_project_code=self.get_project_code,
        ).pack(fill="both", expand=True)

    def show_next_batch(self) -> None:
        self.clear_main()
        NextBatchFrame(
            self.main_frame,
            back_callback=self.show_batch_menu,
            get_project_code=self.get_project_code,
        ).pack(fill="both", expand=True)

    def _apply_dark_theme(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        colors = {
            "background": "#1e1e1e",
            "panel": "#242424",
            "accent": "#0e639c",
            "accent_active": "#1d7fba",
            "accent_pressed": "#0c4f77",
            "button": "#333333",
            "button_active": "#3f3f3f",
            "button_pressed": "#292929",
            "input_bg": "#1a1a1a",
            "disabled_bg": "#2a2a2a",
            "disabled_fg": "#777777",
            "fg": "#f2f2f2",
        }

        self.configure(bg=colors["background"])
        style.configure("TFrame", background=colors["background"])
        style.configure("App.TFrame", background=colors["background"])
        style.configure("Section.TFrame", background=colors["panel"])
        style.configure("TLabel", background=colors["panel"], foreground=colors["fg"])
        style.configure("App.TLabel", background=colors["background"], foreground=colors["fg"])
        style.configure("Section.TLabel", background=colors["panel"], foreground=colors["fg"])
        style.configure("SectionHeading.TLabel", background=colors["panel"], foreground=colors["fg"])
        style.configure("AppHeading.TLabel", background=colors["background"], foreground=colors["fg"])
        style.configure("TLabelframe", background=colors["panel"], foreground=colors["fg"])
        style.configure("TLabelframe.Label", background=colors["panel"], foreground=colors["fg"])
        style.configure("Section.TLabelframe", background=colors["panel"], foreground=colors["fg"])
        style.configure("Section.TLabelframe.Label", background=colors["panel"], foreground=colors["fg"])
        style.configure("TButton", background=colors["button"], foreground=colors["fg"])
        style.map(
            "TButton",
            background=[("active", colors["button_active"]), ("pressed", colors["button_pressed"])],
        )
        style.configure("Accent.TButton", background=colors["accent"], foreground="#ffffff")
        style.map(
            "Accent.TButton",
            background=[("active", colors["accent_active"]), ("pressed", colors["accent_pressed"])],
        )
        style.configure(
            "TEntry",
            fieldbackground=colors["input_bg"],
            foreground=colors["fg"],
            insertcolor=colors["fg"],
        )
        style.map(
            "TEntry",
            fieldbackground=[("disabled", colors["disabled_bg"])],
            foreground=[("disabled", colors["disabled_fg"])],
        )
        style.configure("TCheckbutton", background=colors["panel"], foreground=colors["fg"])
        style.map("TCheckbutton", background=[("active", colors["panel"])])
        style.configure(
            "Vertical.TScrollbar",
            background=colors["button"],
            troughcolor=colors["background"],
            arrowcolor=colors["fg"],
        )
        style.configure(
            "Horizontal.TScrollbar",
            background=colors["button"],
            troughcolor=colors["background"],
            arrowcolor=colors["fg"],
        )
        style.configure(
            "TProgressbar",
            background=colors["accent"],
            troughcolor=colors["background"],
        )
        style.configure(
            "Accent.Horizontal.TProgressbar",
            background=colors["accent"],
            troughcolor=colors["background"],
        )

        self.option_add("*TCombobox*Listbox.background", colors["panel"])
        self.option_add("*TCombobox*Listbox.foreground", colors["fg"])
        self.option_add("*Listbox*Background", colors["panel"])
        self.option_add("*Listbox*Foreground", colors["fg"])
        self.option_add("*Foreground", colors["fg"])

        self.dark_colors = colors


def run_app() -> None:
    """Convenience entry point used by the CLI and python -m legopy."""

    BatchSwitcherApp().mainloop()
