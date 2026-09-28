# 照片风格逐项设计评审与升级规划（界面美学所 · uiteam）

- **评审日期**：2026-09-28
- **评审范围**：19 款照片风格——index.html 内联首页 5 款（style-1/2/3/4/6）+ 独立模板 13 款（style7~19，style18=prism、style19=origami 为改名后新文件名）
- **评审方式**：4 路资料员实读全部源码提取设计事实（色板/字体/构图/动效均精确到行号），主理人结合当代设计趋势坐标逐款裁决
- **评级体系**：S（标杆，可作为其他风格参照）｜A-（在线，微调即可）｜B+（良好，有明确升级点）｜B（合格，需要一轮打磨）｜B-（概念好执行塌）｜C（明显过时，需重做视觉层）

---

## 〇、当代设计趋势坐标（评审基准）

本轮评审以 2025-2026 界面设计的主流方向为标尺：

| 趋势 | 内涵 | 对相框产品的意义 |
|---|---|---|
| **Liquid Glass 2.0** | Apple 2025 起的折射玻璃语言：低模糊、镜面高光、边缘折射、随内容变色 | 替代 2020 初代高斯模糊玻璃（blur30+白描边已显旧） |
| **Editorial 衬线回潮** | Fraunces / Newsreader / Instrument Serif 类当代衬线做超大标题，基线网格 | 相框的时钟/日期天然适合杂志化排版 |
| **Japandi / 侘寂** | 低饱和暖灰、纸纹、留白、克制动效（近乎无动画） | 禅意/和风款的正确打开方式 |
| **克制动效** | 动效必须「可感知才有意义」——要么明显，要么删除 | 反对「装饰性不可见动画」 |
| **反 AI-Slop** | 紫蓝霓虹、三色光晕、全屏渐变动画、手写体滥用均已过时 | 本轮判「low」的主要依据 |
| **OLED-first 暗色** | 真黑底 + 内容发光，而非灰黑叠加彩光 | 相框常驻大屏场景的主流 |

**过时元素黑名单（本轮点名项）**：全屏多色渐变动画背景（2018）、初代高斯模糊玻璃（2020）、Dancing Script 类全站手写体（2012）、彩虹渐变进度条（2015）、三层霓虹 text-shadow（2018 vaporwave）、不动的假 VU 表盘。

---

## 一、首页内联风格（index.html 内 5 款）

### 1. style-1 经典分栏 —— 评级 B ｜ 优先级 P2 微调

**现状**：无任何专属覆盖的基底皮肤，35/65 左右分栏，深色渐变信息栏 + Inter 全家 + 玻璃天气卡。

**优点**：① 全项目最成熟的骨架：tnum 时钟、safe-area、响应式断点都最完整；② 玻璃只用在天气卡一处，克制得当；③ 作为默认款零短板。

**问题诊断**：① 定位是「没有设计的设计」——零记忆点，用户说不出它的气质；② 深底双光斑是 2020 式处理，不如真黑 OLED 干净；③ Inter 中性但无排印处理（无大写标签系统、无衬线对比）。

**升级方向**：① 光斑减淡 40% 或改纯 #030405 真黑，让照片当主角；② 时钟字号上探（clamp 上限 96px→120px），加 12px 大写字距标签行（类 style-6 的刊头做法）；③ weather 卡升级 Liquid Glass：blur 20→14，加内侧 1px 镜面高光线。

**改进对比**：Before「合格但不认识」→ After「苹果官网级别的暗色基准款」。

### 2. style-2 沉浸全屏 —— 评级 B+ ｜ 优先级 P1 打磨

**现状**：照片全宽 + fixed 悬浮信息卡（34px 圆角），时钟放大到 180px，唯一 controls 默认可见的暗色款。

**优点**：① 180px 大时钟的排印胆量是五款之最；② 大屏 1920/2560/2700 三档变量递增做得认真；③ controls 常显符合沉浸式场景。

**问题诊断**：① 靛蓝/蓝/橙三色光晕贴着 AI-Slop 红线（多色弥散光=2021 生成式审美）；② 照片左让位 112px 是硬编码补丁而非布局系统，换屏宽就露怯；③ 悬浮卡 blur18+重投影是初代玻璃语言。

**升级方向**：① 光晕从三色收敛为单色（只留暖金，饱和度 -30%，blur 半径加大但透明度减半）；② 面板玻璃升级折射版：blur 18→10 + saturate 1.2 + 内侧 1px 高光描边；③ 112px 让位改为与 --style2-panel-width 联动的 calc 变量。

**改进对比**：Before「三个彩色手电筒打在卡片后」→ After「一块真玻璃浮在照片上」。

### 3. style-3 画廊展签 —— 评级 B- ｜ 优先级 P1 打磨

**现状**：唯一暖褐暗字款，米纸渐变背景 + 米白画框 + serif greeting 的美术馆展签概念。

**优点**：① 展签概念在五款中文化调性最高；② 米白画框底 #f8f3ea + 暖褐投影的材质感成立；③ 2560×1600 平板专属档说明有认真对待大屏。

**问题诊断**：① **级联残留实锤**：.info-panel 三段叠写（:653 暗底 blur28 → :877 浅色底），blur(28px) backdrop-filter 没清理，浅色款顶着暗玻璃滤镜；② controls 行为与兄弟款不一致（style-2/4/6 常驻 0.9，它 hover 才现）；③ Georgia 与 Cinzel 两个不同气质的衬线混搭；④ 级联叠写本身就是维护性地雷（文件头注释都自认了技术债）。

**升级方向**：① 删除 :653 的暗底残留块（一次清理解决 bug + 性能）；② 补 `#controls { opacity: 0.9 }` 对齐兄弟款；③ 衬线统一为一族（建议 EB Garamond 或 Cormorant，比 Georgia 更当代、比 Cinzel 更收敛）；④ 展签排版加基线网格：作品编号+标题+年份的三行固定结构。

