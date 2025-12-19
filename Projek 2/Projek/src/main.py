import os
import uuid
import random
import datetime
import tkinter as tk
from tkinter import ttk, messagebox

from utils import (
    ensure_dirs, load_all_items, list_packages_from_soal,
    load_questions_for_package, normalize_correct_answer,
    pick_questions_with_fresh_priority,
    HISTORY_FILE, load_json, save_json
)

# ================= CONFIG =================
ensure_dirs()

DEFAULT_PACKAGES = ["PK", "PM", "PPU", "PBM", "PU"]
QUESTIONS_PER_LEVEL = 8
DAILY_NUM_QUESTIONS = 5
SESSION_SECONDS = 75 * 60
DAILY_POINTS = {"easy": 1, "medium": 2, "hard": 3}


# ================= APP =================
class QuizApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Latihan Soal UTBK")
        self.resizable(False, False)

        self._style()

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.packages = list_packages_from_soal() or DEFAULT_PACKAGES
        self.history = load_json(HISTORY_FILE, default=[])

        # session state
        self.questions = []
        self.idx = 0
        self.score = 0
        self.daily_score = 0
        self.showing_explanation = False
        self.is_daily = False

        # timer
        self.timer_label = None
        self.timer_running = False
        self.timer_job = None
        self.remaining = SESSION_SECONDS

        self._home()

    # ================= WINDOW RESIZE =================
    def resize(self, w, h):
        self.geometry(f"{w}x{h}")
        self.update_idletasks()

    # ================= STYLE (PASTEL PINK) =================
    def _style(self):
        s = ttk.Style()
        s.theme_use("clam")

        
        bg = "#fdf6fb"   
        text = "#4a044e"
        btn = "#fbcfe8"
        primary = btn
        btn_hover = "#f9a8d4"

        s.configure("TFrame", background=bg)
        s.configure("TLabel", background=bg, foreground=text)
        s.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        s.configure("Subtitle.TLabel", font=("Segoe UI", 10))

        s.configure(
            "TButton",
            font=("Segoe UI", 11),
            padding=10,
            background=btn,
            foreground=text
        )
        s.map("TButton", background=[("active", btn_hover)])

  
        s.configure(
            "Choice.TRadiobutton",
            background=primary,
            foreground=text,
            font=("Segoe UI", 11),
            padding=10,
            relief="flat"
        )
        s.map(
            "Choice.TRadiobutton",
            background=[
                ("active", btn_hover),
                ("selected", "#f472b6")
            ],
            foreground=[("selected", text)]
        )

    # ================= UTILS =================
    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    # ================= TIMER =================
    def start_timer(self):
        if self.timer_running:
            return
        self.timer_running = True
        self.remaining = SESSION_SECONDS
        self._tick()

    def _tick(self):
        if not self.timer_running:
            return

        m, s = divmod(self.remaining, 60)
        if self.timer_label:
            self.timer_label.config(text=f"⏱ {m:02d}:{s:02d}")

        if self.remaining <= 0:
            self.timer_running = False
            messagebox.showinfo("Waktu Habis", "Sesi berakhir")
            self.finish()
            return

        self.remaining -= 1
        self.timer_job = self.after(1000, self._tick)

    def stop_timer(self):
        self.timer_running = False
        if self.timer_job:
            try:
                self.after_cancel(self.timer_job)
            except:
                pass
            self.timer_job = None

    # ================= HOME =================
    def _home(self):
        self.stop_timer()
        self.clear()
        self.resize(420, 360)

        box = ttk.Frame(self.container)
        box.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(box, text="Latihan Soal UTBK", style="Title.TLabel").pack(pady=10)
        ttk.Button(box, text="▶ Start", width=22, command=self._package_menu).pack(pady=4)
        ttk.Button(box, text="🔥 Daily Challenge", width=22, command=self._daily_menu).pack(pady=4)
        ttk.Button(box, text="📊 History", width=22, command=self._history).pack(pady=4)

    # ================= PACKAGE =================
    def _package_menu(self):
        self.clear()
        self.resize(520, 480)

        box = ttk.Frame(self.container)
        box.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(box, text="Pilih Paket", style="Title.TLabel").pack(pady=10)
        for p in self.packages:
            ttk.Button(box, text=p, width=26,
                       command=lambda x=p: self._level_menu(x)).pack(pady=4)

        ttk.Button(box, text="⬅ Kembali", width=26, command=self._home).pack(pady=10)

    # ================= LEVEL =================
    def _level_menu(self, package):
        self.clear()
        self.resize(520, 480)

        box = ttk.Frame(self.container)
        box.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(box, text=f"Paket {package}", style="Title.TLabel").pack(pady=8)
        for lvl in ("easy", "medium", "hard"):
            ttk.Button(box, text=lvl.capitalize(), width=26,
                       command=lambda l=lvl: self.start_quiz(package, l)).pack(pady=4)

        ttk.Button(box, text="⬅ Kembali", width=26, command=self._package_menu).pack(pady=10)

    # ================= START QUIZ =================
    def start_quiz(self, package, level):
        db = load_questions_for_package(package.lower()) or load_all_items()
        db = normalize_correct_answer(db)

        self.questions = pick_questions_with_fresh_priority(
            db, QUESTIONS_PER_LEVEL, self.history, package.lower(), level=level
        )
        random.shuffle(self.questions)

        if not self.questions:
            messagebox.showinfo("Info", "Soal tidak tersedia")
            self._home()
            return

        self.idx = 0
        self.score = 0
        self.is_daily = False
        self.start_timer()
        self.show_question()

    # ================= DAILY =================
    def _daily_menu(self):
        self.clear()
        self.resize(520, 480)

        box = ttk.Frame(self.container)
        box.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(box, text="Daily Challenge", style="Title.TLabel").pack(pady=10)
        for p in self.packages:
            ttk.Button(box, text=p, width=26,
                       command=lambda x=p: self.start_daily(x)).pack(pady=4)

        ttk.Button(box, text="⬅ Kembali", width=26, command=self._home).pack(pady=10)

    def start_daily(self, package):
        db = load_questions_for_package(package.lower()) or load_all_items()
        db = normalize_correct_answer(db)

        pool = [q for q in db if q.get("level") in DAILY_POINTS]
        random.shuffle(pool)
        self.questions = pool[:DAILY_NUM_QUESTIONS]

        self.idx = 0
        self.daily_score = 0
        self.is_daily = True
        self.start_timer()
        self.show_question()

    # ================= QUESTION =================
    def show_question(self):
        self.showing_explanation = False
        self.clear()
        self.resize(900, 620)

        top = ttk.Frame(self.container)
        top.pack(fill="x", pady=4)

        ttk.Label(top, text="UTBK Quiz", style="Subtitle.TLabel").pack(side="left", padx=10)
        self.timer_label = ttk.Label(top, font=("Segoe UI", 9, "bold"), foreground="#86198f")
        self.timer_label.pack(side="right", padx=10)

        card = ttk.Frame(self.container)
        # card benar-benar di tengah
        card.pack(expand=True)
        card.place(relx=0.5, rely=0.5, anchor="center")

        q = self.questions[self.idx]

        ttk.Label(card, text=f"Soal {self.idx+1}/{len(self.questions)}",
                  style="Subtitle.TLabel").pack(anchor="w", pady=4)

        if q.get("reading"):
            ttk.Label(
                card,
                text=q["reading"],
                wraplength=720,
                justify="center",
                anchor="center"
            ).pack(fill="x", pady=6)

        ttk.Label(
            card,
            text=q["question"],
            wraplength=720,
            justify="center",
            anchor="center",
            font=("Segoe UI", 12)
        ).pack(fill="x", pady=8)

        self.answer_var = tk.IntVar(value=-1)
        self.radio = []
        for i, c in enumerate(q["choices"]):
            rb = ttk.Radiobutton(
                card,
                text=c,
                variable=self.answer_var,
                value=i,
                style="Choice.TRadiobutton"
            )
            rb.pack(anchor="w", pady=2)
            self.radio.append(rb)

        self.feedback = ttk.Label(card, font=("Segoe UI", 11, "bold"))
        self.feedback.pack(pady=6)

        self.expl = ttk.Label(card, wraplength=800)
        self.expl.pack(pady=4)

        nav = ttk.Frame(card)
        nav.pack(fill="x", pady=10)

        self.next_btn = ttk.Button(nav, text="Next ▶", command=self.next_step)
        self.next_btn.pack(fill="x", pady=4)
        ttk.Button(nav, text="⬅ Kembali", command=self._home).pack(fill="x", pady=4)

    # ================= NEXT =================
    def next_step(self):
        q = self.questions[self.idx]

        if not self.showing_explanation:
            sel = self.answer_var.get()
            if sel == -1:
                messagebox.showwarning("Pilih", "Pilih jawaban dulu")
                return

            for rb in self.radio:
                rb.config(state="disabled")

            if sel == q["correct_answer"]:
                if self.is_daily:
                    self.daily_score += DAILY_POINTS[q["level"]]
                else:
                    self.score += 1
                self.feedback.config(text="✅ Benar", foreground="#16a34a")
            else:
                self.feedback.config(text="❌ Salah", foreground="#dc2626")

            self.expl.config(text=f"Pembahasan:\n{q.get('explanation','')}")
            self.showing_explanation = True
            self.next_btn.config(text="Soal Berikutnya ▶")
            return

        if self.idx < len(self.questions) - 1:
            self.idx += 1
            self.show_question()
        else:
            self.finish()

    # ================= FINISH =================
    def finish(self):
        self.stop_timer()
        result = {
            "id": str(uuid.uuid4()),
            "time": datetime.datetime.now(datetime.UTC).isoformat(),
            "score": self.score,
            "daily": self.daily_score if self.is_daily else None
        }
        self.history.append(result)
        save_json(HISTORY_FILE, self.history)
        messagebox.showinfo("Selesai", "Sesi selesai")
        self._home()

    # ================= HISTORY =================
    def _history(self):
        win = tk.Toplevel(self)
        win.title("History")
        win.geometry("600x400")

        tree = ttk.Treeview(win, columns=("time", "score"), show="headings")
        tree.pack(fill="both", expand=True)

        tree.heading("time", text="Waktu")
        tree.heading("score", text="Skor")

        for h in self.history[-50:]:
            waktu = h.get("time", "-")
            skor = h.get("score", h.get("daily", 0))
            tree.insert("", "end", values=(waktu, skor))


# ================= MAIN =================
if __name__ == "__main__":
    QuizApp().mainloop()
