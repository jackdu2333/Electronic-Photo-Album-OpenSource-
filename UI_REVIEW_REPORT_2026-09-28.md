# UI/UX 全量评审报告（界面美学所 · uiteam）

- **评审日期**：2026-09-28
- **评审对象**：Electronic-Photo-Album-OpenSource- 前端全量（17 个模板 + 3 个静态资源，约 14,000 行）
- **评审团**：甄美琳（设计总监/主理人）、布理清（UX 策略）、颜如玉（视觉）、穆可凡（原型工程）、曾较真（质量门禁）
- **评审方式**：静态代码走查 + 主理人逐条证据复现（未做真机浏览器实测，涉及推断处均已标注）

---

## 一、最终结论：【Block】

**触发依据**：七项硬门禁中三项违规（#1 对比度、#3 触控目标、#4 键盘焦点），叠加 2 个 HIGH 级缺陷（XSS 注入向量、触屏横屏核心控制不可见）。按工作室门禁章程，硬门禁违规直接 Block。

**积极面先说清楚**：核心功能链路可用、无 Lorem ipsum、`href="#"` 全库零命中、`lang` 属性 17/17、iOS 设计语言有辨识度、19 套风格模板差异化是真实亮点。这个项目的底子不差，Block 是门禁意义上的「暂不可发布」，不是「产品不行」。修复 P0 五条后即可申请复审。

---

## 二、五维打分卡（满分 50，主理人修正版）

| 维度 | 得分 | 简评 |
| :--- | :---: | :--- |
| 任务完成度与易用性 | 12/15 | 核心链路顺畅；但触屏横屏控制不可见、空态缺失拖累体验 |
| 设计哲学与视觉层级 | 7/10 | iOS 语言清晰统一；三套主色并存 + 令牌双轨破坏色彩契约 |
| 细节执行与微交互 | 6/10 | 弹性按压/toast 打磨用心；幽灵触区、22px 按钮是硬伤 |
| 无障碍与规范合规 | 5/10 | 对比度/焦点/触控目标三项硬门禁违规 |
| 独特质感与适度创新 | 4/5 | 19 风格模板差异化是全项目最大亮点（曾较真原报 7/5 系笔误，主理人修正为 4/5） |
| **总分** | **34/50** | |

---

## 三、七项硬门禁检查表

| # | 门禁 | 结果 | 关键证据 |
|---|------|------|----------|
| 1 | WCAG AA 对比度 | ❌ 违规 | 见 P0-3 |
| 2 | 375px 无横向滚动 | ⚠️ 部分合规 | index.html:350-366 聊天输入框 62% 宽挤压；manage.html 超长文件名溢出策略不统一（静态推断，未实测） |
| 3 | 触控目标 ≥24px | ❌ 违规 | `.remove-btn` 22×22（style.css:335-350）；多按钮 32-38px 低于 44px 推荐值 |
| 4 | `:focus-visible` 焦点可见 | ❌ 违规 | 10/17 模板零 focus 样式（admin、style7/8/12/13/14/16/17/18/19） |
| 5 | 语义化 HTML | ⚠️ 部分合规 | `lang` 17/17 ✅；图标按钮缺 aria-label；部分表单 label 覆盖不全 |
| 6 | 真实数据与文案 | ✅ 合规 | 全库无 Lorem ipsum / 占位文本 |
| 7 | 无死链假控件 | ✅ 基本合规 | `href="#"` / `javascript:void` 全库零命中 |

---

## 四、问题与整改清单（证据链含主理人复核状态）

复核标记：✅ = 主理人已复现属实　◑ = 两名团员独立指证　△ = 单一来源未复核

### P0 —— 阻断级（5 条，修完可申请复审）

