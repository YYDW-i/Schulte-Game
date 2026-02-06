import random
import time
import tkinter as tk
from tkinter import messagebox


def evaluate_adult(seconds: float) -> tuple[str, str]:
    """
    Adult reference bands for 5x5 (1-25) Schulte table commonly used by training tools:
    Beginner: 40-60s, Average: 25-40s, Advanced: 15-25s, Elite: <15s
    """
    if seconds < 15:
        level = "精英（Elite）"
        advice = "已经非常强了！可以尝试：6×6、倒序(25→1)、或在更嘈杂环境保持稳定。"
    elif seconds < 25:
        level = "高级（Advanced）"
        advice = "很不错！下一步目标：稳定进 15–20 秒，并把错误率压到 0。"
    elif seconds < 40:
        level = "中等（Average）"
        advice = "处在常见平均区间。建议先稳准再提速：固定盯中间，用余光分组找数。"
    elif seconds < 60:
        level = "入门（Beginner）"
        advice = "建议放慢一点点，先追求 0 错；形成固定搜索策略后再提速。"
    else:
        level = "需要加强"
        advice = "先把目标定在 40–60 秒：每轮专注、慢一点但不出错，逐步自然会提速。"
    return level, advice


def general_tips() -> str:
    return (
        "通用建议：\n"
        "1) 盯住中心格，尽量用余光覆盖全表，不要逐格扫。\n"
        "2) 眼睛离屏幕约 40–50cm；单次训练别超过 10 轮。\n"
        "3) 先追求准确（0错），再追求速度。\n"
        "4) 若想更贴近测验流程，用“5局测试”看平均时间。"
    )


class SchulteApp:
    SIZE = 5
    MAX_NUM = 25

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("舒尔特方格 5×5（Schulte Table）")

        self.target = 1
        self.start_time = None
        self.finished = False
        self.errors = 0

        self.batch_mode = False
        self.batch_total = 5
        self.batch_left = 0
        self.batch_times: list[float] = []

        # Top bar
        top = tk.Frame(root, padx=10, pady=8)
        top.pack(fill="x")

        self.target_var = tk.StringVar(value="目标：1")
        self.time_var = tk.StringVar(value="用时：0.00 s")
        self.err_var = tk.StringVar(value="错误：0")

        tk.Label(top, textvariable=self.target_var, font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Label(top, text="   ").pack(side="left")
        tk.Label(top, textvariable=self.time_var, font=("Segoe UI", 12)).pack(side="left")
        tk.Label(top, text="   ").pack(side="left")
        tk.Label(top, textvariable=self.err_var, font=("Segoe UI", 12)).pack(side="left")

        tk.Button(top, text="新一局", command=self.new_game).pack(side="right", padx=4)
        tk.Button(top, text="5局测试", command=self.start_batch).pack(side="right", padx=4)
        tk.Button(top, text="退出", command=root.quit).pack(side="right", padx=4)

        # Grid
        self.grid_frame = tk.Frame(root, padx=10, pady=10)
        self.grid_frame.pack()

        self.buttons: dict[int, tk.Button] = {}
        self._build_grid()

        self.new_game()
        self._tick()

    def _build_grid(self):
        for r in range(self.SIZE):
            self.grid_frame.rowconfigure(r, weight=1)
            for c in range(self.SIZE):
                self.grid_frame.columnconfigure(c, weight=1)

        # Create placeholders; real labels assigned in new_game()
        for idx in range(1, self.MAX_NUM + 1):
            btn = tk.Button(
                self.grid_frame,
                text="",
                width=6,
                height=3,
                font=("Segoe UI", 12, "bold"),
            )
            self.buttons[idx] = btn

    def new_game(self):
        nums = list(range(1, self.MAX_NUM + 1))
        random.shuffle(nums)

        self.target = 1
        self.start_time = None
        self.finished = False
        self.errors = 0

        self.target_var.set("目标：1")
        self.time_var.set("用时：0.00 s")
        self.err_var.set("错误：0")

        # Place buttons in grid according to shuffled nums
        for i, n in enumerate(nums):
            r, c = divmod(i, self.SIZE)
            btn = self.buttons[n]
            btn.config(
                text=str(n),
                state=tk.NORMAL,
                relief=tk.RAISED,
                command=lambda x=n: self.on_click(x),
            )
            btn.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")

    def start_batch(self):
        self.batch_mode = True
        self.batch_left = self.batch_total
        self.batch_times = []
        messagebox.showinfo("5局测试", "将连续进行 5 局，结束后按平均用时给出评价。")
        self.new_game()

    def on_click(self, number: int):
        if self.finished:
            return

        if self.start_time is None:
            self.start_time = time.perf_counter()

        if number == self.target:
            btn = self.buttons[number]
            btn.config(state=tk.DISABLED, relief=tk.SUNKEN)
            self.target += 1
            if self.target <= self.MAX_NUM:
                self.target_var.set(f"目标：{self.target}")
            else:
                self.finish_game()
        else:
            self.errors += 1
            self.err_var.set(f"错误：{self.errors}")
            self.root.bell()

    def finish_game(self):
        self.finished = True
        elapsed = time.perf_counter() - self.start_time if self.start_time else 0.0

        # Optional: small accuracy penalty for evaluation only (not “standard”, just practical)
        adjusted = elapsed + self.errors * 2.0

        if self.batch_mode:
            self.batch_times.append(adjusted)
            self.batch_left -= 1
            if self.batch_left > 0:
                messagebox.showinfo("继续", f"本局结束：{elapsed:.2f}s，错误 {self.errors}。\n将开始下一局（剩余 {self.batch_left} 局）。")
                self.new_game()
                return
            else:
                avg = sum(self.batch_times) / len(self.batch_times)
                level, advice = evaluate_adult(avg)
                messagebox.showinfo(
                    "5局测试结果",
                    f"5局平均（含错误惩罚）: {avg:.2f}s\n等级：{level}\n\n{advice}\n\n{general_tips()}",
                )
                self.batch_mode = False
                return

        level, advice = evaluate_adult(adjusted)
        messagebox.showinfo(
            "本局结果",
            f"用时：{elapsed:.2f}s\n错误：{self.errors}\n"
            f"评价用时（含错误惩罚）：{adjusted:.2f}s\n等级：{level}\n\n{advice}\n\n{general_tips()}",
        )

    def _tick(self):
        if self.start_time is not None and not self.finished:
            elapsed = time.perf_counter() - self.start_time
            self.time_var.set(f"用时：{elapsed:.2f} s")
        self.root.after(50, self._tick)


if __name__ == "__main__":
    root = tk.Tk()
    app = SchulteApp(root)
    root.mainloop()
