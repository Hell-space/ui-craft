# 游戏 mod、插件与覆盖层的界面

物品旁的一行、占据全屏的整备界面和整包美术重制，各自承担的改动不同。先分清谁拥有世界、字体、槽位、画面空间、输入和持久状态。小型扩展让人继续辨认宿主；整包重制可以靠全新的美术建立身份。两种范围都能沿用已成立的交互语义。

只要 mod 给玩家新增了看得见的东西，就按这份文件做：配置界面、物品或技能的提示框、HUD 元素、按键提示、聊天与通知格式、交易或合成界面、调试与作弊菜单、ImGui 覆盖层。纯玩法逻辑（掉落率、AI、物理、存档格式）不用。

各 API 名称随游戏版本变化，下面的代码是写法示意，动手前按项目实际的版本和映射核对一次。

## 1. 先定三件事

| 问题 | 怎么判断 | 决定了什么 |
|---|---|---|
| 这个界面是原版的延伸，还是独立工具？ | 玩家在正常游玩中会打开它（背包页签、交易、技能树）→ 延伸；开发者、主播、速通玩家用的叠加层（ImGui、性能监视、地图编辑器）→ 独立工具 | 延伸：用原版控件、贴图、字体、配色，让比例、字面与相邻宿主控件协调。独立工具：可自定配色，按亮暗战场及信息密度决定底板的明暗与透明度 |
| 生态里有没有现成的配置框架？ | Minecraft 的 Mod Menu + Cloth Config / YACL，Stardew 的 Generic Mod Config Menu，Skyrim / Fallout 4 的 MCM，WoW 的 Settings API，RimWorld 的 ModSettings | 有就用它。玩家熟悉、不用自己画，也自动跟原版风格走。只有现成框架表达不了的界面才自己画 |
| 它会在什么画面上出现？ | 白天、夜晚、洞穴、雪地、爆炸特效、菜单背景 | 面板底色与文字描边的强度；最亮和最暗的场景各截一张图验收 |

