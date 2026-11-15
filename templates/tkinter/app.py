"""tkinter 小工具模板 —— 由 ui-craft 提供。用 scaffold.py --type tk 生成（会同时写出配好色的 ui_craft_ttk.py）。

结构：整幅强调色顶栏（标题、全窗口最大的数字、每日柱状图，标题栏同色连成一片）
      → 左：分类预算卡片、最近记录（可滚动、可悬停的列表）；右：记一笔表单（主按钮贴着卡片底边）。
改法：换文字、数字和数据；用不上的卡片整块删掉。顶栏一个窗口只放一条。
      颜色、字体、圆角都来自 ui_craft_ttk（ui.COLORS、ui.mix），不要另写颜色；分类色按顺序取 c["series"]。
"""
import tkinter as tk
from tkinter import ttk

import ui_craft_ttk as ui

# ---- 示例数据：换成你的
SPENT, BUDGET, DAYS, TODAY = 2386.40, 6500, 30, 13
DAILY = [86, 160, 64, 392, 118, 96, 220, 74, 132, 318, 152, 425.7, 148.7]   # 1 日到今天，每天花了多少
CATEGORIES = [  # 名称、头像上的字、已花、预算
    ("餐饮", "餐", 1240.0, 1800), ("交通", "行", 386.4, 600), ("购物", "购", 640.0, 500), ("其他", "杂", 120.0, 600)]
RECENT = [  # 说明、分类、时间、金额（正数是收入）
    ("和同事午饭", "餐饮", "今天 12:30", -84.00), ("打车去客户那", "交通", "今天 09:15", -46.70),
    ("生椰拿铁", "餐饮", "今天 08:42", -18.00), ("便利店晚饭", "餐饮", "昨天 20:05", -37.20),
    ("摇粒绒外套", "购物", "昨天 19:20", -249.00), ("报销到账", "其他", "昨天 10:02", 46.70),
    ("地铁月卡充值", "交通", "11 月 10 日", -100.00), ("周末买菜", "餐饮", "11 月 9 日", -126.30)]