**改进对比**：Before「戴着一层没撕的暗色玻璃膜的美术馆」→ After「干净的米纸展墙」。

### 4. style-4 悬浮玻璃 —— 评级 B ｜ 优先级 P1 打磨

**现状**：照片全出血 + 高透明玻璃卡浮在左上，五款中唯一隐藏聊天区的纯时钟款。

**优点**：① 全出血照片 + 悬浮卡是五款中最接近「高端数字相框硬件」的概念；② 四个布局变量化（card-width/safe-gap/card-bottom/overlay-clearance）工程素养好；③ 按横竖方分档让位的处理聪明。

**问题诊断**：① blur(30px)+saturate(1.14)+白 14% 描边是教科书级 2020 初代玻璃拟态，现在看是「磨砂贴膜」；② 金褐/暖金/蓝青三色光晕同 style-2 的问题；③ weather-desc 11px 全文件最小字号；④ 砍掉留言区是产品决策但未在任何地方说明理由。

**升级方向**：① 玻璃升级 Liquid Glass：blur 30→12、saturate 1.4、加 conic-gradient 边缘折射光（随时间缓慢旋转 60s）；② 光晕收敛为单色暖金；③ weather-desc 提到 12px；④ 若定位就是纯时钟卡，把日期/农历/宝宝年龄换算加进来补信息价值。

**改进对比**：Before「磨砂贴膜+三个彩灯」→ After「一 Lamborghini 仪表玻璃般的折射悬浮卡」。

### 5. style-6 浅色海报 —— 评级 A- ｜ 优先级 P2 微调

**现状**：米白冷灰渐变 + Georgia serif 超大时钟（150px）+ 双行日期 + 无框天气的杂志刊头式排版。

**优点**：① **全项目排印素养最高的一款**——大衬线时钟、双行日期结构、12px 大写宽字距 greeting、去框去底的天气排版，就是 Editorial trend 本身；② 气泡透明化处理（旧消息 0.7）层级聪明；③ 52px 大控制按钮可达性最好。

**问题诊断**：① Georgia 是 1990s 网页老衬线，字面平庸，撑不起 150px 的展示位；② placeholder rgba α0.34 / sender-name α0.48 对比度不足（上轮 a11y 修复未覆盖到这两处）；③ 浅色款共用的小屏规则会把它的大时钟 clamp 抹平成 52-84px，个性在小屏丢失。

**升级方向**：① Georgia → **Fraunces**（可变光学尺寸，现代编辑衬线的标杆）或 Instrument Serif，一行代码换气质；② placeholder/sender-name 透明度提到 0.55+；③ 小屏 clamp 下限从 52px 提到 64px 保住海报感。

**改进对比**：Before「用老报纸字体排的杂志」→ After「用 Fraunces 排的就是当代杂志本身」。

---

## 二、独立模板风格（style7~19）

### 6. style7 日式禅意（zen） —— 评级 A- ｜ 优先级 P2 微调

**现状**：纸纹底 + 圆形相框 + 竖排题签 + 红印章的低饱和三色构图，全项目最克制（0 keyframes）。

**优点**：① 克制是美德也是执行力：全款仅 1 条 transition，侘寂气质靠「不做」达成；② 竖排 writing-mode + 印章双字「記憶」的文化元素完整不堆砌；③ #F5F3EF 纸底 + #C44536 印章红的配色是日本传统色正路（朱色）。

**问题诊断**：① 色值全部硬编码、无 :root token，是 13 模板中「最需要 token 化的正面典型」；② 10px meta 小字（:242）与 700px 断点 9px；③ 照片 sepia(0.15) 全局滤镜会让非暖调照片显脏。

**升级方向**：① 建 :root 三色 token（纸/墨/朱）；② meta 字号提 12px；③ sepia 滤镜降到 0.08 或只用于题签底图；④ 印章加一次性的 1.2s 盖章入场动画（scale 1.15→1 + 轻微 rotate），这是「克制动效」的正确用法。

**改进对比**：Before「安静的茶室」→ After「同一种安静，但盖章那一下有生命」。

### 7. style8 赛博朋克（cyberpunk） —— 评级 B ｜ 优先级 P1 打磨

**现状**：#0A0E27 深底 + 霓虹粉/青/黄三色 + 扫描线 + HUD 四角框 + Orbitron 时钟的全套赛博语言。

**优点**：① 概念执行完整度高的「主题款」：网格、扫描线、HUD、辉光管各就各位；② Orbitron 用于科技时钟选型正确；③ 引文文本 #FFE8F7 保证了可读性底线。

**问题诊断**：① 三层霓虹 text-shadow（15/30/45px 三层辉光）是 2018 vaporwave 的「夜店招牌」手法，当代赛博美学已转向「终端绿/单色磷光」的克制路线；② 全屏扫描线 mix-blend-mode:screen 每帧合成，性能与审美双输；③ 中文回退 monospace 栈——Orbitron 无汉字，中文全落系统默认，霓虹英文+普通宋体的混搭很破功；④ HUD 定位硬编码 top:200px，移动端只改尺寸不改位。

**升级方向**：① 辉光三层减为一层（blur 8px 以内），主色收敛为单色青 #00F0FF，粉黄降为点缀（≤2 处）；② 扫描线删掉或降为 6s 一次、高度 1px、透明度 0.06 的「示波器呼吸线」；③ 中文栈补 Noto Sans SC 500，数字 Orbitron + 中文黑体的对位才成立；④ HUD 改用 inset 双细线（1px）+ 半透明填充，从「霓虹管」变「仪器面板」。

**改进对比**：Before「2018 年的夜店招牌」→ After「《银翼杀手 2049》里 that 仪器面板——冷、准、贵」。

### 8. style9 和风（japanese） —— 评级 B+ ｜ 优先级 P2 微调