小型扩展可以让潮表沿用时钟的轮廓和快捷栏提示。新维度与整包重制可以发展自己的材质及形状体系，宿主的字体缩放、槽位与输入仍是参照。实例见[航行中的潮表与箱内的装备比较](opus-game-art.md#原版模组如何显出新内容)。

[原生物品比较校样](../examples/pixel-kit/project.godot)把主机物品、焦点、GUI 比例和皮肤留在宿主，附加组件只计算和显示差值。左右预览、取消、换包、改变尺寸后都可核对同一件已装备物。独立使用插件时，应复查具体目标宿主和常见叠加层的真实遮挡。整包重制可为原物绘制新轮廓，同时保留宿主的可装备状态和操作映射。

## 2. 贴合原版的做法

1. **截原版的图来取样。** 打开游戏里最接近的原版界面（背包、设置、商店），截图，量它的边框粗细、内边距、字号、行高、按钮高度、颜色。用这些数值对齐像素密度和控件关系；以当前宿主、资源包与缩放设置为准。颜色用取色器从截图取，不要凭印象写，更不要写网页常见的蓝 `#3B82F6`、紫色渐变。
2. **用原版的控件和贴图。** 按钮、滑块、复选框、滚动条、九宫格边框都用游戏自带的。自绘控件先与原版相邻控件并排看边角、对齐与反馈；为新物件保留可辨的轮廓。
3. **跟随游戏的界面缩放。** Minecraft 的 GUI 缩放、Terraria 的 UI 缩放、WoW 的 UIParent 缩放、Unity 游戏的分辨率。坐标和尺寸都乘缩放系数或用相对布局；在最小（如 1280×720）和最大缩放各看一次。
4. **像素风游戏守住整数像素。** 不用圆角、不用柔和阴影、不用渐变，线宽按游戏的像素单位（1 像素 × 缩放），文字不缩放到非整数倍。
5. **字体用游戏的字体。** 不另加网页字体。需要中文时确认游戏字体有中文字形（Minecraft、泰拉瑞亚自带；ImGui、Unity IMGUI 默认没有，要加载并指定中文字形范围）。
6. **文案进语言文件。** `en_us.json` / `zh_cn.json`、`.lang`、`.po`、Localization 表。按最长的译文（德语、俄语、中文全角标点）留宽度，不要把文字画进贴图。

## 3. 读得清、不挡玩

- **HUD 元素放边角，中心留给游戏。** 新的 HUD 不要盖住准星、血条、小地图、聊天框这些原版位置；给出位置和透明度的配置项。
- **按背景决定承托文字的面积。** 雪地上可以用暗边亮芯，复杂背景可给文字加局部底条；在暂停的高密度比较面板里，稳定实底往往更可读。
- **颜色语义跟随原版。** 物品稀有度、伤害类型、阵营色沿用游戏已有的那套；新增状态色时先看原版有没有对应的颜色可借。
- **提示框（tooltip）的层级：** 名称 → 关键数值 → 说明 → 来源 mod 名（最弱的灰色）。和原版提示框的行距、分隔线一致。
- **通知要短。** 聊天栏消息加 mod 前缀（用原版的格式码上色），不要每次都刷屏；重复事件合并计数。

## 4. 输入与状态

- 打开界面时释放鼠标锁定，关闭时恢复；Esc（手柄 B）关闭最上层；界面打开时游戏是否暂停，跟原版同类界面一致。
- 新按键不和原版、常见 mod 冲突，并且能在原版按键设置里改。
- 手柄：焦点在控件间能用方向键走通，关闭后焦点回到打开它的地方。
- 多人游戏：界面上的操作走服务端校验，客户端先显示"处理中"再显示结果；失败时说明原因（权限、距离、背包满）。

## 5. 性能

界面代码每帧都在跑。

- 渲染回调里不分配内存、不拼接字符串、不重复测量文字宽度：在打开界面或数据变化时算好并缓存。
- Unity IMGUI 的 `OnGUI` 每帧会调用多次：`GUIStyle` 和纹理在初始化时建好，不要每次 `new`。
- WoW 的 `OnUpdate` 按间隔节流；Factorio 的 GUI 只在事件里更新，不在 `on_tick` 里重建。
- ImGui 覆盖层只在打开时绘制；关闭时连窗口也不要 `Begin`。

## 6. 各平台做法

| 平台 | 界面接口 | 原版风格从哪来 | 配置界面 |
|---|---|---|---|
| Minecraft Java（Fabric / NeoForge / Forge） | 继承 `Screen`，在 `init()` 里 `addDrawableChild(ButtonWidget.builder(…).dimensions(…).build())`；绘制用 `DrawContext`（Yarn 映射）或 `GuiGraphics`（Mojang 映射） | 原版控件与 GUI 贴图（1.20.2+ 的 GUI sprites）、`textRenderer`、`Text.translatable` | Mod Menu + Cloth Config 或 YACL |
| Minecraft 基岩版 | 资源包 JSON UI（`ui/*.json`）；Script API 的 `@minecraft/server-ui` 表单 | 原版 JSON UI 的控件与九宫格 | 表单的视觉是固定的，只设计标题、选项顺序和文案 |
| Terraria（tModLoader） | `UIState` + `UIPanel` / `UITextPanel` / `UIList`，在 `ModSystem` 里挂到界面层 | 原版面板蓝和边框贴图；`FontAssets.MouseText` | `ModConfig`（自动生成界面） |
| Stardew Valley（SMAPI） | 继承 `IClickableMenu`，`IClickableMenu.drawTextureBox` 画原版边框，`Game1.smallFont` | 原版菜单贴图（`Game1.menuTexture`） | Generic Mod Config Menu |
| RimWorld | 继承 `Window`，`Listing_Standard`、`Widgets.ButtonText`、`Text.Font` | 原版窗口与控件 | `Mod.DoSettingsWindowContents` |
| Skyrim / Fallout 4 | MCM（SkyUI MCM 的 Papyrus 脚本或 MCM Helper 的 JSON 配置）；复杂界面用 Scaleform（Flash）或 SKSE + ImGui | 原版菜单 | MCM：只设计页面划分、选项顺序、说明文字 |
| World of Warcraft 插件 | Lua + XML，`CreateFrame("Frame", 名称, UIParent, "BackdropTemplate")`，原版模板如 `UIPanelButtonTemplate` | 原版模板、`GameFontNormal` 系列字体对象 | `Settings.RegisterAddOnCategory` |
| Factorio | `player.gui.screen.add{type="frame", …}`，样式用原版的 `inside_shallow_frame` 等 | 原版样式原型 | 设置（settings.lua）+ 原版样式的面板 |
| Roblox | `ScreenGui` → `Frame` / `TextLabel` / `TextButton`，配 `UICorner`、`UIStroke`、`UIPadding`、`UIListLayout` | 游戏自己的美术；没有就按本技能的配色导出 | 自建；注意手机与手柄的安全区 |
| Unity 游戏（BepInEx / MelonLoader） | IMGUI（`OnGUI`、`GUILayout.Window`）做工具类菜单；贴合游戏时克隆游戏自己的 uGUI 预制体 | 游戏的 uGUI 预制体、字体与精灵 | BepInEx ConfigurationManager（F1） |
| Godot 游戏或插件 | `Control` 节点 + `Theme` 资源 | 游戏已有的 Theme | 插件的 `EditorInspectorPlugin` 或自建 |
| Garry's Mod | Derma：`vgui.Create("DFrame")`，重写 `Paint` 用 `draw.RoundedBox`、`surface.CreateFont` | 沿用服务器主题，独立工具按场景选底板 | 自建 |
| Dear ImGui 覆盖层（游戏内工具、模拟器、ReShade 插件） | `ImGui::Begin/End`、`ImGuiStyle` | 使用宿主或工具当前的皮肤，新主题按覆盖层的用途决定 | 同一覆盖层的设置页 |

## 7. 独立工具类覆盖层的配色

默认蓝或灰可能就是用户熟悉的工具身份。先看当前选区、危险状态和文字在实际背景上是否可辨。简报需要自定皮肤时，可用现有品牌令牌、引擎主题资源或下列导出器作起点。

```bash
python scripts/palette.py "#C8A15A" --export imgui      # Dear ImGui：C++ 的 ApplyStyle()（--export imgui-cs 给 ImGui.NET）
python scripts/palette.py "#C8A15A" --export unity      # Unity：C# 静态颜色 + IMGUI 皮肤初始化；--export uss 给 UI Toolkit
python scripts/palette.py "#C8A15A" --export godot      # Godot：GDScript 常量 + Theme 设置
python scripts/palette.py "#C8A15A" --export minecraft  # Minecraft Java：ARGB int 常量（给 DrawContext.fill / 文字颜色）
python scripts/palette.py "#C8A15A" --export lua        # WoW / Factorio / LÖVE：0–1 的 {r, g, b, a}；--export roblox 给 Color3.fromRGB
```

导出后检查选中、禁用、悬停和焦点。透明度跟背景亮度及需要看见的世界细节一起调整。

## 8. 验收

在受影响的宿主界面复现任务。只改一行物品名，可以在原 GUI 比例打开长名称并复看相邻槽位；涉及菜单接管时，再检查已支持的打开、确认、返回和恢复操作。叠加在变化背景上的信息要看易失读的明暗场景。需要兼容的资源包、设备、其他 mod 或服务端影响到这次结果时，再验证对应组合。记录测到的宿主和条件。

