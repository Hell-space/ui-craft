#!/usr/bin/env python3
"""一套线宽一致的界面图标（24×24，1.8 描边，圆头圆角），代替 emoji 和东拼西凑的图标。

用法:
  python icons.py --list                       # 看有哪些图标（中文说明）
  python icons.py search bell user             # 打印可直接粘贴的内联 <svg>
  python icons.py search bell --jsx            # React / JSX 写法（strokeWidth 等驼峰属性）
  python icons.py search bell user --sprite    # 一段隐藏的 <svg> 符号表 + <use> 用法，页面里图标多时用
  python icons.py --all --sprite > icons.html  # 全部图标的符号表
  python icons.py --all --svg-dir icons/ --color "#3A3530"   # 每个图标存成一个 .svg 文件：Qt、WPF、Godot、Unity、Flutter 直接加载
  python icons.py search bell --svg-dir icons/ --size 20 --stroke 1.6

图标颜色跟随文字颜色（currentColor），大小跟随字号（1.25em）。放在按钮、导航、列表里时不用另外写样式。
只有图标没有文字的按钮，必须加 aria-label。
"""
from __future__ import annotations

import argparse
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ICONS: dict[str, tuple[str, str]] = {
    # 操作
    "search": ("搜索", '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>'),
    "plus": ("新增", '<path d="M12 5v14M5 12h14"/>'),
    "minus": ("减少", '<path d="M5 12h14"/>'),
    "close": ("关闭", '<path d="M6 6l12 12M18 6 6 18"/>'),
    "check": ("完成、选中", '<path d="m5 12.5 4.5 4.5L19 7.5"/>'),
    "edit": ("编辑", '<path d="m4.5 19.5 4.4-1.1L19.2 8.1l-3.3-3.3L5.6 15.1zM13.4 7.3l3.3 3.3"/>'),
    "trash": ("删除", '<path d="M4.5 7h15M10 7V4.5h4V7M6.5 7l1 12.5h9L17.5 7M10.5 11v5M13.5 11v5"/>'),
    "copy": ("复制", '<rect x="8.5" y="8.5" width="11" height="11" rx="2"/><path d="M15.5 8.5V6a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 6v8A1.5 1.5 0 0 0 6 15.5h2.5"/>'),
    "download": ("下载", '<path d="M12 4v11M7 10.5l5 5 5-5M5 19.5h14"/>'),
    "upload": ("上传", '<path d="M12 15.5V4.5M7 9l5-5 5 5M5 19.5h14"/>'),
    "share": ("分享", '<circle cx="17.5" cy="6" r="2.5"/><circle cx="6.5" cy="12" r="2.5"/><circle cx="17.5" cy="18" r="2.5"/><path d="m8.7 10.8 6.6-3.6M8.7 13.2l6.6 3.6"/>'),
    "link": ("链接", '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>'),
    "external": ("在新窗口打开", '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>'),
    "refresh": ("刷新、重试", '<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3L19.5 9"/><path d="M19.5 4.5V9H15"/>'),
    "filter": ("筛选", '<path d="M4 5h16l-6 7.5V19l-4-2v-4.5z"/>'),
    "sort": ("排序", '<path d="M7 4v16M3.5 16.5 7 20l3.5-3.5M17 20V4M13.5 7.5 17 4l3.5 3.5"/>'),
    "send": ("发送", '<path d="M20.5 3.5 10 14M20.5 3.5 14 20.5l-4-6.5-6.5-4z"/>'),
    "logout": ("退出登录", '<path d="M14.5 4.5H18a1.5 1.5 0 0 1 1.5 1.5v12a1.5 1.5 0 0 1-1.5 1.5h-3.5M10 8l-4 4 4 4M6 12h9.5"/>'),
    "play": ("播放", '<path d="M8 5.5v13l10.5-6.5z"/>'),
    "pause": ("暂停", '<path d="M9 5.5v13M15 5.5v13"/>'),
    # 方向
    "chevron-down": ("展开", '<path d="m6 9 6 6 6-6"/>'),
    "chevron-up": ("收起", '<path d="m6 15 6-6 6 6"/>'),
    "chevron-left": ("上一个", '<path d="m15 6-6 6 6 6"/>'),
    "chevron-right": ("下一个、进入", '<path d="m9 6 6 6-6 6"/>'),
    "arrow-right": ("前往", '<path d="M5 12h14M13 6l6 6-6 6"/>'),
    "arrow-left": ("返回", '<path d="M19 12H5M11 6l-6 6 6 6"/>'),
    "arrow-up": ("上升、回到顶部", '<path d="M12 19V5M6 11l6-6 6 6"/>'),
    "arrow-down": ("下降、向下", '<path d="M12 5v14M6 13l6 6 6-6"/>'),
    "arrow-up-right": ("跳转", '<path d="M7 17 17 7M9 7h8v8"/>'),
    # 导航与对象
    "menu": ("菜单", '<path d="M4 7h16M4 12h16M4 17h16"/>'),
    "more": ("更多", '<circle cx="5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="19" cy="12" r="1.2"/>'),
    "home": ("首页", '<path d="M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6h-6v6H5a1 1 0 0 1-1-1z"/>'),
    "user": ("个人、账户", '<circle cx="12" cy="8.5" r="3.5"/><path d="M5 20a7 7 0 0 1 14 0"/>'),
    "users": ("成员、团队", '<circle cx="9" cy="8.5" r="3.2"/><path d="M3 19.5a6 6 0 0 1 12 0M16 5.5a3 3 0 0 1 0 6M21 19.5a5 5 0 0 0-3.5-4.8"/>'),
    "settings": ("设置", '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>'),
    "bell": ("通知", '<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 20a2 2 0 0 0 4 0"/>'),
    "mail": ("邮件", '<rect x="3.5" y="5.5" width="17" height="13" rx="2"/><path d="m4 7 8 6 8-6"/>'),
    "message": ("消息、评论", '<path d="M4.5 6A1.5 1.5 0 0 1 6 4.5h12A1.5 1.5 0 0 1 19.5 6v9a1.5 1.5 0 0 1-1.5 1.5H10l-4.5 3.5v-3.5A1.5 1.5 0 0 1 4.5 15z"/>'),
    "phone": ("电话", '<path d="M6.5 3.5h3l1.5 4-2 1.5a11 11 0 0 0 6 6l1.5-2 4 1.5v3a2 2 0 0 1-2 2A16 16 0 0 1 4.5 5.5a2 2 0 0 1 2-2z"/>'),
    "calendar": ("日期、日程", '<rect x="4" y="5.5" width="16" height="14" rx="2"/><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4"/>'),
    "clock": ("时间", '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>'),
    "map-pin": ("地点", '<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/>'),
    "globe": ("语言、网站", '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.5 2.6 3.5 5.4 3.5 8.5s-1 5.9-3.5 8.5c-2.5-2.6-3.5-5.4-3.5-8.5s1-5.9 3.5-8.5z"/>'),
    "heart": ("喜欢", '<path d="M12 19.5s-7.5-4.6-7.5-10A4.2 4.2 0 0 1 12 7a4.2 4.2 0 0 1 7.5 2.5c0 5.4-7.5 10-7.5 10z"/>'),
    "star": ("收藏、评分", '<path d="m12 4 2.4 5 5.4.7-4 3.8 1 5.4L12 16.3 7.2 18.9l1-5.4-4-3.8 5.4-.7z"/>'),
    "bookmark": ("书签、稍后看", '<path d="M7 4h10a1 1 0 0 1 1 1v15l-6-4-6 4V5a1 1 0 0 1 1-1z"/>'),
    "eye": ("查看、显示", '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/>'),
    "lock": ("锁定、隐私", '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8.5 10.5V7.5a3.5 3.5 0 0 1 7 0v3"/>'),
    "shield": ("安全", '<path d="M12 3.5 19 6v5.5c0 4.5-3 7.8-7 9-4-1.2-7-4.5-7-9V6z"/><path d="m9 12 2.2 2.2L15.5 10"/>'),
    # 内容
    "grid": ("网格视图", '<rect x="4" y="4" width="6.5" height="6.5" rx="1.2"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.2"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1.2"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.2"/>'),
    "list": ("列表视图", '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.8" cy="6" r=".9"/><circle cx="4.8" cy="12" r=".9"/><circle cx="4.8" cy="18" r=".9"/>'),
    "image": ("图片", '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><circle cx="9" cy="9.5" r="1.8"/><path d="m4 17.5 5-5 4 4 2.5-2.5 4.5 4.5"/>'),
    "file": ("文件、文档", '<path d="M6.5 3.5h7l4 4V19a1.5 1.5 0 0 1-1.5 1.5h-9.5A1.5 1.5 0 0 1 5 19V5a1.5 1.5 0 0 1 1.5-1.5z"/><path d="M13.5 3.5V8h4M8.5 12.5h7M8.5 16h5"/>'),
    "folder": ("文件夹", '<path d="M3.5 7A1.5 1.5 0 0 1 5 5.5h4.5l2 2.5H19a1.5 1.5 0 0 1 1.5 1.5V17a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 17z"/>'),
    "layers": ("图层、分组", '<path d="m12 4 8.5 4.5L12 13 3.5 8.5z"/><path d="m3.5 12.5 8.5 4.5 8.5-4.5M3.5 16.5 12 21l8.5-4.5"/>'),
    "chart-bar": ("统计", '<path d="M4 20h16M7 16v-5M12 16V6M17 16v-8"/>'),
    "chart-line": ("趋势", '<path d="M4 19h16"/><path d="m4.5 15 4.5-5 4 3 6.5-7.5"/>'),
    "code": ("代码", '<path d="m8 7-5 5 5 5M16 7l5 5-5 5M14 4l-4 16"/>'),
    "terminal": ("终端、命令", '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="m7.5 9.5 3 2.5-3 2.5M12.5 15h4"/>'),
    "database": ("数据库、存储", '<ellipse cx="12" cy="6" rx="7" ry="2.5"/><path d="M5 6v12c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5V6M5 12c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5"/>'),
    "cloud": ("云、同步", '<path d="M7 18.5a4.5 4.5 0 0 1-.6-9 6 6 0 0 1 11.4 1.6A3.8 3.8 0 0 1 17.5 18.5z"/>'),
    "mic": ("录音、语音", '<rect x="9" y="3.5" width="6" height="10.5" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v2.5"/>'),
    "camera": ("拍照、扫码", '<path d="M4.5 8A1.5 1.5 0 0 1 6 6.5h2.5L10 4.5h4l1.5 2H18A1.5 1.5 0 0 1 19.5 8v10A1.5 1.5 0 0 1 18 19.5H6A1.5 1.5 0 0 1 4.5 18z"/><circle cx="12" cy="12.5" r="3.5"/>'),
    # 商业
    "cart": ("购物车", '<path d="M3.5 4.5h2.5l2.2 10.5h9.6l2-7.5H7"/><circle cx="9.5" cy="19" r="1.4"/><circle cx="16.5" cy="19" r="1.4"/>'),
    "credit-card": ("支付", '<rect x="3" y="5.5" width="18" height="13" rx="2"/><path d="M3 10h18M7 15h3"/>'),
    "wallet": ("钱包、余额", '<path d="M4.5 7.5V6A1.5 1.5 0 0 1 6 4.5h11"/><rect x="4.5" y="7.5" width="15.5" height="12" rx="1.8"/><path d="M16 13.5h.2"/>'),
    "tag": ("标签、价格", '<path d="M4 12.6V5a1 1 0 0 1 1-1h7.6l7.7 7.7a1 1 0 0 1 0 1.4l-7.2 7.2a1 1 0 0 1-1.4 0z"/><circle cx="8.5" cy="8.5" r="1.4"/>'),
    "box": ("商品、包裹", '<path d="M4 8l8-4 8 4-8 4zM4 8v8l8 4 8-4V8M12 12v8"/>'),
    "truck": ("配送", '<path d="M3.5 6.5h10v9.5h-10zM13.5 10h4l3 3v3h-7"/><circle cx="7" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>'),
    # 状态
    "info": ("提示", '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5M12 7.8v.2"/>'),
    "alert": ("警告", '<path d="M12 4 21 19.5H3z"/><path d="M12 10v4.5M12 17.2v.2"/>'),
    "help": ("帮助", '<circle cx="12" cy="12" r="8.5"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.4M12 17v.2"/>'),
    "bolt": ("快速、电量", '<path d="M13 3 5 13.5h6L10 21l8-10.5h-6z"/>'),
    "sun": ("浅色模式", '<circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"/>'),
    "moon": ("深色模式", '<path d="M19.5 14.5A7.5 7.5 0 0 1 9.5 4.5a7.5 7.5 0 1 0 10 10z"/>'),
    "gamepad": ("游戏", '<path d="M7 8.5h10a4 4 0 0 1 3.9 4.7l-.6 3.4a2.2 2.2 0 0 1-3.8 1.1L14.5 15.5h-5l-2 2.2a2.2 2.2 0 0 1-3.8-1.1l-.6-3.4A4 4 0 0 1 7 8.5z"/><path d="M8 11v3M6.5 12.5h3M15.5 12h.2M17.5 13.5h.2"/>'),
}

