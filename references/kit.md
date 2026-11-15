# 网页套件

## 1. 选择与检查骨架

从操作方式与内容形状选择骨架。若模板已有一半区块需要删掉，先判断能否只复用其中的控件和主题。已有产品或明确参考稿可直接从其真实入口构建。

```sh
python scripts/scaffold.py --list
python scripts/scaffold.py --type tool --out work/
python scripts/audit.py work/ --gate
python scripts/shot.py work/index.html --browser "允许的浏览器路径"
```

内置编辑预设采用钴蓝油墨，植物预设采用亚麻、陶土和花瓣色。生成器处理由主题衍生的深绿时，保留明度并换成低彩度蓝灰；浅色绿系仍可用于有实际语义的局部。核对浅色、暗色、悬停、成功态及叠层在所用媒介中的实际呈色。

使用骨架时放入本项目的内容和操作。模板中尚未接入的入口标为禁用，交付前接上真实目的地或操作，或移除该入口。`audit.py --gate` 分页检查技术问题与套件残留。实际姓名、品牌、字段及单条相似文案不会单独阻断交付；同页出现同一模板的三条不同标记，或引用与套件样图内容完全一致的素材，会阻断。明确采用样例时可加 `--allow-sample`，其他技术检查仍生效。焦点样式、运行时控件名称及视觉权重回到实际界面判断。

| 要做的东西 | `--type` | 默认预设 |
|---|---|---|
| 苹果风格产品官网、产品摄影、结构拆解、软件功能展示 | `showcase` | studio，默认浅色，章节可单独布光 |
| 软件功能的前后对照、同坐标细节放大 | `compare` | studio，默认跟随系统，支持原生触屏和键盘 |
| 长文、博客、专栏、文档单篇（宋体标题、首字下沉、页边注、由数据画出的图、阅读进度条、随滚动高亮的目录） | `article` | paper-ink |
| 应用设置、账户中心、偏好设置（每行写清后果、右侧实时预览“别人看到的你”、改动后浮出保存条） | `settings` | graphite，石墨底和预设的钴蓝操作色 |
| HTML 邮件：订单、发货、预约、账单、验证码（表格布局，颜色写死在标签上，没有 ui-craft.css） | `email` | paper-ink |
| 官网、落地页、产品介绍、活动页（宋体大标题 + 产品自己的界面当主视觉，朱笔批注贯穿全页） | `landing` | paper-ink |
| AI 模型、软件新版本、硬件、App 的发布页（整页深色；超大名字 + 400 根页线标出它找到的三页，可切换的示例、对比条、可复制的用法） | `launch` | graphite，强调色默认柠檬绿，固定深色 |
| 后台、dashboard、管理系统、数据页（晨报式：一句结论、年度目标对时间进度、带走势线的指标带、标注过的趋势图） | `dashboard` | paper-ink |
| 小工具、小应用、demo（计时器、计算器、转换器、记录类；刻度表盘 + 一天的时间轴） | `tool` | graphite，强调色默认番茄红 |
| 手机 App、小程序的页面（账本格线、30 天刻度尺、一条可以直接打字的“记一笔”） | `mobile` | paper-ink |
| 登录、注册、申请、预约等表单（左边是与产品有关的实物——盖了日期戳的还书期限卡，右边是表单） | `form` | studio，浅色暖白、深色石墨。植物主题可选 botanical |

| 预设 `--style` | 气质 | 适合 |
|---|---|---|
| `paper-ink` | 印刷品、安静、有温度 | 内容、阅读、人文、文化 |
| `graphite` | 精密、冷静、高密度 | 开发者工具、后台、效率软件 |
| `midnight` | 发布会、高级、有光 | 科技产品官网、AI、硬件、金融 |
| `sunlit` | 明亮、友好、圆润 | 消费 App、教育、生活服务 |
| `editorial` | 杂志、钴蓝油墨、大字 | 媒体、作品集、文化机构 |
| `botanical` | 亚麻、陶土与花瓣色 | 健康、食物、家居 |
| `swiss` | 理性、锋利、网格 | 设计机构、活动、数据报告 |
| `dusk` | 温暖的光、柔焦 | 品牌页、生活方式、创意工具 |
| `studio` | 摄影棚的暖白与石墨，系统无衬线 | 有主视觉的产品展示、工业设计 |