| # | 类别 | 问题与定位 | 修复建议 | 复核 |
|---|------|-----------|----------|------|
| P0-1 | 安全 | `admin.html:158` XSS 注入向量：`f.replace(/'/g,"\\'")` 反斜杠转义可被击穿——文件夹名以 `\` 结尾再含 `'` 即在 onclick 属性内逃逸出 JS 上下文 | 弃用内联 onclick 字符串拼接，改 `addEventListener` + `data-*` + `textContent` 渲染 | ✅ |
| P0-2 | 交互 | `index.html:480/492/1710` 触屏横屏下 `#controls` 永远 `opacity:0`：hover:none 块（:377）只覆盖聊天输入框，4 个横屏媒体块（:1767/2052/2150/2168）无补偿；且 opacity:0 仍拦截点击，形成幽灵触区 | 横屏块内补 `#controls { opacity: 1 }`，或全局 `@media (hover:none)` 兜底 | ✅ |
| P0-3 | 无障碍 | 对比度多处不达标：`style.css:16` `#8E8E93` 用于 12-13px 文字（白底约 3.26:1）；`admin.html:48-51` 内联 `#888/#666/#999`（`#999` 约 2.85:1）；`style.css:525-528` 警示按钮白字于 `#FF9500`（约 2.2:1）；`style.css:326-333` `.file-name` 10px 白字于渐变底 | 小字灰阶提至 `#6D6D72` 以上；警示按钮改深色文字；清理 `#999` 级内联色 | ✅（对比度为 WCAG 公式估算） |
| P0-4 | 无障碍 | 键盘焦点缺失：10/17 模板无任何 focus 样式，纯键盘用户在管理后台及 9 个风格模板中无法辨识当前位置 | 全局补 `:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px }` | ✅（grep 全库） |
| P0-5 | 无障碍 | 触控目标 < 24×24 AA 基线：`.remove-btn` 22×22（style.css:335-350）；gallery-overlay 按钮 30×30、全屏键 32×32 等低于 44px 推荐值 | 视觉尺寸可不变，用伪元素/负 margin 扩大命中区至 ≥44×44 | ✅ |

### P1 —— 需修复（发布前应完成）

| # | 类别 | 问题与定位 | 修复建议 | 复核 |
|---|------|-----------|----------|------|
| P1-1 | 视觉 | 三套主色并存：`#007AFF`（style.css:8,30）、`#3498db`（manage.html:19）、紫蓝渐变 `#7c5cff→#3f7cff`（login.html:128,440，违反反 AI-Slop 禁令） | 全局收敛到 `--color-primary` 单一来源；登录页渐换为品牌蓝系 | ✅ |
| P1-2 | 视觉 | admin.html 60+ 处内联魔法色（`#27ae60/#e74c3c/#999` 等）脱离令牌体系 | 抽取 admin 专属样式块，全部走 CSS 变量 | ✅ |
| P1-3 | 一致性 | 令牌双轨制：`--color-*` 与 `--app-*` 并存且值重复（style.css:8 vs :30 同为 #007AFF） | 合并为单套令牌，`--app-*` 过渡期 alias | ✅ |
| P1-4 | 工程 | `style.css:58` `--font-tabular-nums: "tnum","cv05",monospaced` 把 font-feature 值当字体族，声明无效 | 改为 `--font-numeric-feature: "tnum"` 配合 `font-variant-numeric: tabular-nums` | ✅ |
| P1-5 | 一致性 | 13 个风格模板中 11 个不加载 style.css，交互兼容靠 `unified-style-menu.js` 577 行 if-else 特判兜底 | 抽公共交互层/最小共享样式，降低特判复杂度 | ◑ |
| P1-6 | 一致性 | z-index 双轨：令牌变量已定义（style.css:42-50）但 `.ios-nav-bar`(:105)、`#toast-container`(:593) 仍硬编码 | 统一引用 `var(--z-*)` | ✅ |
| P1-7 | 无障碍 | `prefers-reduced-motion` 仅 2/17 模板支持（login、style16） | 全局补 reduced-motion 降级块 | ✅（grep） |
| P1-8 | 一致性 | style18/19 页面 `<title>` 与文件名/风格名错位（bauhaus.html 题为「空间折光光轨」、cinematic.html 题为「建筑折纸双平面」） | 对齐命名或更新菜单元数据 | ✅ |
| P1-9 | 无障碍 | 全屏/历史等纯符号图标按钮缺 `aria-label` | 补可访问名称 | ◑ |
| P1-10 | 触屏 | 风格菜单锚点按钮仅 28px（unified-style-menu.js:428），核心高频操作低于 44px 推荐 | 扩大命中区 | △ |
| P1-11 | UX | 空相册/加载失败态缺失或文案含糊；超长文件名溢出策略不统一 | 补空态插画+行动指引文案；统一 ellipsis 策略 | △ |
| P1-12 | 视觉 | Emoji 充当 UI 图标（admin.html:161 📁），违反全站内联 SVG 图标规约 | 换内联 SVG | ✅ |
| P1-13 | UX | 聊天输入框 62% 定宽在 375px 下挤压输入空间（index.html:350-366） | 改弹性宽度 | △ |