**现状**：木质相框 + 樱花粒子 + 书法体数字 + 双 img 氛围层的满配和风，天气逻辑全项目最完整。

**优点**：① 季节感元素最全（樱花/木纹/抹茶绿/樱粉）；② 天气图标映射 + 关闭态 + 异常回退是全部 19 款中最健壮的实现；③ 按宽高比分档 padding（is-landscape/portrait/square）的处理聪明。

**问题诊断**：① 10-12 片樱花花瓣 14-24s 循环飘落，量大就成了「网页特效」；② Yuji Syuku 书法体做时钟数字，装饰性 > 可读性（"1"和"7"在这个字体里几乎认不出）；③ 木纹用 CSS 渐变模拟偏 iOS 拟物旧味；④ 双 img 氛围层（blur20 全屏）GPU 代价不小。

**升级方向**：① 花瓣减到 5-6 片、时长拉到 25-40s、透明度 0.6——从「下雪」变「偶尔一片落下」；② 时钟数字换 'Noto Serif JP' 500 + tnum，书法体只留标题「今日」二字；③ 木框扁平化：去掉渐变高光，改纯色 #D4A574 + 1px 深木描边；④ 氛围层 blur 20→14 且只保留一张。

**改进对比**：Before「樱花主题屏保」→ After「一间有光影的和室，花瓣偶尔飘过」。

### 9. style10 北欧极简（nordic） —— 评级 B+ ｜ 优先级 P2 微调

**现状**：纯白底 + 双层极细边框 + 2px 圆角 + 冰蓝点缀，四个「几乎不可见」的环境动效。

**优点**：① 2px 圆角 + 1px 双层描边是北款最纯正的做法；② Inter + Noto Sans SC 栈干净；③ motion-active 类直接禁用全部动画，尊重用户偏好做到了 JS 层。

**问题诊断**：① 四个 @keyframes（frameAura/shadowBreath/quietShimmer/polarGlow）周期 16-24s、幅度极小——**不可感知的动画等于不存在的动画**，纯耗电；② polarGlow 极光渐变安在北欧款上概念牵强（北欧设计语言是高对比黑白+一抹信号色，不是极光）；③ 照片用 div background-image，加载失败静默显示灰底无任何兜底；④ #777 次文本对白底 4.0:1 压线。

**升级方向**：① 删除全部四个不可感知 keyframes（或合并成一个 frameAura 并放大到可感知幅度）；② 冰蓝 #B8D4E3 用得更狠一点——时钟数字或当前时段标签整体用它，北欧的「一抹色」哲学；③ 照片容器补 Image 预加载探测 + 失败占位（复用 style.css 的 .gallery-image-error 模式）；④ #777 → #5f5f5f。

**改进对比**：Before「看不出动效的动效 + 不好意思用力的蓝」→ After「黑白灰里一记干净的冰蓝」。

### 10. style11 复古胶片（vintage） —— 评级 A- ｜ 优先级 P2 微调

**现状**：胶片黑底 + 双层齿孔 + SVG 噪点 + 漏光渐变 + 暗房暖黄的完整胶片世界。

**优点**：① 概念完成度 13 模板最高：齿孔双层实现（CSS 渐变+DOM 双保险）、feTurbulence 真噪点、漏光 radial 都是有据可依的胶片物理特征；② Playfair Display + Noto Serif SC 的衬线组合正确；③ 暖黄 #F4E4C1 做暗房主文本的对比度处理在线。

**问题诊断**：① 装饰元素叠满后接近「主题公园化」——噪点+齿孔+漏光+双面板边框+打捞滤镜五件套全开，缺主次；② grain 层 fixed 全屏 z-index:100 常驻合成；③ 11px salvage badge；④ 无翻页交互，5min 定时是唯一切图方式。

**升级方向**：① 做减法：漏光与噪点二选一（建议留噪点删漏光，噪点是胶片本质、漏光是特效）；② 齿孔改顶部单条横排（Kodak 金边布局），释放两侧空间；③ 加「胶片边印字」细节：框底 10px 大写字距的 `KODAK PORTRA 400 ▸ FRAME 17` 式刻字（用真实照片 id/日期填充）——这类微排版是复古感的当代做法；④ badge 提 12px。

**改进对比**：Before「胶片元素大满贯」→ After「一帧真的从暗房洗出来的底片」。

### 11. style12 悬浮画框（floating） —— 评级 B ｜ 优先级 P1 打磨

**现状**：深蓝三段渐变背景上单只 16:10 画框 3D 浮动，鼠标视差 + 独立阴影层。

**优点**：① 3D 视差（rAF 节流）+ translateZ 独立阴影层的技术实现是 13 模板中最讲究的；② 唯一自带 img onerror 重试的旧款；③ 零外链，最轻量。

**问题诊断**：① 背景三段深蓝渐变（#1a1a2e→#16213e→#0f3460）是 2018 渐变潮的标准配色，且和「悬浮画框」的画廊概念无关；② 'Segoe UI' 系统栈零排印处理，chip 文字像系统通知；③ 无时钟——作为常驻相框连时间都没有，信息功能残缺；④ float 6s 浮动 + hover 暂停的互动组合不错，但幅度（rotateX/Y 微倾）配 2000px perspective 偏小。

**升级方向**：① 背景改 #101012 纯深灰 + 一道极淡的顶部环境光（模拟画廊射灯），渐变删除；② chip 排版升级：12px 大写 + tnum + 0.1em 字距；③ 加极简时钟 chip（右下角，Inter 300 tnum）；④ 视差幅度 ÷20 → ÷12，让 3D 真的被感知。

**改进对比**：Before「渐变背景上的漂浮 demo」→ After「画廊射灯下的一只真画框」。

### 12. style13 瀑布流（waterfall） —— 评级 C+ ｜ 优先级 P0 重做视觉层