强调色可从品牌、图像、材料或既有系统取得。`--accent` 为操作和选中态生成颜色，深色展示区保留预设底色。有精确品牌规范时将原值留给标识。需要用品牌色给整片展示区布光时加 `--tint-stage`。用 `--neutral warm|cool` 调整中性色。模板里的唱机、光环和扫描图都是示例，在题材相符且可用时取用其结构。

`--theme light|dark` 固定主题，`--single` 内联本地素材、样式和脚本，`--pack index.html` 打包完成页，`--bundle 目录/` 只取库。需要离线时可加 `--system-fonts` 省略预设的网络字体，并检查页面自行引入的资源。`--motion system` 响应系统减少动态效果；`full` 保留完整演示动效。产品摄影与拆解见[产品展示](product-showcase.md)。

## 2. 把模板改成项目的页面

保留有用的语义元素、可用状态、焦点样式和脚本加载保护。按任务修改模板自己的样式、区块次序、取景与排版。未用的演示逻辑随对应区块一起移除。复用套件的按钮或输入时可以沿用其类名和角色变量，产品已有组件时用项目的实现。

让用户可以核对的数字来自给定资料或真实数据。有示例数据需求时保持口径自洽，把必要的演示标识放在恰当的位置。标题直接命名当前任务，按钮说明按下后的结果，空或错误只在流程可能出现时设计。图标优先项目图标集，素材优先能辨认产品的原图或截图。

预览出现浏览器原始样式时，先看相邻的 CSS 是否加载。必要时打包成单文件再开。审查代码后还要在浏览器里看实际布局，重放本次涉及的动作。

## 3. 组件速查

全部是现成的类，直接写。修饰类跟在主类后面。

### 排版

| 类 | 用途 |
|---|---|
| `.display` | 首屏大标题，一页一个 |
| `h1` `h2` `h3` | 页面标题 / 区块标题 / 卡片标题（直接用标签，自带样式） |
| `.eyebrow` | 标题上方的小标签（"01 · 听""价格"） |
| `.lede` | 标题下面的导语，一两句 |
| `.muted` `.subtle` | 次要文字 / 更次要的说明（更小） |
| `.num` + `.unit` | 大数字 + 它的单位：`<p class="num">81<span class="unit">%</span></p>` |
| `.mono` `kbd` | 等宽的编号、时间 / 键帽 |

小标签、标题、导语连着写时间距自动处理，不用加 margin。

### 布局

| 类 | 用途 |
|---|---|
| `.wrap` | 页面内容的定宽容器，左右自动留边 |
| `.section` | 区块的上下大留白，和 `.wrap` 一起用：`<section class="wrap section">` |
| `.stack` | 竖排，子项之间等距（`.stack-sm` 更紧，`.stack-lg` 更松） |
| `.row` | 横排并垂直居中（`.between` 两端对齐，`.end` 靠右） |
| `.grow` | 放在 `.row` 里，占满剩余宽度 |
| `.grid` | 自动换行的等宽网格，`style="--min: 18rem"` 调每格最小宽度 |
| `.split` | 左窄右宽两栏（`.rev` 左宽右窄，`.even` 等宽，`.center` 垂直居中，`.bottom` 底对齐），窄屏自动变一栏 |
| `.sec-head` | 区块开头的"小标签 + 标题"组合 |
| `.hide-sm` | 手机上隐藏 |

### 按钮与表单

```html
<button class="btn primary">主操作</button>      <!-- 一屏只有一个 primary -->
<button class="btn">普通操作</button>
<button class="btn ghost">不重要的操作</button>
<button class="btn ink">深色按钮（导航里的注册）</button>
<button class="btn danger">删除</button>
<!-- 尺寸 .sm .lg；通栏 .block；只有图标 .icon（要加 aria-label）；提交中 .loading -->

<div class="field">
  <label for="mail">邮箱</label>
  <input class="input" id="mail" type="email" placeholder="you@company.com" aria-describedby="mail-hint">
  <span class="hint" id="mail-hint">用来接收登录链接。</span>
  <!-- 出错时：input 加 aria-invalid="true"，并显示 <span class="error">说清怎么改</span> -->
</div>
<select class="select">…</select>   <textarea class="textarea"></textarea>
<label class="check"><input type="checkbox"><span>记住我</span></label>
<input class="switch" type="checkbox" aria-label="开关的名字">
<div class="seg" role="group" aria-label="范围"><button aria-pressed="true">7 天</button><button>30 天</button></div>
```