ATTRS = 'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"'
JSX_ATTRS = 'viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round"'


def inline(name: str, jsx: bool = False) -> str:
    body = ICONS[name][1]
    if jsx:
        return f'<svg className="ic" {JSX_ATTRS} aria-hidden="true">{body}</svg>'
    return f'<svg class="ic" {ATTRS} aria-hidden="true">{body}</svg>'


def sprite(names: list[str]) -> str:
    syms = "\n".join(f'  <symbol id="i-{n}" viewBox="0 0 24 24">{ICONS[n][1]}</symbol>' for n in names)
    return (f'<svg width="0" height="0" style="position:absolute" aria-hidden="true">\n'
            f'  <defs><style>symbol {{ fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }}</style></defs>\n'
            f"{syms}\n</svg>\n"
            "<!-- 用法：<svg class=\"ic\" aria-hidden=\"true\"><use href=\"#i-search\"/></svg> -->")


def main() -> int:
    ap = argparse.ArgumentParser(description="线宽一致的界面图标", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("names", nargs="*")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--jsx", action="store_true")
    ap.add_argument("--sprite", action="store_true")
    ap.add_argument("--svg-dir", help="把图标存成单独的 .svg 文件（桌面、游戏引擎、原生应用用）")
    ap.add_argument("--color", default="currentColor", help="配合 --svg-dir：描边颜色。网页里保持 currentColor；引擎和桌面写成具体颜色，如 \"#3A3530\"")
    ap.add_argument("--size", type=int, default=24, help="配合 --svg-dir：输出尺寸（像素）")
    ap.add_argument("--stroke", type=float, default=1.8, help="配合 --svg-dir：线宽（以 24 网格计）")
    a = ap.parse_args()
    if a.list or not (a.names or a.all):
        for n, (zh, _) in ICONS.items():
            print(f"  {n:<16}{zh}")
        print(f"\n共 {len(ICONS)} 个。打印内联写法：python icons.py search bell")
        return 0
    names = list(ICONS) if a.all else a.names
    bad = [n for n in names if n not in ICONS]
    if bad:
        print(f"没有这些图标：{', '.join(bad)}。先用 --list 看名字；实在没有就不放图标，不要换成 emoji。")
        return 2
    if a.svg_dir:
        import os
        import colorkit as ck
        rgba = ck.to_rgba(a.color)
        if rgba:
            authored = ck.theme_hex(rgba[:3])
            if authored != ck.hex_of(rgba[:3]):
                if rgba[3] < 1:
                    authored += f"{round(rgba[3] * 255):02X}"
                print(f"墨绿色描边已调整为 {authored}。")
                a.color = authored
        os.makedirs(a.svg_dir, exist_ok=True)
        for n in names:
            body = ICONS[n][1]
            svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{a.size}" height="{a.size}" viewBox="0 0 24 24" fill="none" '
                   f'stroke="{a.color}" stroke-width="{a.stroke:g}" stroke-linecap="round" stroke-linejoin="round">{body}</svg>\n')
            with open(os.path.join(a.svg_dir, f"{n}.svg"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(svg)
        print(f"已写入 {len(names)} 个 .svg 到 {a.svg_dir}（{a.size}px，线宽 {a.stroke:g}，颜色 {a.color}）")
        if a.color == "currentColor":
            print("提示：桌面和游戏引擎一般不认 currentColor，用 --color 写成具体颜色（取 palette.py 导出的文字色或强调色）。")
        return 0
    if a.sprite:
        print(sprite(names))
    else:
        for n in names:
            print(f"<!-- {n}：{ICONS[n][0]} -->\n{inline(n, a.jsx)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