**现状**：五色循环渐变动画背景 + 白卡片瀑布流 + 标签筛选 + 无限滚动，交互最强、视觉最旧。

**优点**：① 交互功能 13 模板最丰富：标签筛选（top12 归一化）、IntersectionObserver 无限滚动、批次自适应、实时状态条；② break-inside:avoid + 4K 五列的布局工程正确；③ 受控横滑筛选条处理得当。

**问题诊断**：① **五色循环渐变动画背景（#ffecd2→#fcb69f→#a1c4fd→#c2e9fb，15s 无限循环）是全项目最过时的单一元素**——2018 渐变潮 + 彩虹配色 + 还在动，三连击；② 强制 aspect-ratio 4:3 + contain，非 4:3 照片全部 letterbox，瀑布流的灵魂（原始比例）被自己阉割；③ Open Sans 是「没有选择的字体」，2008-至今的默认安全牌；④ 卡片 hover 白色 outline + 上浮是 Pinterest 2016 年做法。

**升级方向**：① 背景 → #faf9f7 暖纸白纯色（或极淡噪点），渐变动画删除；② aspect-ratio 改 `auto` + object-fit cover 按原始比例瀑布流（这才叫瀑布流）；③ Open Sans → 'Outfit' 或 Inter（几何无衬线，配瀑布流的干净感）；④ 卡片改 bento 式：照片 + 底部 2 行信息（标题/日期左对齐、标签右对齐 11px→12px 大写），hover 只留 translateY(-4px) + 阴影加深，去 outline；⑤ 筛选按钮组改「胶囊 + 下划线 active 态」替代色块填充。

**改进对比**：Before「彩虹渐变上的 Pinterest 仿站」→ After「暖纸底上的 Muji 照片墙——功能不变，气质换血」。

### 13. style14 全景卷轴（panoramic） —— 评级 B- ｜ 优先级 P1 打磨

**现状**：横向 scroll-snap 卷轴 + 拖拽/滚轮/触摸三通道 + 彩虹进度条 + 灰渐变背景。

**优点**：① 交互工程最完整：拖拽（防误触阈值）、滚轮横映射、触摸 1.5x、懒加载、批次追加；② scroll-snap x mandatory 用得正确；③ 入场交错动画（80ms 间隔）有节奏感。

**问题诊断**：① **彩虹渐变进度条（红黄绿 linear-gradient）是 2015 拟物残留**，也是全项目第二处彩虹元素；② 背景三段灰渐变（#0c0c0c→#1a1a1a→#2d2d2d）平庸且无叙事；③ 'Segoe UI' 无排印处理；④ 无键盘左右键支持（无障碍断层，focus-visible 样式存在却无可聚焦元素）；⑤ 触摸处理未 preventDefault，可能与原生滚动叠加出双速。

**升级方向**：① 进度条改 2px 单色 #d4af37 金线（配影院概念）或 #fff 40% 透明度；② 背景改 #0a0a0a 真黑 + 底部 8% 高度的倒影渐变（照片地板反射，影院叙事）；③ 标签加排印：1rem/300 大号照片序号 + 0.9rem 说明的两行结构；④ 补 keydown 左右键翻卷（scrollBy 一个 snap 宽度）+ tabindex=0；⑤ touchmove 补 preventDefault 逻辑判断。

**改进对比**：Before「彩虹进度条的相册横滑」→ After「暗厅里的连续放映墙」。

### 14. style15 拍立得墙（polaroid） —— 评级 C ｜ 优先级 P0 重做字体层

**现状**：拍立得卡片墙 + 3D 翻转看背面便签 + 胶带图钉装饰 + 全站可编辑元数据（唯一带编辑器的风格）。

**优点**：① **功能价值 13 模板最高**：点击编辑日期/标签、CSRF 带全、防抖自动保存、Esc 关闭——是唯一「能整理照片」的风格；② 3D 翻转 + 随机倾斜的手作感方向正确；③ 背面便签的「写笔记」概念有生活味。

**问题诊断**：① **Dancing Script 全站应用是全项目最过时的字体决策**——2012 网页手写体潮，且该字体几乎不含汉字，中文全部回退系统默认，「手写感」在中文环境下直接破功；② 'Open Sans' 被引用约 10 处但 head 从未加载——所有 toolbar/按钮实际渲染的是系统字体，「设计」名存实亡；③ 图钉红 #ff6b6b radial 装饰与卡片固定 350px 高度（竖图溢出或横图留白）；④ 墙卡片 img 无 onerror。

**升级方向**：① 字体层重做：标题/手写感 → 'Caveat'（英文）+ 'Klee One'（日文手写、含汉字，Google Fonts 有）；正文/按钮 → 'Noto Sans SC'；Dancing Script 仅保留在「日期涂鸦」一处；② 修 Open Sans 加载（或干脆随 ① 移除引用）；③ 图钉改内联 SVG（真实图钉造型 + 阴影），卡片高度改 aspect-ratio 自适应；④ 墙 img 补 onerror 占位。

**改进对比**：Before「英文手写体贴在中文墙上」→ After「真的像手账本里一页——字是写的，照片是贴的」。

### 15. style16 艺术画廊（gallery） —— 评级 A- ｜ 优先级 P2 微调

**现状**：暗蓝底金色系策展网格 + 双 spotlight 跟随 + 展签卡片 + 自动对焦轮播，「光影典藏馆」。

**优点**：① 概念层级最高：spotlight 光标跟随 + 卡内 radial 对焦 + 6800ms 自动巡展，真的有「策展」叙事；② 唯一零 webfont 的系统衬线栈（Noto Serif SC/Songti/Georgia）——聪明且零加载成本；③ 描述 hover 展开（2 行→5 行）是正确的渐进披露。

**问题诊断**：① 标题金渐变（#d4af37→#f5d76e background-clip:text）+ drop-shadow 偏「酒店大堂金字」——画廊该哑光；② --photo-bg 变量 JS 写入但 CSS 无消费点（死代码）；③ 960-1420px 恒 2 列，中间尺寸浪费；④ tag clamp 下限 11.2px 压线。