### 表面

| 类 | 用途 |
|---|---|
| `.card` | 一个独立的对象（`.flat` 只有边线，`.sunken` 凹下去，`.tint` 强调色浅底，`.lift` 悬停抬起） |
| `.window` + `.window-bar` | 产品界面片段的窗口框，放在首屏舞台里当主视觉 |
| `.stage` > `.pad` | 深色舞台：页面里最重要的那一块。一页最多两块（首屏、结尾） |
| `.glow` | 加在舞台里的 `.window` 上，背后透出一团光 |

舞台里的文字、按钮、徽标自动换成舞台配色；舞台里的 `.card` / `.window` 仍是普通表面。

### 数据

```html
<!-- 指标带：并排的关键数字。不要把每个数字做成一张卡 -->
<dl class="metrics">
  <div><dt>成交额</dt><dd class="num">¥63,840</dd><span class="delta up">▲ 12.4%<small>较上周三</small></span></div>
  <div><dt>退款率</dt><dd class="num">2.9<span class="unit">%</span></dd><span class="delta down">▲ 0.4 点<small>在变差</small></span></div>
</dl>
<!-- .delta.up 绿 = 变好，.delta.down 红 = 变差。颜色说好坏，箭头说方向 -->

<div class="table-wrap"><table class="table">
  <thead><tr><th>商品</th><th class="r">销量</th><th>状态</th></tr></thead>
  <tbody><tr><td class="main">手冲壶 600ml</td><td class="r">41</td><td><span class="badge danger">今天补货</span></td></tr></tbody>
</table></div>
<!-- 数字列加 .r 右对齐；每行的主字段加 .main -->

<span class="badge">默认</span> <span class="badge accent">强调</span> <span class="badge ok">正常</span>
<span class="badge warn">注意</span> <span class="badge danger">紧急</span> <span class="badge plain">不带圆点</span>

<div class="bar"><i style="--v:75"></i></div>            <!-- 进度条，--v 是百分比 -->
<span class="avatar">周</span>                            <!-- 头像，放一个字 -->
```

### 列表、导航、反馈

```html
<div class="list">
  <div><span class="avatar">林</span><div class="grow"><p class="t">标题</p><p class="d">说明</p></div><span class="meta">10:40</span></div>
</div>
<!-- 带序号的待办：<div class="list todo">，每行开头 <span class="n">1</span>，最要紧的那条 <span class="n hot">1</span> -->

<header class="nav" id="nav"><div class="wrap">
  <a class="brand" href="/">品牌名</a>
  <nav class="links hide-sm"><a href="#features">功能</a><a href="#pricing">价格</a></nav>
  <a class="btn sm ink" href="/signup">开始用</a>
</div></header>

<div class="shell"><aside class="sidebar">
  <a class="brand" href="/">产品名</a>
  <nav class="side-group"><a class="side-item" href="/today" aria-current="page">今日</a><a class="side-item" href="/orders">订单<span class="count">86</span></a></nav>
</aside><main class="main">…</main></div>

<div class="tabs" role="tablist"><button type="button" role="tab" aria-selected="true">全部</button><button type="button" role="tab">未读</button></div>

<div class="note">普通提示</div>  <div class="note warn">要注意</div>  <div class="note danger">出错了，以及怎么办</div>
<div class="toast">已保存</div>
<dialog class="dialog"><h3>删除这个项目？</h3><p>删除后 30 天内可以在回收站恢复。</p>
  <div class="row"><button type="button" class="btn">取消</button><button type="button" class="btn danger">删除</button></div></dialog>
<div class="empty"><h3>还没有订单</h3><p>第一笔订单进来后会显示在这里。</p><a class="btn primary" href="/products/new">去上架商品</a></div>

<footer class="footer"><div class="wrap cols">…</div></footer>
```