def build_ui(root):
    c, P = ui.COLORS, ui.P
    color = {name: c["series"][i] for i, (name, *_) in enumerate(CATEGORIES)}
    glyph = {name: g for name, g, *_ in CATEGORIES}
    root.title("小账本")
    ui.titlebar(root, c["stage"], c["stage-ink"])

    # ---- 顶栏：标题 → 全窗口最大的数字 → 每日柱状图
    band = ui.band(root)
    band.pack(fill="x")
    band.columnconfigure(1, weight=1)
    head = ui.group(band, on="stage")
    head.grid(row=0, column=0, columnspan=2, sticky="we", pady=(0, P(12)))
    ttk.Label(head, text="十一月", style="Stage.Title.TLabel").pack(side="left")
    ttk.Label(head, text="11 月 13 日 · 周四", style="Stage.Muted.TLabel").pack(side="left", padx=(P(12), 0), pady=(P(7), 0))
    ttk.Button(head, text="导出账单", style="StageGhost.TButton").pack(side="right")

    left = BUDGET - SPENT
    hero = ui.group(band, on="stage")
    hero.grid(row=1, column=0, sticky="nw")
    ttk.Label(hero, text="这个月还可以花", style="Stage.Muted.TLabel").pack(anchor="w")
    big = ui.group(hero, on="stage")
    big.pack(anchor="w")
    num = ttk.Label(big, text=f"¥{int(left):,}", style="Stage.Display.TLabel")
    num.pack(side="left")
    ttk.Label(big, text=f".{round(left % 1 * 100):02d}", style="Stage.Unit.TLabel").pack(side="left", anchor="s", pady=(0, P(12)))
    ttk.Label(hero, text=f"还剩 {DAYS - TODAY} 天，平均每天还能花 ¥{left / (DAYS - TODAY):,.0f}",
              style="Stage.Muted.TLabel").pack(anchor="w")
    facts = ui.group(hero, on="stage")
    facts.pack(anchor="w", pady=(P(14), 0))
    over = sum(1 for *_, spent, cap in CATEGORIES if spent > cap)
    for label, value in (("已花", f"¥{SPENT:,.0f}"), ("预算", f"¥{BUDGET:,}"), ("超支", f"{over} 类")):
        cell = ui.group(facts, on="stage")
        cell.pack(side="left", padx=(0, P(32)))
        ttk.Label(cell, text=label, style="Stage.Small.TLabel").pack(anchor="w")
        ttk.Label(cell, text=value, style="Stage.Num.TLabel").pack(anchor="w")

    chart = ui.group(band, on="stage")
    chart.grid(row=1, column=1, sticky="nswe", padx=(P(56), 0))
    allowance = BUDGET / DAYS
    cap_row = ui.group(chart, on="stage")
    cap_row.pack(fill="x")
    ttk.Label(cap_row, text="每天花了多少", style="Stage.Muted.TLabel").pack(side="left")
    ttk.Label(cap_row, text=f"虚线是日均预算 ¥{allowance:,.0f}", style="Stage.Small.TLabel").pack(side="right")
    cv = tk.Canvas(chart, height=P(132), width=P(300), bg=c["stage"], highlightthickness=0, bd=0)
    cv.pack(fill="both", expand=True, pady=(P(10), 0))
    grown = [0.0]

    def draw(*_):
        cv.delete("all")
        w, h = cv.winfo_width(), cv.winfo_height()
        base, gap = h - P(22), P(4)
        bw = (w - gap * (DAYS - 1)) / DAYS
        top = max(max(DAILY), allowance) * 1.12
        for i in range(DAYS):
            x0 = i * (bw + gap)
            if i < len(DAILY):
                t = min(1.0, max(0.0, (grown[0] - i * 0.02) / 0.6))
                t = 1 - (1 - t) ** 3
                v = DAILY[i]
                fill = c["stage-ink"] if i == TODAY - 1 else ui.mix(c["stage-ink"], c["stage"], 0.62 if v > allowance else 0.34)
                y0 = base - max(P(3), (base - P(4)) * v / top * t)
            else:
                fill, y0 = ui.mix(c["stage-ink"], c["stage"], 0.14), base - P(3)
            cv.create_rectangle(round(x0), round(y0), round(x0 + bw), base, fill=fill, width=0)
        ya = round(base - (base - P(4)) * allowance / top)
        cv.create_line(0, ya, w, ya, fill=ui.mix(c["stage-ink"], c["stage"], 0.7), dash=(P(3), P(3)))
        small = (ui.FAMILY, ui.BASE - 1)
        cv.create_text(0, h, text="11/1", anchor="sw", fill=c["stage-muted"], font=small)
        cv.create_text(w, h, text="11/30", anchor="se", fill=c["stage-muted"], font=small)
        cv.create_text((TODAY - 1) * (bw + gap) + bw / 2, h, text="今天", anchor="s", fill=c["stage-ink"],
                       font=(ui.FAMILY, ui.BASE - 1, "bold"))
    cv.bind("<Configure>", draw)

    # ---- 下半部分
    body = ttk.Frame(root, padding=(P(24), P(18), P(24), P(22)))
    body.pack(fill="both", expand=True)
    body.columnconfigure(0, weight=3, uniform="col")
    body.columnconfigure(1, weight=2, uniform="col")
    body.rowconfigure(1, weight=1)
    gap = P(16)

    # 分类预算：四格并排，超支的那一格用危险色
    bc = ui.card(body, padding=(P(22), P(16), P(22), P(20)))
    bc.grid(row=0, column=0, sticky="we", padx=(0, gap))
    ttk.Label(bc, text="分类预算", style="Card.Heading.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, P(12)))
    bars = []
    for i, (name, _, spent, cap) in enumerate(CATEGORIES):
        bc.columnconfigure(i, weight=1, uniform="b")
        cell = ui.group(bc)
        cell.grid(row=1, column=i, sticky="we", padx=(0, P(18) if i < len(CATEGORIES) - 1 else 0))
        over = spent > cap
        ttk.Label(cell, text=name, image=ui.dot(root, color[name], gap=P(6)), compound="left",
                  style="Card.Muted.TLabel").pack(anchor="w")
        line = ui.group(cell)
        line.pack(anchor="w", pady=(P(2), P(8)))
        ttk.Label(line, text=f"¥{spent:,.0f}", style="Card.NumDanger.TLabel" if over else "Card.Num.TLabel").pack(side="left")
        ttk.Label(line, text=f" / {cap:,}", style="Card.Small.TLabel").pack(side="left", anchor="s", pady=(0, P(3)))
        bar = ui.progress(cell, 0, c["danger"] if over else color[name])
        bar.pack(fill="x")
        bars.append((bar, min(100.0, spent / cap * 100)))

    # 最近记录：可滚动、可悬停的列表
    lc = ui.card(body, padding=(P(12), P(14), P(12), P(10)))
    lc.grid(row=1, column=0, sticky="nswe", padx=(0, gap), pady=(gap, 0))
    top = ui.group(lc)
    top.pack(fill="x", padx=P(10), pady=(0, P(4)))
    ttk.Label(top, text="最近", style="Card.Heading.TLabel").pack(side="left")
    ttk.Label(top, text="本月 37 笔", style="Card.Muted.TLabel").pack(side="right")
    outer, inner = ui.scroll_area(lc)
    outer.pack(fill="both", expand=True)
    for desc, cat, when, amt in RECENT:
        r = ui.row(inner)
        r.pack(fill="x")
        ui.avatar(r, glyph[cat], color[cat]).pack(side="left")
        txt = ui.group(r)
        txt.pack(side="left", padx=(P(12), 0))
        ttk.Label(txt, text=desc, style="Card.TLabel").pack(anchor="w")
        ttk.Label(txt, text=f"{cat} · {when}", style="Card.Small.TLabel").pack(anchor="w")
        ttk.Label(r, text=f"+{amt:,.2f}" if amt > 0 else f"−{abs(amt):,.2f}",
                  style="Card.NumOk.TLabel" if amt > 0 else "Card.Num.TLabel").pack(side="right")

    # 记一笔：主按钮贴着卡片底边，和左边列表的底边对齐
    fc = ui.card(body, padding=(P(22), P(18), P(22), P(22)))
    fc.grid(row=0, column=1, rowspan=2, sticky="nswe")
    ttk.Label(fc, text="记一笔", style="Card.Heading.TLabel").pack(anchor="w")
    ttk.Label(fc, text="金额", style="Card.Muted.TLabel").pack(anchor="w", pady=(P(14), P(4)))
    amount = ttk.Entry(fc, style="Card.TEntry", font=(ui.NUM_FAMILY, ui.BASE + 10))
    amount.insert(0, "38.50")
    amount.pack(fill="x")
    ttk.Label(fc, text="分类", style="Card.Muted.TLabel").pack(anchor="w", pady=(P(14), P(6)))
    chips = ui.group(fc)
    chips.pack(fill="x")
    pick = tk.StringVar(root, value="餐饮")
    for name, *_ in CATEGORIES:
        ttk.Radiobutton(chips, text=name, value=name, variable=pick, image=ui.dot(root, color[name], gap=P(6)),
                        compound="left", style="Card.Chip.TRadiobutton").pack(side="left", padx=(0, P(8)))
    ttk.Label(fc, text="备注", style="Card.Muted.TLabel").pack(anchor="w", pady=(P(14), P(4)))
    note = ttk.Entry(fc, style="Card.TEntry")
    note.insert(0, "楼下咖啡")
    note.pack(fill="x")
    ttk.Checkbutton(fc, text="这笔可以报销", style="Card.TCheckbutton").pack(anchor="w", pady=(P(12), 0))
    acts = ui.group(fc)
    acts.pack(side="bottom", fill="x", pady=(P(16), 0))
    ttk.Button(acts, text="记下", style="Card.Accent.TButton", padding=(P(16), P(10))).pack(side="left", fill="x", expand=True)
    ttk.Button(acts, text="清空", style="Card.Ghost.TButton", padding=(P(18), P(10))).pack(side="left", padx=(P(8), 0))

    # ---- 动效：数字滚到位、柱子和进度条长出来（都在 1 秒内结束）
    start = 10 ** (len(str(int(left))) - 1)
    ui.tween(num, 900, lambda t: num.configure(text=f"¥{int(start + (left - start) * t):,}"), delay=120)
    ui.tween(cv, 1100, lambda t: (grown.__setitem__(0, t * 1.6), draw()), delay=120)
    ui.tween(bc, 900, lambda t: [b.configure(value=v * t) for b, v in bars], delay=240)

    # 窗口最小尺寸按内容算，缩小窗口时不会把内容挤掉
    root.update_idletasks()
    root.minsize(root.winfo_reqwidth(), root.winfo_reqheight())
    return root


if __name__ == "__main__":
    import sys
    ui.enable_dpi_awareness()
    app = tk.Tk()
    ui.apply(app, dark="--dark" in sys.argv)
    build_ui(app)
    app.mainloop()