**升级方向**：① 金渐变字 → 纯色 #d4af37 + 取消 drop-shadow，金色只用于展签标题与分隔细线（哑光金才是美术馆）；② 删 --photo-bg 死代码；③ 960-1420 区间补 2→3 列断点（1100px 起 3 列）；④ tag 12px；⑤ 展签排版对齐美术馆规范：作品名衬线斜体、年份与收藏者小字分离、编号用衬线数字。

**改进对比**：Before「金色大堂风的艺术网站」→ After「美术馆真正挂画的那面墙」。

### 16. style17 黑胶唱机（french） —— 评级 B+ ｜ 优先级 P0 修 bug

**现状**：暗金双栏——左侧唱机控制台（VU 表头 + 辉光管时钟 + 旋转唱盘）+ 右侧唱片封套大图。

**优点**：① 概念是 13 模板最独特的：黑胶+Hi-Fi 主题在相框产品里独一份；② 辉光管时钟（琥珀双层辉光 + Space Mono + tnum）是全项目最迷人的时钟实现；③ vinylSpin 20s 匀速是唯一合理存在的 CSS 无限动画（唱盘本来就该转）。

**问题诊断**：① **#weather-temp 永远显示 "--°C ☀️"——天气 UI 渲染了但脚本无任何更新逻辑（bug）**；② VU 表是纯装饰——不会动的 VU 表就是塑料模型，Hi-Fi 迷一眼出戏；③ vu-badge 11px；④ fetch 用 /api/photos 而 15/16 用 /api/images（接口不统一）；⑤ 留言区只有静态文案。

**升级方向**：① 修天气：接入与 style9 相同的 weather-config 逻辑（含图标映射与关闭态），或删掉天气行——占位比没有更糟；② VU 表活起来：两个指针各绑一个不同周期的 CSS rotate 动画（8s/13s，角度 ±30°），播放感立刻成立；③ badge 12px；④ 接口与 15/16 归一到 /api/images；⑤ 留言区接 /api/messages（style7 有现成实现可抄）。

**改进对比**：Before「漂亮的黑胶模型，表针不会动，天气是假的」→ After「一台真的在放歌的唱机」。

### 17. style18 空间折光（prism） —— 评级 B ｜ 优先级 P0 修 bug + P1 概念落地

**现状**：全屏暗场中央 3D 玻璃相框 + 左上毛玻璃环形时钟挂件 + 鼠标视差。

**优点**：① Plus Jakarta Sans 是全部 19 款中最当代的字体选择（2024+ 几何人文无衬线）；② 毛玻璃挂件 + 时钟渐变字的「悬浮仪表」气质对味；③ 视差曲线（÷40）手感克制。

**问题诊断**：① **#weather-desc 永远显示「晴朗 • --°C」（bug，与 17 同病）**；② `--prism-purple: #7f00ff` 声明后全文零使用（死代码，且这个紫本身就该删）；③ **「折光」概念没有动态表达**：相框是死的——没有 keyframes、没有折射光效，只有静态玻璃模糊，名字里最核心的「折光」停留在文字上；④ 时钟 白→cyan 渐变字贴 AI-Slop 边缘。

**升级方向**：① 修天气（同 17 方案）；② 删 --prism-purple；③ **给「折光」兑现**：相框边缘加一圈 conic-gradient 细光边（cyan→blue→transparent，60s 缓慢旋转，opacity 0.4），照片换片瞬间光边闪一次——概念即动效；④ 时钟渐变字改纯白 + 单独秒数用 cyan（排印对比替代渐变）；⑤ inline onclick 换 addEventListener（与全局整改对齐）。

**改进对比**：Before「叫折光的静态玻璃框」→ After「边缘真的有一道光在缓慢折射的相框」。

### 18. style19 建筑折纸（origami） —— 评级 B- ｜ 优先级 P0 修 bug + P1 概念落地

**现状**：浅色双平面构图——左「建筑刻印墙」（Bodoni Moda 时钟/天气/留言）+ 右白色悬浮主图平面。

**优点**：① 唯一全浅色单屏款，#eae8e1 暖灰底 + #1c1b18 墨色的纸感配色干净；② Bodoni Moda 的衬线时钟 + 12px/0.28em 大写刻印排版，建筑图纸气质高级；③ 三款新风格中排版素养最高。

**问题诊断**：① **致命执行塌陷：.arch-front-plane 的 translateZ(20px) 没有任何祖先设 perspective——3D 双平面视觉完全失效**，核心卖点「前后景深错位」现在是一张平面贴图；② #weather-temp/--°C 与 #weather-desc「晴朗」永远占位（bug，17/18/19 三连）；③ 「折纸」没有一道折痕元素——既无折线也无纸厚度；④ 动效几乎为零（仅按钮 0.25s），静态到失去生气。

**升级方向**：① 补 `.arch-origami-stage { perspective: 1600px }` + 前平面 hover/换片时 translateZ 20→28px 的过渡——一行属性救活整个概念；② 修天气（同 17）；③ 折痕落地：左右平面交界处加 2px 渐变折痕线（阴影渐变模拟纸张折角）+ 主图平面右缘 1px 纸厚描边；④ 入场动画：前平面从 rotateY(8deg) 展开到 0（1.2s cubic-bezier），「折纸展开」一次即收。

**改进对比**：Before「平面效果图冒充 3D」→ After「真的立在桌面上的一张折纸」。

---

## 三、总览与优先级路线

### 评级总表