### P2 —— 建议（不阻塞）

| # | 问题与定位 | 说明 |
|---|-----------|------|
| P2-1 | 访客分享机制缺失 | auth.py:228-241 全局 before_request 鉴权，未登录 302→/login。私人相册属设计意图，但家庭分享场景建议增加只读 share-token 链接 |
| P2-2 | 命名双轨 | CSS 端 `data-home-style="style-1"`（带连字符）与 URL 参数 `?theme=style1`（无连字符）双轨，靠映射表维护，易在未来扩展时踩坑 |
| P2-3 | login.html:548-572 OAuth 图标 SVG 四处重复内联 | 抽 `<symbol>` 复用 |

### 评审中证伪的指控（不冤枉好设计）

1. ~~「访客访问首页 → 403 核心链路断裂」（布理清 G1，原 HIGH）~~ —— **证伪**：auth.py:241 实际为 302 重定向至 /login，且强制登录是私人相册的设计意图，降级为 P2-1 产品建议。
2. ~~「风格菜单写入 `style-1` 连字符格式，后端只认 `style1`，切换直接失败」（布理清 G3，原 HIGH）~~ —— **证伪**：unified-style-menu.js:6-23 的 id 全部无连字符，与路由映射键完全匹配，链路可用（仅存 P2-2 命名双轨问题）。
3. ~~「.gallery-name 11px」（曾较真 F12）~~ —— **证伪替换**：该类全库不存在；真实问题为 `.file-name` 10px（style.css:327），已并入 P0-3。

---

## 五、覆盖记录

| 评审人 | 覆盖范围 | 产出 | 主理人复核结果 |
|--------|----------|------|----------------|
| 布理清（UX） | 4 核心页 + 13 风格模板信息架构/任务流/文案 + 路由核对 | 2 HIGH、8 MEDIUM、5 LOW | 2 HIGH 均证伪降级；MEDIUM/LOW 采纳入 P1/P2 |
| 颜如玉（视觉） | style.css 全文 + 4 核心页 + 8 风格模板色彩/排印/反 Slop | 3 HIGH、7 MEDIUM、3 LOW | 3 HIGH 全部复现属实 |
| 穆可凡（工程） | script.js / unified-style-menu.js 全文 + 模板抽查 + XSS 向量分析 | 2 HIGH、若干 MEDIUM | 2 HIGH 全部复现属实（1 处表述修正：opacity:0 仍可命中，是「隐形占位」而非「不可点」） |
| 曾较真（门禁） | 17 模板 + 3 静态资源七门禁全查 + 50 分卡 | 3 门禁违规、36 整改条目 | 3 门禁违规属实；1 条证据证伪替换；打分笔误修正 |
| 甄美琳（主理人） | style.css 全文精读 + 9 次定向复现 + 2 项全库 grep | 仲裁终局 | —— |

**评审局限**：本次为静态走查，未启动真机/浏览器实测；375px 横向溢出类结论（门禁 #2、P1-13）为代码推断，建议修复后用真机复核。

---

## 六、修复路线图

1. **P0 五条（预计 0.5-1 天）**：XSS 修复 + 横屏控制一行 CSS + 焦点样式全局补齐 + 触控命中区扩大 + 对比度灰阶调整。全部是低风险小改动，不动业务逻辑。
2. **P1（1-2 天）**：色彩令牌收敛（含登录页渐变重做）、admin 内联样式抽离、z-index/令牌统一、reduced-motion、aria-label、风格菜单命中区。
3. **P2（择机）**：访客分享 token、命名双轨合并、SVG symbol 化。
4. **复审**：P0+P1 修完后提请曾较真复审，复审只聚焦整改清单条目，不做范围蔓延。

---

## 七、整改执行记录（2026-09-28 当日完成）

