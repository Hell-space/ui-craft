# 构图配方

十二个总是好看的区块骨架，各带关键 CSS。变量名与 `assets/tokens.css`、`assets/styles.css` 一致。它们是骨架不是模板：**内容、物件、颜色从题材里来**，骨架只决定东西放在哪、多大、谁压着谁。

先决定阅读顺序。多条同类记录可以复用骨架以便比较，章节需要转换观察任务时再改变尺度、取景或构图。

## 目录
1. 舞台首屏：巨字 + 物件
2. 刊物首屏：满宽超大标题
3. 发布会首屏：物件在光里、截图出格
4. 数据故事首屏：一个大数字 + 一条横贯的曲线
5. 有层级的 Bento
6. 黏住的叙事：左文右图随滚动切换
7. 指标带
8. 单条证言
9. 定价
10. 结尾色面与页脚
11. 手机首屏
12. 空状态

---

## 1. 舞台首屏：巨字 + 物件

**用于**：3–4 档的产品首页、个人中心的"今日"。图书馆样例就是这个。

```html
<section class="stage-hero">
  <div class="copy">
    <p class="eyebrow" data-reveal>…</p>
    <h1 data-split>…</h1>
    <p class="big" data-reveal="blur">11.14</p>
    <p class="lede" data-reveal>…</p>
    <div class="acts" data-reveal>…</div>
  </div>
  <div class="object" data-reveal="scale">…题材物件…</div>
</section>
```
```css
.stage-hero { display: grid; grid-template-columns: minmax(0, 6fr) minmax(0, 5fr); align-items: end; gap: 2rem clamp(2rem, 5vw, 5rem);
  margin: .5rem clamp(.5rem, 1.5vw, 1.25rem) 0; padding: clamp(2.5rem, 4vw, 4.5rem) clamp(1.5rem, 4vw, 4rem) 0;
  border-radius: var(--r-xl); background: var(--stage-bg); color: var(--stage-ink); overflow: hidden; isolation: isolate; }
.stage-hero .big { font: var(--display-weight) clamp(5rem, 2.4rem + 10vw, 9.5rem)/.8 var(--font-display); letter-spacing: -.04em; }
.stage-hero .object { position: relative; align-self: end; }
.stage-hero .object::before { content: ""; position: absolute; inset: -30% -15% -5%; z-index: -1;
  background: radial-gradient(50% 50% at 50% 60%, color-mix(in srgb, var(--stage-ink) 18%, transparent), transparent 70%); filter: blur(12px); }
```
要点：舞台四周留出页面底色的边（`margin`），像一张放在桌上的卡；物件贴着舞台底边，或压过底边一点；舞台上的主按钮用 `--stage-btn`。

## 2. 刊物首屏：满宽超大标题

**用于**：媒体、作品集、文化机构、长文。`editorial` 与 `swiss` 预设。

```css
.press-hero { padding: clamp(2rem, 6vw, 5rem) var(--gutter) 0; }
.press-hero .kicker { display: flex; justify-content: space-between; padding-bottom: .75rem; border-bottom: 2px solid var(--text);
  font: 500 .75rem/1 var(--font-mono); letter-spacing: .08em; }
.press-hero h1 { margin: .25em 0 0; font: var(--display-weight) clamp(3.5rem, 1rem + 11vw, 11rem)/.86 var(--font-display);
  letter-spacing: var(--display-tracking); text-wrap: balance; max-width: 12ch; }
.press-hero h1 em { font-style: italic; color: var(--accent-text); }        /* 西文斜体做重音；中文改用颜色 */
.press-hero .deck { display: grid; grid-template-columns: minmax(0, 4fr) minmax(0, 7fr); gap: 2rem; margin-top: 2rem;
  padding-top: 1rem; border-top: 1px solid var(--border); }
```
要点：标题大到占满宽度、行高 0.86；栏线一粗一细；导语与元信息用不对称两栏。中文标题行高 1.1、字距 0。

## 3. 发布会首屏：物件在光里、截图出格

**用于**：产品官网、AI / 硬件 / 金融。`midnight`、`graphite`。