| 风格 | 名称 | 评级 | 一句话判决 |
|---|---|---|---|
| style-6 | 浅色海报 | **A-** | 排印最好，换掉 Georgia 即封神 |
| style7 | 日式禅意 | **A-** | 克制的典范，补 token 与盖章动画 |
| style11 | 复古胶片 | **A-** | 概念最完整，做减法更高级 |
| style16 | 艺术画廊 | **A-** | 策展叙事成立，金字改哑光 |
| style-2 | 沉浸全屏 | B+ | 大时钟有胆，光晕要收敛 |
| style9 | 和风 | B+ | 最健壮，樱花要减量 |
| style10 | 北欧极简 | B+ | 有教养，删无效动效 |
| style17 | 黑胶唱机 | B+ | 概念最独特，天气 bug 拖后腿 |
| style-1 | 经典分栏 | B | 合格基底，缺记忆点 |
| style-4 | 悬浮玻璃 | B | 玻璃语言该换代了 |
| style12 | 悬浮画框 | B | 3D 灵魂在，背景拖后腿 |
| style18 | 空间折光 | B | 字体最潮，「折光」没兑现 |
| style-3 | 画廊展签 | B- | 概念好，级联残留 + 行为不一致 |
| style14 | 全景卷轴 | B- | 交互最强，彩虹进度条拖后腿 |
| style19 | 建筑折纸 | B- | 3D 概念因缺 perspective 完全失效 |
| style13 | 瀑布流 | **C+** | 功能最强、视觉最旧，渐变背景必须换血 |
| style15 | 拍立得墙 | **C** | 编辑功能最好，字体层必须重做 |

### 分级整改路线图

**P0 —— bug 与硬伤（必须修，预计 1 天）**
1. style17/18/19 天气占位 bug：三款共用同一套天气接入（含图标映射与关闭态），一次写完三处接入
2. style19 补 `perspective: 1600px`（一行救活 3D 概念）
3. style15 修 Open Sans 未加载 / 字体层重做（Caveat + Klee One + Noto Sans SC）
4. style13 渐变动画背景换血 + aspect-ratio 回归原始比例
5. style18 删 --prism-purple 死代码

**P1 —— 过时感清除（预计 1-2 天）**
6. style8 三层霓虹收敛 + 扫描线降级 + 中文栈补齐
7. style-2/style-4 光晕收敛 + 玻璃升级 Liquid Glass 2.0
8. style14 彩虹进度条改单色 + 补键盘滚动
9. style-3 清理级联残留 + controls 行为对齐
10. style12 背景改画廊射灯 + 补时钟
11. style18 折光光边兑现 / style19 折痕落地（概念补完）

**P2 —— 精修（择机）**
12. style-6 Georgia → Fraunces / style-1 光斑减淡 / style7 token 化 + 盖章动画
13. style9 樱花减量 / style10 删无效动效 + 冰蓝放大 / style11 减法 + 胶片刻字
14. style16 哑光金 + 三列断点

### 横向系统性建议

1. **天气逻辑统一化**：style9/10 已有完整实现，17/18/19 完全缺失——抽一个 `weather-widget.js` 公共模块是 P1-5（公共交互层）的第一块砖，性价比最高。
2. **接口归一**：style17/18/19 用 /api/photos，style15/16 用 /api/images，分叉无理由，建议统一。
3. **字体策略收敛**：19 款共 11 种 webfont 组合。建议定 4 款「字体角色」：几何无衬线（Outfit/Plus Jakarta）、当代衬线（Fraunces/Bodoni Moda）、中文正文（Noto Sans/Serif SC）、点睛手写（Caveat/Klee One），新风格从中取用，淘汰 Orbitron 之外的孤品字体。
4. **P1-5 兑现路径**：本轮发现 17/18/19 脚本近乎逐行复制 + 天气三连缺失，正好以「天气模块 + 轮播模块」作为公共层重构的两个首批模块，风险可控、收益立现。

---

## 八、逐项修改对照表（2026-09-28 精细化打磨执行记录）

> 状态标记：✅ 已落实 ｜ ◑ 部分落实 ｜ ⏸ 处理说明（含理由）

### P0 —— bug 与硬伤

| # | 评审意见 | 状态 | 修改位置与方式 |
|---|---|---|---|
| P0-1 | style17/18/19 天气永远占位 | ✅ | 新建 `static/weather-widget.js` 公共模块（数据源 `/api/weather-config`，天气码→图标/中文描述映射，含关闭态与异常占位；自动探测 `#weather-temp/#weather-desc/#weather-icon` 适配三款不同布局：17 单徽标组合式 / 18 单行组合式 / 19 三元素分体式）；三模板 `</body>` 前各加一行引入；另暴露 `window.WeatherWidget.refresh` 供后续联动 |
| P0-2 | style19 缺 perspective，3D 失效 | ✅ | `.arch-origami-stage` 补 `perspective: 1600px`；`.arch-front-plane` 补 `transition: transform 0.9s` + hover `translateZ(28px)` + `origamiUnfold` 入场动画（rotateY 8°→0°，1.2s 一次即收） |
| P0-3 | style15 字体过时 + Open Sans 未加载 | ✅ | head 字体链接 Dancing Script → `Caveat + Klee One + Noto Sans SC`；body `'Dancing Script'` → `'Noto Sans SC'`；卡片标题 `.polaroid-front/back h3` → `'Caveat','Klee One'`（手写感保留在标题，正文可读）；7 处 `'Open Sans'` 引用全部 → `'Noto Sans SC'`；墙卡片 img 补 error 斜纹占位 |
| P0-4 | style13 渐变背景 + 强制 4:3 | ✅ | 五色循环渐变动画 → `#faf9f7` 暖纸白纯色（`gradientShift` keyframes 一并删除）；img 删 `aspect-ratio: 4/3 + object-fit: contain` → `height: auto` 原始比例真瀑布流；Open Sans → Inter（head 双链接 + 全部引用） |
| P0-5 | style18 --prism-purple 死代码 | ✅ | `:root` 中删除该声明 |

### P1 —— 过时感清除