| 项 | 状态 | 执行摘要 |
|---|---|---|
| P0-1 XSS | ✅ 已修复 | admin.html 渲染改 `data-path` + 事件委托 + `escapeAttr` 属性转义，内联 onclick 拼接全部移除 |
| P0-2 触屏横屏 | ✅ 已修复 | index.html `(hover: none)` 块补 `#controls { opacity: 1 }`，另加 `:focus-within` 显现 |
| P0-3 对比度 | ✅ 已修复 | `--color-label4`→#6D6D72、`--app-text-secondary`→#6e6e73；警示按钮改深色文字；success/danger toast 改深色底（新增 `-dk` 令牌）；admin `#999` 系抽类；login remember-hint；index style-4（0.42→0.75 + 11px）/style-6（0.42→0.75）；style13 三处红→#d93025/#c5221f；manage 徽章→#1a5f8a；`.file-name` 11px + scrim 加深至 0.75 |
| P0-4 焦点 | ✅ 已修复 | style.css 全局 `:focus-visible` + index.html 与 13 个风格模板各自基线块（admin/login/manage 经 style.css 覆盖），移除 `#controls button outline:none` 并补焦点环 |
| P0-5 命中区 | ✅ 已修复 | `.remove-btn` 24px 视觉 + 伪元素扩至 44；gallery-overlay 按钮/链接伪元素扩至 44；usm-toggle 伪元素扩至 46 |
| P1-1 主色收敛 | ✅ 已修复 | manage → #007AFF/#0062CC；login 紫色全家（accent、logo 渐变、按钮渐变、焦点环、紫晕背景）→ 品牌蓝系 |
| P1-2 admin 魔法色 | ✅ 已修复 | 内联色抽为 `.admin-muted/.admin-hint/.admin-count/.admin-error/.folder-row/.folder-name/.folder-status/.folder-remove` 等类，全部走令牌 |
| P1-3 令牌双轨 | ✅ 已修复 | `--app-*` 全部改为 `var(--color-*)` 兼容别名 |
| P1-4 tabular | ✅ 已修复 | `--font-tabular-nums` 值修正为 `"tnum", "cv05"` |
| P1-5 公共交互层 | ⏸ 暂缓 | 架构级重构涉及 13 模板脚本合并，无真机验证兜底，建议单独立项 |
| P1-6 z-index | ✅ 已修复 | `.ios-nav-bar`/`#toast-container` 改引用 `--z-controls`/`--z-toast` |
| P1-7 reduced-motion | ✅ 已修复 | style.css + index + 13 风格模板全覆盖 |
| P1-8 文件正名 | ✅ 已修复 | style18-bauhaus.html→**style18-prism.html**、style19-cinematic.html→**style19-origami.html**；routes/main.py + routes/api.py 同步 |
| P1-9 aria-label | ✅ 已修复 | index 翻页按钮/留言输入框、manage 搜索框、style17/18/19 翻页按钮 |
| P1-10 usm 命中区 | ✅ 已修复 | 伪元素扩至 ≥44px，视觉不变 |
| P1-11 图片兜底 | ✅ 已修复 | style17/18/19 showPhoto onerror 自动跳片（连续失败熔断防死循环）；manage 缩略图斜纹占位；admin 画廊预加载探测 + `.gallery-image-error` 占位类 |
| P1-12 Emoji 图标 | ✅ 已修复 | admin 📁/📦 → 内联 SVG（aria-hidden） |
| P1-13 聊天宽度 | ✔️ 销案 | 复核证实为误报：index 无 62% 定宽，基础即 width:100% + flex:1 |
| P2-1/2/3 | ⏸ 未动 | 建议项，按清单「择机」处理 |

**验证记录**：`node --check` 两个 JS 通过；jinja2 解析 17/17 通过；routes 模板引用零缺失；旧色值（紫蓝/flat 蓝/旧红）、旧文件名、内联 onclick 全库清零。残留两处 `#ff6b6b` 均为非文本装饰（style14 彩虹渐变条、style15 装饰圆点），不在清单项内，保留。

**待办**：真机复测（375px 竖/横屏、iOS 输入聚焦缩放、读屏走查）；完成后提请复审。