```css
.launch { text-align: center; padding: clamp(4rem, 9vw, 8rem) var(--gutter) 0; background: var(--stage-bg); color: var(--stage-ink); overflow: hidden; }
.launch h1 { font: var(--display-weight) clamp(2.75rem, 1rem + 6vw, 6rem)/.95 var(--font-display); letter-spacing: var(--display-tracking); max-width: 14ch; margin-inline: auto; }
.launch .shot { position: relative; width: min(1120px, 100%); margin: clamp(3rem, 6vw, 5rem) auto -6rem;
  border-radius: var(--r-xl); background: var(--surface); box-shadow: var(--shadow-pop);
  border: 1px solid transparent;
  background: linear-gradient(var(--surface), var(--surface)) padding-box,
              linear-gradient(170deg, rgb(255 255 255 / .6), rgb(255 255 255 / 0) 30%, color-mix(in srgb, var(--accent) 40%, transparent)) border-box; }
.launch .shot::before { content: ""; position: absolute; inset: -18% 10% auto; height: 70%; z-index: -1;
  background: radial-gradient(50% 50% at 50% 50%, color-mix(in srgb, var(--accent) 45%, transparent), transparent 70%); filter: blur(40px); }
```
要点：截图里放**真实感的产品界面**（HTML 搭的），宽于文字列，向下溢出到下一个区块（负 margin）；光晕在截图**后面**；居中只在这里成立，因为下面有一个足够强的物件。

## 4. 数据故事首屏：一个大数字 + 一条横贯的曲线

**用于**：年度报告、个人数据回顾、仪表盘的首屏。

```css
.datahero { position: relative; padding: clamp(3rem, 6vw, 5rem) var(--gutter) 0; }
.datahero .n { font: var(--display-weight) clamp(5rem, 2rem + 12vw, 12rem)/.8 var(--font-display); letter-spacing: -.045em;
  font-variant-numeric: proportional-nums lining-nums; }
.datahero .n small { font-size: .3em; letter-spacing: 0; color: var(--text-subtle); }
.datahero svg { display: block; width: 100%; height: clamp(120px, 18vw, 220px); margin-top: -2rem; }   /* 曲线压住数字底部 */
.datahero .curve { fill: none; stroke: var(--accent); stroke-width: 2.5; }      /* 加 class="draw" 让它被画出来 */
.datahero .area { fill: url(#fade); }                                            /* 线性渐变：强调色 25% → 0 */
```
要点：曲线横贯全宽、去掉坐标轴，只标一两个关键点（最高、今天）；数字用 `Motion.count()` 滚动到位；曲线用 `.draw` 描绘。

## 5. 有层级的 Bento

```css
.bento { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); grid-auto-rows: minmax(150px, auto); gap: 12px; }
.bento > * { border-radius: var(--r-lg); padding: 1.25rem; background: var(--surface); box-shadow: var(--shadow-card); overflow: hidden; }
.bento .hero { grid-column: span 4; grid-row: span 2; background: var(--stage-bg); color: var(--stage-ink); }   /* 主格：物件或核心数据 */
.bento .tall { grid-column: span 2; grid-row: span 2; }
.bento .wide { grid-column: span 3; }
.bento .tint-a { background: var(--accent-subtle); }                                                        /* 有色表面区分类别 */
@media (max-width: 760px) { .bento { grid-template-columns: 1fr 1fr; } .bento > * { grid-column: span 2; grid-row: auto; } }
```
要点：格子大小反映重要性，最大的那格必须有物件或大数字；每格里只讲一件事，并且**有一个可视的东西**（迷你界面、数字、图形），不是"图标 + 两行字"。

## 6. 黏住的叙事：左文右图随滚动切换

**用于**：讲 3–5 个步骤或特性，代替三列卡片。

```css
.story { display: grid; grid-template-columns: minmax(0, 5fr) minmax(0, 6fr); gap: clamp(2rem, 6vw, 6rem); }
.story .steps > * { min-height: 70vh; display: grid; align-content: center; color: var(--text-subtle); transition: color 400ms var(--ease-out-quart); }
.story .steps > * h3 { color: var(--text-muted); }
.story .steps > .active, .story .steps > .active h3 { color: var(--text); }
/* 未激活的步骤只降一级颜色，不要用 opacity: .35——那会读成坏掉的文字，也让对比度不达标 */
.story .visual { position: sticky; top: 15vh; height: 70vh; border-radius: var(--r-xl); background: var(--surface-sunken); }
.story .visual > * { position: absolute; inset: 0; opacity: 0; scale: .98; transition: opacity 400ms, scale var(--spring-smooth-dur) var(--spring-smooth); }
.story .visual > .active { opacity: 1; scale: 1; }
@media (max-width: 860px) { .story { grid-template-columns: 1fr; } .story .visual { position: relative; top: 0; height: auto; aspect-ratio: 4/3; } }
```
用 `IntersectionObserver`（`threshold: .6`）把进入中线的那一步标 `active`，同步右侧画面。窄屏改成每步下面跟一张图。

## 7. 指标带

**代替**"每个 KPI 一张卡"。