| # | 评审意见 | 状态 | 修改位置与方式 |
|---|---|---|---|
| P1-6 | style8 三层霓虹/扫描线/中文栈/HUD | ✅ | 时钟 `#FF2E93`+三层辉光 → `#00F0FF`+单层 8px 微光；扫描线 3px 双色 → 1px 单色青（box-shadow 20px/0.8→10px/0.25）；HUD 3px 实线霓虹管 → 1px 细线 + `rgba(0,240,255,0.04)` 半透明填充；head 补 `Noto Sans SC`，body 栈 → `'Orbitron','Noto Sans SC',monospace`（中文不再裸奔系统默认）。相框 3px 青描边保留（主色身份元素，符合收敛方向） |
| P1-7 | style-2/4 三色光晕 + 初代玻璃 | ✅ | index.html：`--style2-panel-color-a/b/c` 与 `--style4-card-color-a/b/c` 三色变量全部收敛为单一暖金 `238,204,128`；style-2 面板 blur 18→10 + saturate 1.2 + 内侧 1px 高光；style-4 面板 blur 30→12 + saturate 1.4 + 高光 0.10→0.18 |
| P1-8 | style14 彩虹进度条 + 无键盘支持 | ✅ | 进度条 3px 红黄绿渐变 → 2px 单色金 `#d4af37`；容器补 `tabindex="0"` + aria-label；JS 补 keydown 左右键平滑滚动（步长 max(420px, 80% 视口)） |
| P1-9 | style-3 级联残留 + controls 不一致 + 衬线混搭 | ✅ | 删除 `:653` 暗底残留块（`rgba(14,16,22,0.72)` + `blur(28px) saturate(140%)`——浅色面板不该背暗玻璃）；补 `html[data-home-style="style-3"] #controls { opacity: 0.9 }` 对齐兄弟款；greeting 字体栈去掉从未加载的 `'Cinzel'` → `'Georgia', serif` |
| P1-10 | style12 渐变背景/无时钟/chip 素排印/视差弱 | ✅ | 背景三段蓝渐变 → 画廊射灯（`radial 顶部暖光 0.06 + #101012`）；meta chip 补 `letter-spacing 0.12em + tabular-nums + uppercase`；JS 新增左下角极简时钟 chip（1s tick，tnum）；视差幅度 ÷20 → ÷12 |
| P1-11 | style18「折光」未兑现 / style19「折痕」缺失 | ✅ | style18：`.prism-photo-card::after` 加 conic-gradient cyan→blue 光带，60s 缓旋扫过相框（opacity 0.10-0.12，pointer-events none）；时钟渐变字 → 纯白（秒级信息用排印对比替代渐变）。style19：`.arch-back-wall::after` 折痕线（48px 间隙中 2px 渐变竖线）+ 前平面 `border-right-color` 加深模拟纸厚 + 左缘内侧 2px 折线 `::before` |

### P2 —— 精修（便宜项落实，重排印项说明）

| # | 评审意见 | 状态 | 修改位置与方式 |
|---|---|---|---|
| P2-12a | style-6 Georgia→Fraunces | ✅ | head 加载 `Fraunces:wght@300;400`；`.time`/`.date` 字体栈 → `'Fraunces', Georgia, ...` |
| P2-12b | style-6 placeholder/sender 对比度 | ✅ | placeholder `rgba(36,48,56,0.34)` → `0.55`；sender-name `0.48` → `0.62` |
| P2-12c | style-6 小屏时钟下限 | ✅ | 共享小屏规则 `clamp(52px,…)` → `clamp(64px,…)` |
| P2-13a | style-1 光斑减淡 | ✅ | body 双 radial 光斑透明度 0.05→0.03 / 0.10→0.06（约 -40%） |
| P2-13b | style-1 时钟 120px + 大写标签行 | ⏸ | 涉及信息层级新增（非单行改动），留待 style-1 专项微调；当前 B 级不阻塞 |
| P2-14a | style7 meta 字号 + sepia + 盖章动画 | ✅ | `.zen-meta-item` 10px→12px 且 α0.78→0.9；700px 断点 9px→11px；照片 `sepia(0.15) contrast(0.95)` → `sepia(0.08) contrast(0.97)`；`.seal` 补 `sealStamp` 入场（0.6s 延迟，scale 1.6→1 + rotate -6°→0°，一次即收） |
| P2-14b | style7 :root 三色 token 化 | ⏸ | 全文件 30+ 处硬编码色值替换属机械重构，盲改无浏览器回归兜底，与 P1-5 公共层重构同批处理更安全 |
| P2-15a | style9 樱花减量/时钟/氛围层 | ✅ | JS：花瓣 12/10 → 7/5 片，时长 14-24s → 25-40s，补 opacity 0.6，DOM 上限同步 7；时钟 `'Yuji Syuku'` → `'Noto Serif JP'` + `tabular-nums`（书法体退居装饰）；氛围层 blur 20→14 |
| P2-15b | style9 木框扁平化 | ⏸ | 木纹渐变是该款识别性元素，扁平化属审美方向变更，建议先出两版对比再定 |
| P2-16a | style10 删四个不可感知动效 | ✅ | `frameAura/shadowBreath/quietShimmer/polarGlow` 四组 keyframes 及全部引用删除（`motion-active` 禁用开关保留） |
| P2-16b | style10 冰蓝落时钟 | ◑ | 时钟 `--dark-gray` → `#4A7C95`——评审原文建议用 `--ice-blue`，但 `#B8D4E3` 对白底仅约 1.6:1 连大字 3:1 都不达，改用同族深冰蓝（WCAG 4.6:1），意图一致、可读性合规 |
| P2-16c | style10 onerror + #777 | ✅ | JS 补 Image 预加载探测 + `.photo-load-error` 斜纹占位类；两处 `#777` → `#5f5f5f` |
| P2-17a | style11 漏光与噪点二选一 | ✅ | 删漏光（HTML 元素 + 基础规则 + has-salvaged 变体规则三处），保留噪点（胶片本质） |
| P2-17b | style11 齿孔改顶置 + 胶片刻字 | ⏸ | 齿孔双层改单条属布局重构；刻字需新数据通道（照片 id/日期注入）；两者归入 style11 专项迭代 |
| P2-18a | style16 哑光金 + 死代码 + 断点 + tag | ✅ | 标题金渐变+drop-shadow → 纯色 `var(--gold-1)`；`--photo-bg` CSS 初始化与 JS 写入两处死代码删除；3 列断点 1420px→1200px；tag `clamp(0.7rem,…)` → `0.75rem`（12px） |
| P2-19 | style-3 衬线统一 | ✅ | 并入 P1-9：`'Cinzel'` 移除（本就未加载），统一 Georgia 系 |
| P2-20 | style15 图钉 SVG 化 / 卡片自适应高 | ⏸ | 图钉改 SVG + 350px 固定高改 aspect-ratio 属视觉重排，与拖拽排序 TODO 同批 |
| P2-21 | style13 bento 信息条 / 筛选胶囊化 | ⏸ | 卡片结构重排属布局重构，本轮仅完成背景/比例/字体三层换血（C+→B 档），结构层留专项 |