手机画框：`.phone` > `.phone-scroll`（里面先放 `.statusbar`）+ `.tabbar`，见 `templates/mobile.html`。

---

## 4. 变量速查

| 用在哪 | 变量 |
|---|---|
| 文字 | `--text` 主要 · `--text-muted` 次要 · `--text-subtle` 说明 · `--text-faint` 只给装饰线和刻度 |
| 底色 | `--bg` 页面 · `--surface` 卡片 · `--surface-sunken` 凹下去的槽 · `--surface-raised` 浮层 |
| 线 | `--border` · `--border-strong` |
| 强调 | `--accent` 实底 · `--accent-fg` 压在它上面的字 · `--accent-text` 当文字用 · `--accent-subtle` 浅底 |
| 状态 | `--ok` `--warn` `--danger`（各有 `-soft` 浅底） |
| 舞台 | `--stage` · `--stage-ink` · `--stage-muted` |
| 字号 | `--fs-xs` 12 · `--fs-sm` 13 · `--fs-md` 15 · `--fs-lg` 18 · `--fs-xl` 24 · `--fs-2xl` 32 · `--fs-3xl` · `--fs-display` |
| 间距 | `--s-1` 4 · `--s-2` 8 · `--s-3` 12 · `--s-4` 16 · `--s-5` 24 · `--s-6` 32 · `--s-7` 48 · `--s-8` 64 · `--s-9` 96 |
| 圆角 | `--r-sm` · `--r-md` · `--r-lg` · `--r-xl`；胶囊与圆形用 `999px` |
| 阴影 | `--shadow-card` 贴着的 · `--shadow-pop` 浮起的 |
| 字体 | `--font-display` 标题与大数字 · `--font-body` 正文 · `--font-mono` 等宽 |

需要半透明的强调色：`color-mix(in srgb, var(--accent) 12%, transparent)`。必须是 `in srgb`。

---

## 5. 动效速查

产品展示支持 `[data-scroll-scene]` 与直接子元素 `[data-scene-pin]`。读取 CSS 变量 `--scene-progress` 绘制连续状态，详见 `product-showcase.md`。库已经处理好了弹簧、减弱动效、脚本失败时的兜底。只需要加属性：

| 写法 | 效果 | 用在哪 |
|---|---|---|
| `data-reveal` | 进入视口时上浮淡入 | 首屏的几个元素；下面每个区块最多一次 |
| `data-reveal="scale"` | 由小放大进入 | 首屏的主视觉（窗口、卡片） |
| `data-reveal="fade"` | 只淡入 | 不想有位移的地方 |
| `data-split` | 标题逐行揭开 | 首屏大标题，一页一个 |
| `data-count="63840"` | 数字从 0 滚到目标值（小数加 `data-decimals="1"`） | 关键指标 |
| `style="--delay:160ms"` | 推迟开始 | 首屏按阅读顺序错开：0 → 80 → 200 → 260 → 340ms |
| `class="draw"` | SVG 线条描出来 | 折线图 |
| `data-parallax="0.08"` | 随滚动轻微位移（0.05–0.2） | 首屏主视觉物件，一页一两处 |
| `data-tilt="6"` | 指针移上去时朝指针倾斜；父级加 `data-tilt-area` 可以扩大感应范围 | 主视觉物件、一张重点卡 |
| `class="float"` / `class="spin-slow"` | 慢慢上下浮动 / 极慢地自转 | 主视觉物件，一页最多一处 |
| `.bar` | 进度条进入视口时从 0 长到 `--v`；放在 `data-stagger` 的行里会依次生长 | 对比、完成度 |
| `data-copy="#id"` | 复制目标元素的文字，按钮上显示"已复制" | 提示词、邀请码、代码 |

**标签页**（切换示例、方案、平台）——选中块会滑动，面板切换有过渡，支持方向键：

```html
<section data-tabs>
  <div class="pills" role="tablist" aria-label="示例类别">
    <button type="button" role="tab" aria-selected="true">推理</button>
    <button type="button" role="tab">写作</button>
  </div>
  <div role="tabpanel">第一个面板</div>
  <div role="tabpanel" hidden>第二个面板</div>
</section>
```

