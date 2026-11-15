#!/usr/bin/env python3
"""把弹簧物理参数转换成 CSS linear() 缓动与对应时长。

用法:
  python springs.py                      # 输出内置的几档弹簧（即 assets/motion.css 里的值）
  python springs.py 380 28               # 自定义：刚度 阻尼（质量为 1）
  python springs.py 380 28 --points 48

原理：对 x'' = -k(x-1) - c x' 做数值积分，从 0 走到 1，直到稳定在 ±0.001 内，
采样成 linear() 的折线点。时长就是稳定所需的真实时间。
"""
import math, sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PRESETS = [
    # 名字, 刚度, 阻尼, 用途
    ("snappy", 520, 38, "按压回弹、开关、小元素进入：快、几乎不过冲"),
    ("smooth", 260, 32, "面板、弹窗、卡片、布局变化：无过冲的顺滑减速"),
    ("bouncy", 340, 22, "有意的愉悦时刻：落位、点赞、完成——约 10% 过冲"),
    ("gentle", 120, 20, "大面积入场、首屏编排：慢而柔"),
]


def simulate(k, c, dt=1 / 2000):
    x, v, t = 0.0, 0.0, 0.0
    xs = [(0.0, 0.0)]
    settled_for = 0.0
    while t < 5:
        a = -k * (x - 1) - c * v
        v += a * dt
        x += v * dt
        t += dt
        xs.append((t, x))
        if abs(x - 1) < 0.001 and abs(v) < 0.01:
            settled_for += dt
            if settled_for > 0.03:
                break
        else:
            settled_for = 0.0
    return xs, t


def to_linear(xs, total, points=40):
    out = []
    for i in range(points + 1):
        target = total * i / points
        # 最近的采样
        j = min(range(len(xs)), key=lambda n: abs(xs[n][0] - target)) if i not in (0, points) else (0 if i == 0 else len(xs) - 1)
        val = 1.0 if i == points else xs[j][1]
        out.append(f"{val:.4f}".rstrip("0").rstrip(".") if val not in (0, 1) else str(int(val)))
    return "linear(" + ", ".join(out) + ")"


def run(k, c, points=40):
    xs, total = simulate(k, c)
    peak = max(x for _, x in xs)
    return to_linear(xs, total, points), round(total * 1000), (peak - 1) * 100


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    points = 40
    if "--points" in sys.argv:
        points = int(sys.argv[sys.argv.index("--points") + 1])
        args = [a for a in args if a != str(points)]
    if len(args) >= 2:
        lin, ms, over = run(float(args[0]), float(args[1]), points)
        print(f"/* k={args[0]} c={args[1]}  时长 {ms}ms  过冲 {over:.1f}% */")
        print(lin)
        return
    for name, k, c, use in PRESETS:
        lin, ms, over = run(k, c, points)
        print(f"  /* {name}: k={k} c={c}，{ms}ms，过冲 {max(over,0):.1f}%。{use} */")
        print(f"  --spring-{name}: {lin};")
        print(f"  --spring-{name}-dur: {ms}ms;")


if __name__ == "__main__":
    main()