### 系统性建议

| # | 建议 | 状态 | 说明 |
|---|---|---|---|
| 系-1 | 天气逻辑模块化 | ✅ | `weather-widget.js` 已落地并被 17/18/19 三款接入——这正是 P1-5 公共交互层的第一个模块 |
| 系-2 | 接口归一 /api/images | ⏸ | style17/18/19 现用 `/api/photos`（`p.display_url || /api/photos/{id}/image`），与 `/api/images` 响应结构不同，切换需同步改数据映射；盲切风险大于收益，归入 P1-5 公共层重构批次 |
| 系-3 | 字体四角色收敛 | ◑ | 本轮已引入 Fraunces（当代衬线）/ Caveat+Klee One（点睛手写）/ Noto 系（中文正文）并对齐到角色制；Orbitron 保留于 style8（主题字体身份），全量收敛待新风格持续按角色制取用 |
| 系-4 | P1-5 公共交互层 | ◑ | 天气模块已落地为首块砖；轮播模块（17/18/19 近逐行复制脚本）待第二批 |

### 验证记录

- `node --check`：weather-widget.js / script.js / unified-style-menu.js 全部通过
- jinja2 解析：17/17 模板通过
- 遗留清剿全部归零：Dancing Script / Open Sans（style15、style13）/ light-leak（style11）/ gradientShift（style13）/ 四组 keyframes 引用（style10）/ prism-purple（style18）
- git 工作区变更 55 个文件（含此前 UI 门禁整改与本轮风格打磨）

### 诚实声明（执行中的三次自我纠错）

1. style10 清引用时误将 `frameAura` 替换成了 `shadowBreath`（应为删除）——已发现并用上下文区分修正，两处均已删除
2. style16 死代码 JS 清理时误插入一行 `--mouse-x` setter（应为纯删除）——已删除，并确认与聚光灯 JS 无冲突
3. weather-widget.js 收尾时误加无意义注释——已回滚

三处均已在终检中确认归零，最终状态以本对照表为准。

---

## 九、自查复审记录（2026-09-28 · 第二轮）

打磨落地后，主理人对**自己新引入的代码**再做一轮评审——重点不是风格品味，而是「新代码与既有元素的坐标/层级/填充冲突」。逐查 15+ 嫌疑点，结论：

### 抓到并修复的回归（2 个）

| # | 问题 | 根因 | 修复 |
|---|---|---|---|
| 复-1 | style12 新增时钟 chip 与既有 meta chip **完全重叠**（两者同为 `left:24px; bottom:22px` fixed） | 加时钟时只看了「哪个角落空着」的主观印象，没核对既有 chip 坐标 | 时钟 chip 迁至右下角 `right:24px; bottom:22px`（左下 meta、右上 salvage、右下为唯一空位） |
| 复-2 | style7 印章动画 `to { opacity: 1 }` + `both` 填充，动画结束后**永久覆盖**基础 `opacity: 0.85` 的墨色感 | 写 keyframes 时没回头核对 `.seal` 基础透明度 | 终帧对齐 `opacity: 0.85`，盖章后保持墨韵 |

### 排除的虚惊（2 个）

1. **style-3 greeting 白字隐形疑云**：清理残留块后担心 `color: rgba(255,255,255,0.90)` 在米纸底上不可见——查证 `:922` 分组规则已将 greeting/date/weather-desc/sender-name 统一覆盖为深色 `rgba(22,22,22,0.58)`，无问题。
2. **style7 印章 transform 冲突疑云**：担心 `both` 填充抹掉基础 transform——查证 `.seal` 基础样式无 transform，无冲突。

### 一次通过项

style14 键盘监听的变量作用域（`scrollContainer` 定义于同块前方）✓；style18 光带 z-index 5 压过主图 z2（折光扫过照片表面为预期行为）✓；style19 折痕线 z3 高于图层级 ✓；style10 probe 与 photo-switching 无冲突 ✓；style17 `.vu-meter-header` 为 flex 布局，电平条成立 ✓；weather-widget 三种挂载形态与关闭态边界 ✓；style8 中文回退栈（Orbitron→Noto Sans SC→monospace）✓；style16 断点链（640→960→1200→2100→3200）无空洞 ✓。

### 复审后的方法沉淀

本轮两个回归同属一类：**写新代码时没有回头核对它与既有元素的坐标、层级、填充状态的冲突**。静态检查清单新增三条：新增 fixed/absolute 元素先 grep 同象限既有元素；新增 animation 的终帧必须对齐目标元素的基础态（opacity/transform）；新增 z-index 前先列出同上下文既有层级。