`.seg`（分段控件）和 `.tabs`（下划线标签）也会自动获得滑动的选中块。

首屏整套入场在 1.2 秒内结束；每天用很多次的工具页不加入场动画。不要给每个元素都加，不要加无限循环的装饰动画。

---

## 6. 套件的常用约定

| 决定 | 何时可以沿用 | 何时调整 |
|---|---|---|
| 主题角色 | 同一类表面、文字和控件可重复引用令牌 | 品牌原色、独立图例、印刷色样各自有含义，单独命名，逐对验证 |
| 排版与对齐 | 一组标题与正文沿同一网格；跨行数字共享列边 | 编辑版面可换尺度、独立对齐或出血；按真实字面和信息顺序复核 |
| 表面与分组 | 用间距表示从属，分隔线帮助跨行追踪；主次操作有差别 | 卡片适合可独立浏览的对象，连续流程或跨列比较可采用带、表、轴 |
| 内容与状态 | 控件使用可访问名称；图像按用途提供替代内容；页首给出真实任务 | 组件只保留确有用途的状态、标签和提示。窄屏可以重排表格外的控制与说明 |
| 技术检查 | 未授权的模板样例、缺失的图片替代信息、禁用缩放等会影响交付 | 视觉线索到截图上判断；已有焦点环可直接保留。需要运行时确认的内容见[审视与修正](critique.md) |

下面的搭配是模板用法示例，实际设计使用项目和内容所需的部分。

## 8. 常见需求的拼法

**加一个"功能介绍"区块**（左文右图，下一个区块把 `.split` 换成 `.split rev` 并对调左右内容）：

```html
<section class="wrap section">
  <div class="split center" data-reveal>
    <div><p class="eyebrow">02 · 对账</p><h2>每一笔都对得上银行流水</h2>
      <p class="muted">导入流水后自动配对，配不上的单独列出来，点一下就能补。</p></div>
    <div class="card"><div class="list">
      <div><div class="grow"><p class="t">招商银行 尾号 6411</p><p class="d">已配对 212 笔</p></div><span class="badge ok">全部对上</span></div>
      <div><div class="grow"><p class="t">支付宝 商家账户</p><p class="d">已配对 87 笔，3 笔待确认</p></div><span class="badge warn">3 笔待确认</span></div>
    </div></div>
  </div>
</section>
```

**加一组卡片**（对象确实是并列的、各自独立的东西时才用）：

```html
<section class="wrap section">
  <div class="sec-head"><p class="eyebrow">课程</p><h2>这个月开的三门课</h2></div>
  <div class="grid" style="--min: 17rem">
    <article class="card lift"><p class="eyebrow">周二晚 · 8 节</p><h3>手冲入门</h3><p>从磨豆到注水，每节课冲三杯。</p>
      <div class="row between" style="margin-top: var(--s-4)"><span class="num" style="font-size: var(--fs-xl)">¥680</span><a class="btn sm" href="/schedule">看课表</a></div></article>
    <!-- 再复制两张，换内容 -->
  </div>
</section>
```

**加一个设置表单**：

```html
<section class="card" style="max-width: 32rem">
  <h3>通知</h3>
  <div class="stack" style="margin-top: var(--s-4)">
    <div class="field"><label for="n-mail">接收邮箱</label><input class="input" id="n-mail" type="email" value="suhe@example.cn"></div>
    <label class="row between"><span><span class="label">库存预警</span><br><span class="subtle">可售天数低于 3 天时提醒</span></span><input class="switch" type="checkbox" checked></label>
    <div class="row end"><button class="btn">取消</button><button class="btn primary">保存修改</button></div>
  </div>
</section>
```

**加一个确认弹窗**：第 3 节的 `<dialog class="dialog">`，用 `dialog.showModal()` 打开。危险操作的确认按钮用 `.btn.danger` 并写出动作（"删除"），不写"确定"。

**列表为空 / 搜索无结果**：第 3 节的 `.empty`。"还没有"和"筛选无结果"分开写：前者给"去创建"的按钮，后者给"清除筛选"。

---

## 9. 不是网页时

桌面 GUI（Qt、tkinter、WPF、WinUI）、游戏引擎、终端里用不了这套 CSS，但规则和数值照搬：

