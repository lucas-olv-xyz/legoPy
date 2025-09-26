import tkinter as tk
from tkinter import ttk
from first_batch_frame import FirstBatchFrame
from next_batch_frame import NextBatchFrame

class BatchSwitcherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tips Compilation")
        self.geometry("1240x900")
        self.resizable(True, True)
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill="both", expand=True)
        self.project_code_prefix = tk.StringVar(value="E")
        self.project_code_digits = tk.StringVar()
        self.show_batch_menu()

    def clear_main(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def get_project_code(self):
        prefix = (self.project_code_prefix.get() or "").strip().upper()
        prefix = ''.join(ch for ch in prefix if ch.isalpha())
        if not prefix:
            prefix = "E"
        digits = ''.join(filter(str.isdigit, self.project_code_digits.get() or ""))[:3]
        digits = digits.zfill(3)
        return f"{prefix}{digits}"

    def show_batch_menu(self):
        self.clear_main()
        label = ttk.Label(self.main_frame, text="Choose Batch", font=("Arial", 22, "bold"))
        label.pack(pady=(40, 10))

        proj_frame = ttk.Frame(self.main_frame)
        proj_frame.pack(pady=(12, 20))
        ttk.Label(proj_frame, text="Project Code:", font=("Arial", 13)).pack(side="left", padx=(0,6))
        prefix_entry = ttk.Entry(proj_frame, textvariable=self.project_code_prefix, font=("Arial", 13), width=4, justify="center")
        prefix_entry.pack(side="left", padx=(0,4))
        entry_digits = ttk.Entry(proj_frame, textvariable=self.project_code_digits, font=("Arial", 13), width=5, justify="center")
        entry_digits.pack(side="left")

        btn_first = ttk.Button(self.main_frame, text="First Batch", width=25, command=self.show_first_batch)
        btn_first.pack(pady=8)
        btn_next = ttk.Button(self.main_frame, text="Next Batch", width=25, command=self.show_next_batch)
        btn_next.pack(pady=8)

    def show_first_batch(self):
        self.clear_main()
        FirstBatchFrame(self.main_frame, back_callback=self.show_batch_menu, get_project_code=self.get_project_code).pack(fill="both", expand=True)

    def show_next_batch(self):
        self.clear_main()
        NextBatchFrame(self.main_frame, back_callback=self.show_batch_menu, get_project_code=self.get_project_code).pack(fill="both", expand=True)

if __name__ == "__main__":
    BatchSwitcherApp().mainloop()