```css
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr)); border-top: 1px solid var(--text); }
.metrics > div { padding: 1rem 1.25rem 1.25rem 0; }
.metrics > div + div { padding-left: 1.25rem; border-left: 1px solid var(--border); }
.metrics dt { font-size: .75rem; color: var(--text-subtle); }
.metrics dd { margin: .375rem 0 0; font: 500 2rem/1 var(--font-display); letter-spacing: -.025em; font-variant-numeric: tabular-nums; }   /* 并排比较，所以用等宽 */
.metrics .unit { font-size: .5em; color: var(--text-subtle); margin-left: .1em; }
.metrics .delta { font-size: .8125rem; margin-top: .375rem; }     /* ▲ 12.4% 较上周一：颜色表好坏，箭头表方向 */
```

## 8. 单条证言

```css
.quote { display: grid; grid-template-columns: minmax(0, 7fr) minmax(0, 4fr); gap: 3rem; align-items: end; padding-block: clamp(4rem, 8vw, 7rem); }
.quote blockquote { margin: 0; font: var(--display-weight) clamp(1.75rem, 1rem + 2.4vw, 3rem)/1.2 var(--font-display); letter-spacing: -.015em; text-indent: -.45em; }
.quote figcaption { font-size: .875rem; color: var(--text-muted); border-top: 1px solid var(--border); padding-top: 1rem; }
.quote .proof { font: 500 2.5rem/1 var(--font-display); }          /* 配一个具体数字：效果的证据 */
```
要点：一条有观点的证言，大字、悬挂引号；旁边配一个具体数字。不做头像墙、星级、轮播。

## 9. 定价

```css
.plans { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; align-items: stretch; }
.plan { display: flex; flex-direction: column; border-radius: var(--r-lg); padding: 1.5rem; background: var(--surface); box-shadow: var(--shadow-card); }
.plan.pick { background: var(--stage-bg); color: var(--stage-ink); box-shadow: var(--shadow-pop); translate: 0 -8px; }   /* 推荐档：舞台色 + 抬起 */
.plan .price { font: var(--display-weight) 3rem/1 var(--font-display); letter-spacing: -.03em; margin: 1rem 0; }
.plan .price small { font-size: .3em; letter-spacing: 0; opacity: .7; }
.plan ul { flex: 1; }                                                 /* 按钮贴底，三档按钮在一条线上 */
@media (max-width: 860px) { .plans { grid-template-columns: 1fr; } .plan.pick { translate: none; order: -1; } }
```

## 10. 结尾色面与页脚

```css
.closing { margin: 0 clamp(.5rem, 1.5vw, 1.25rem); border-radius: var(--r-xl); padding: clamp(4rem, 9vw, 8rem) var(--gutter);
  background: var(--stage-bg); color: var(--stage-ink); display: grid; gap: 1.5rem; justify-items: start; }
.closing h2 { font: var(--display-weight) clamp(2.5rem, 1rem + 5vw, 5.5rem)/.95 var(--font-display); letter-spacing: var(--display-tracking); max-width: 14ch; }
footer { display: grid; grid-template-columns: minmax(0, 2fr) repeat(3, minmax(0, 1fr)); gap: 2rem; padding: 4rem var(--gutter) 3rem; font-size: .875rem; color: var(--text-muted); }
```
要点：最后一屏是与首屏呼应的色面，标题比中间区块更大；页脚分组清楚、对比度够，不是灰色小字的垃圾桶。

## 11. 手机首屏

**展示用的手机画框**（"在页面中央放一个手机"）：宽屏时画框居中、旁边一块说明牌；≤ 920px 隐藏说明牌；≤ 460px 去掉机身和灵动岛，界面直接铺满 `100dvh`——在真手机上再套一个手机画框没有意义。画框高度用 `clamp(660px, 100dvh - 56px, 868px)`，内容区内部滚动。

- 舞台占满宽度、四周留 8px 底色边，圆角 20px。
- 大数字或大标题在上半屏；物件缩到 80%，放在文字**下面**，可以只露出上半截（被舞台底边裁掉）。
- 主按钮 44px 高、满宽或至少半宽；次要信息收进可展开的区域。
- 横向内容（标签、卡片）用可横滑的一行，边缘 `mask-image` 渐隐，暗示还有更多。

## 12. 空状态

```html
<div class="empty">
  <svg class="empty-object" …>…与题材有关的小物件，如空书架、空票夹…</svg>
  <h3>书架还空着</h3>
  <p>借的书会立在这里，到期前三天提醒你。</p>
  <button class="btn primary pressable">去找一本书</button>
</div>
```
```css
.empty { display: grid; justify-items: center; text-align: center; gap: .5rem; padding: 3rem 1.5rem; }
.empty-object { width: 120px; height: 90px; color: var(--text-faint); margin-bottom: .5rem; }
.empty h3 { font: var(--display-weight) 1.25rem/1.3 var(--font-display); }
.empty p { color: var(--text-muted); max-width: 22em; }
```
标题写现状，正文写接下来会发生什么，一个主按钮。物件用线描，颜色淡，进入时 `data-reveal="scale"`。