```bash
python scripts/palette.py "#题材色" --export list          # 看全部格式
python scripts/scaffold.py --type tk --accent "#题材色" --out mytool/   # tkinter 小工具：主题模块 + 模板程序，先跑起来再改内容
python scripts/palette.py "#题材色" --export ttk > ui_craft_ttk.py   # 只要 tkinter 主题（已有程序换皮）；桌面格式默认冷灰中性色
python scripts/palette.py "#题材色" --export qss > theme.qss         # PySide / PyQt
python scripts/palette.py "#题材色" --export wpf > Theme.xaml        # WPF / WinUI / Avalonia
python scripts/palette.py "#题材色" --export textual               # 终端界面（Textual）；Rich 用 rich
python scripts/palette.py "#题材色" --export godot                 # 游戏引擎：godot / unity / imgui / minecraft / lua / roblox
python scripts/icons.py --all --svg-dir icons/ --color "#3A3530"   # 图标存成 .svg 文件，桌面和引擎直接加载
python scripts/palette.py "#题材色" --hex                         # 只要十六进制色值时
```

| 项 | 取值 |
|---|---|
| 字号 | 12 / 13 / 15 / 18 / 24 / 32，一个窗口不超过 5 种 |
| 间距 | 4 / 8 / 12 / 16 / 24 / 32 / 48，控件之间 8，分组之间 24，窗口边距 16–24 |
| 控件高度 | 按钮与输入框同高：32（紧凑）或 40 |
| 圆角 | 小控件 4–6，卡片与面板 8–10，全程一致 |
| 颜色 | 一个强调色只给主按钮、选中、焦点；其余全部中性色；状态色绿 / 黄 / 红 |
| 字体 | 用系统界面字体（Windows：Segoe UI + 微软雅黑；macOS：系统默认），不换花体 |
| 对齐 | 标签右对齐或顶对齐二选一，全窗口一致；所有输入框左边缘对齐 |

先守平台惯例（`references/product-types.md` 第 8–10 节）。游戏界面读 `references/game-ui.md`。

---

## 10. 颜色替换与框架主题

当任务涉及建立或迁移主题时，按项目选择命令。先看角色映射，特别核对品牌、状态、图例以及图像的原色。

| 情况 | 命令 | 结果 |
|---|---|---|
| 新页面 | `scaffold.py --type … --accent "#题材色" --neutral warm` | 从种子生成明暗主题，再测实际背景上的文字与控件 |
| 已有页面、项目里散落的色值 | `recolor.py <路径> --accent "#题材色"`，确认后 `--write` | 每处颜色按用途换成角色变量（SCSS、桌面、引擎文件写成十六进制），原文件备份在 `.ui-craft-backup/` |
| Tailwind、Ant Design、Element Plus、MUI 项目 | `palette.py "#题材色" --export tailwind`（tailwind4 / antd / element / mui） | 需要调整配色时从主题层接入，沿用既有类名和组件 |
| Qt、WPF、tkinter、Unity、Godot | `palette.py "#题材色" --export qss`（wpf / tk / json） | 一份可以直接加载的样式表或资源字典 |

`recolor.py` 的归类规则：近白背景 → 表面或页面底色；深灰文字 → 主文字；中灰 → 次要或说明文字；浅灰线 → 线色；页面里最多的那一族彩色 → 强调色；红、绿、黄 → 危险、成功、警告（浅色背景用对应的浅底）；大面积彩色渐变 → 深色舞台带一点强调色；彩色投影 → 中性投影；半透明黑白和 `<svg>` 插画不动。换完运行 `shot.py` 看一眼，纠正误分角色，保留需要精确重现的原色；通过 --keep 保护指定色值。

## 11. 图标

`python scripts/icons.py --list` 列出 76 个线性图标（24 网格、1.8 描边、圆头）。`python scripts/icons.py search bell` 打印可直接粘贴的 `<svg class="ic">`，颜色跟随文字、大小跟随字号；React 加 `--jsx`；图标多时用 `--sprite` 生成一次符号表，再用 `<use href="#i-search"/>`。没有合适的就不放图标，不用 emoji。
