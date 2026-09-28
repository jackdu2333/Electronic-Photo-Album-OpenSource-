# 电子相框项目复审报告（2026-09-28）

> 审查人：Delores（AI Code Reviewer）
> 审查基线：main 分支 @ 74bbdae（Style 17~19 主题提交），工作区干净
> 上一轮报告：CODE_REVIEW_REPORT.md（2026-06-22）、PROJECT_REVIEW_REPORT.md（2026-06-22）

---

## 一、覆盖记录

| 审查对象 | 方式 | 结果 |
|---------|------|------|
| 后端全部 Python（app/config/auth/extensions + routes 7 文件 + services 7 文件，约 7600 行） | 逐文件精读 | 完成 |
| 测试套件 | 本机实际运行（Python 3.13.12 + 临时 venv） | **95 passed** |
| ruff 静态检查 | 本机实际运行（最新版 ruff） | **139 errors** |
| GitHub Actions | `gh run list` 实查 | **Python CI 最近两次 push 均 failure** |
| 部署配置（Dockerfile / docker-compose / .dockerignore） | 逐行核对 | 完成 |
| Electron 桌面端（main.js / preload.js / package.json + lock） | 逐行核对 + 版本比对 | 完成 |
| Android 端（MainActivity.kt） | 硬编码凭证扫描 | 无硬编码凭证 |
| 前端关键面（templates XSS 注入点 / script.js innerHTML / CSRF token） | grep 定位 + 上下文精读 | 完成 |

**验证手段声明**：本报告所有"已修复/未修复"结论均基于对当前 main 分支代码的直接读取与本机复现，不采信任何历史报告的自述。

---

## 二、旧账核实（2026-06 两份报告）

### Critical 7 项 — 全部确认修复 ✅

| # | 问题 | 验证证据 |
|---|------|---------|
| 1 | SSL 证书验证禁用 | `api.py:42` `_fetch_json` 统一 `ssl.create_default_context()` ✅（天气接口有残留，见新发现 M2） |
| 2 | Jinja2 XSS | `index.html:2471` `{{ username \| tojson }}` ✅ |
| 3/4 | innerHTML XSS | `script.js:613/618` 留言渲染走 `escapeHtml()`；admin.html:159 显示走 `escapeHtml(f)` ✅ |
| 5 | 明文密码时序攻击 | `auth.py:208` `hmac.compare_digest` ✅ |
| 6 | Python CI 缺失 | `.github/workflows/python-ci.yml` 存在 ✅（但当前红灯，见新发现 H1） |
| 7 | SECRET_KEY 默认值 | `config.py:50` 缺失即 raise；docker-compose 用 `:?` 强制语法 ✅ |

### B 级 6 项 — 5 修 1 未修

| # | 问题 | 状态 | 证据 |
|---|------|------|------|
| B1 | admin.html 文件夹 XSS | ✅ 已修 | escapeHtml helper + onclick 引号转义（残余反斜杠边界见 Low L2） |
| B2 | health.py 版本号过期 | ✅ 已改 3.0.1 | 仍为手动维护，存在再次漂移风险 |
| B3 | healthcheck 打错目标 | ✅ 已修 | Dockerfile:56 / docker-compose:35 均指向 `/health/ready` |
| B4 | 空 JSON body 500 | ✅ 已修 | api.py:233/393、photos_v3.py:163 均有检查（**remove_folder 漏了**，见 M1） |
| B5 | 任意路径添加照片源 | ✅ 已修 | photos_v3.py:307-318 pathlib 白名单，防兄弟前缀绕过 |
| B6 | test_route.py 磁盘残留 | ✅ 已删 | 文件不存在 |

### 部分修复 / 未修

| # | 问题 | 状态 |
|---|------|------|
| W3 | v3 photo API 零测试 | ❌ **仍未修复**（tests/ 无 photos_v3 相关文件） |
| W4 | .dockerignore 缺 venv/ | ✅ 已修 |
| W8 | debug 模式 SSL 验证禁用 | ⚠️ 半修复：每日一言已统一，天气接口残留（见 M2） |

---

## 三、五维打分卡

| 维度 | 得分 | 评语 |
|------|------|------|
| 安全 Security | **7.5 / 10** | 旧 Critical 全清；路径边界、PBKDF2、CSRF、登录锁定有界字典均到位。扣分：桌面端监听 0.0.0.0（H2）、debug SSL 残留（M2）、日志目录 777（M3） |
| 正确性 Correctness | **8 / 10** | 95 测试全绿（Python 3.13 实测）；BEGIN IMMEDIATE 事务、深海打捞 TOCTOU 修复、JSON 原子写均属高质量。扣分：remove_folder 空 body 500（M1） |
| 可维护性 Maintainability | **6.5 / 10** | 分层清晰、注释密度好、配置带范围校验。扣分：lint 债务 139 项堆积、新旧双索引服务并存（M4）、版本号三处手动维护 |
| 测试 Testing | **7 / 10** | 推荐引擎 25 例、数据库 15 例，核心逻辑覆盖扎实。扣分：v3 路由层零覆盖（W3 未修）、coverage 配置只盯 app.py 单文件 |
| 部署运维 Ops | **7.5 / 10** | Docker 多阶段 + 非 root + 健康检查正确 + 必需变量强制；Electron 沙箱化加固。扣分：**Python CI 门禁失效两个月（H1）** |

**加权总评：7.3 / 10**

---

## 四、新发现问题

### H1 — Python CI 门禁失效两个月（High，流程性硬伤）

**证据链**：
- `gh run list`：main 分支最近两次 push（2026-06-29、2026-07-30）Python CI 均 `failure`（30 秒即挂 = lint 阶段），同 push 的 Build & Release / Build TV APK 均 success
- 本机复现：`ruff check .` 报 **139 errors**（70 I001 import 排序、37 F401 unused import、21 E712、其余零散）
- CI 脚本 `.github/workflows/python-ci.yml:32` 执行的正是 `ruff check .`

**影响**：lint 门禁形同虚设，任何后续 PR 的坏代码都能静默进 main；对外部贡献者传递"红灯也无所谓"的信号。

**建议**：`ruff check . --fix` 可自动消掉 114 项；剩余 25 项手动清（多为 E712 与 B007）。半小时内可恢复绿灯。

### H2 — 桌面端 Flask 监听 0.0.0.0，局域网可达（Medium-High）

**证据链**：`app.py:225` 硬编码 `app.run(host='0.0.0.0')`；桌面端 `desktop/main.js:271` spawn 时只传 PORT，未限制绑定地址。

**影响**：桌面客户端场景下，同一局域网的任何设备可访问 `http://<本机IP>:15620` 触达完整 API。缓解因素：启动时自动生成 16 hex 字符随机密码（约 64bit 熵），弱口令风险低，但认证面完全不必要地暴露。

**建议**：host 改为环境变量可配（`FLASK_HOST`，默认 127.0.0.1），Docker 场景显式传 0.0.0.0。

### M1 — `remove_folder` 空 body 触发 500

**证据链**：`photos_v3.py:340` `data = request.get_json()` 后直接 `data.get('folder')`；同文件 `add_folder:296-298` 有 `if not data` 检查，此处遗漏。空 JSON body（Content-Type: application/json）会 AttributeError → 500。

**建议**：补 3 行空值检查，与 add_folder 对齐。

### M2 — 天气接口 debug 模式 SSL 验证禁用残留

**证据链**：`api.py:348` `FLASK_DEBUG=true` 时仍走 `ssl._create_unverified_context()`；而同文件 `:42` `_fetch_json` 已统一默认证书链。两处行为不一致。

**建议**：天气接口与 `_fetch_json` 对齐，删除 debug 降级分支（debug 下开发者可自行信任证书）。

### M3 — 日志目录权限 777

**证据链**：`app.py:39` `os.chmod(LOG_DIR, S_IRWXU | S_IRWXG | S_IRWXO)` 即 0777。日志含请求路径、错误堆栈，任意本地用户可读。

**建议**：收紧为 0750 或 0700。

### M4 — 新旧双索引服务并存（架构债，已知取舍）

**证据链**：`app.py:130-146` 启动时依次执行 `PhotoService.rescan()`（v3）与 `PhotoIndexService.build()`（旧）+ 后台重建线程，两套系统对同一 photos 表各做一轮扫描与 upsert。

**缓解因素**：`sync_records` 的 DELETE 带 `source_type` 保护，desktop 记录不会被误删（本审查已验证该保护存在）。但认知成本高，后台线程与 v3 rescan 存在双写窗口。

**建议**：维持现状可接受；v4 规划时应删掉 PhotoIndexService 内存索引，以 DB 为唯一真相源。

### M5 — v3 路由层零测试（旧 W3，仍未修）

tests/ 目录无任何 photos_v3.py 相关用例。v3 API 是最新的攻击面（照片源管理、路径白名单），恰恰最需要测试锁住行为。

### Low（择机修）

| # | 问题 | 位置 |
|---|------|------|
| L1 | 版本号三处手动维护（health.py / desktop package.json / README），已现漂移苗头 | 全局 |
| L2 | admin.html `escapedF` 未先转义反斜杠，极端文件名可破坏 onclick 转义（macOS/Linux 路径分隔符下实际不可达） | admin.html:158 |
| L3 | pyproject `addopts` 硬编码 `--cov=app`，不装 pytest-cov 连 pytest 都跑不了（DX 坑，本次审查实测踩中）；且 --cov 只盯 app.py 单文件 | pyproject.toml |
| L4 | `index.html:11` `forcedStyle` 模板插值未用 tojson（值来自服务端白名单，无风险，但与 username 的处理模式不一致） | index.html |
| L5 | logout 支持 GET，可被诱导链接登出（低危） | main.py:137 |
| L6 | 批量上传遇非法文件返回 400，但已保存的合法文件保留且已入索引，API 语义含糊 | upload.py:48-100 |
| L7 | Electron `restartFlaskWithNewConfig` 的 isQuitting 时序窗口：Flask 若 1.5s 内未退出，exit 事件会被误判为崩溃并消耗重启次数 | main.js:606-622 |

---

## 五、确认无问题（本轮实测）

- SQL 注入：全部参数化查询（含动态 IN 占位符构造），无拼接风险
- 路径穿越：`/api/images/<f> DELETE`、两个 PhotoSource 的 resolve 均有 `abspath + sep 后缀` 边界，兄弟前缀绕过已防
- 深海打捞 TOCTOU：SELECT + UPDATE 在 `BEGIN IMMEDIATE` 内，竞态已封
- 留言板：JSON→SQLite 迁移 + keep_last=200 防膨胀 + 迁移双重检查锁
- 播放历史膨胀：`cleanup_play_history` 在推荐流程中以 1% 概率触发（每 100 次播放期望清理一次），闭环成立（本轮专项核实）
- JSON 元数据原子写（tempfile + os.replace）
- Electron：contextIsolation + sandbox + preload 最小暴露面 + 随机凭证持久化
- Android：无硬编码服务器地址/凭证（grep 零命中）
- Docker：多阶段构建、非 root、healthcheck 指向就绪接口、必需变量 `:?` 强制
- 依赖版本一致性：desktop/package.json 与 package-lock.json 对齐（electron 42.4.0 / builder 26.15.2）

---

## 六、唯一结论

# ✅ Approve（附 3 项优先修复建议）

**理由**：作为 v3.x 现状——功能完整、测试全绿（本机实测 95/95）、上一轮全部 Critical 级安全旧账经本审查逐项实证修复、无新增 Block 级漏洞。项目基本盘是健康的。

**但若近期有发版/推广计划，强烈建议先清以下三项（合计约 1 小时）**：

| 优先级 | 事项 | 工作量 |
|--------|------|--------|
| P0 | 恢复 Python CI 绿灯（ruff --fix 114 项 + 手动 25 项） | ~30 min |
| P0 | photos_v3.py `remove_folder` 补空 body 检查 | ~5 min |
| P1 | 天气接口删除 debug SSL 降级分支，与 `_fetch_json` 统一 | ~5 min |
| P1 | app.py host 改环境变量可配，桌面端默认 127.0.0.1 | ~15 min |

**路线图建议**（不阻塞发版）：补充 photos_v3 路由层测试（M5）→ 日志目录权限收紧（M3）→ v4 时拆除旧 PhotoIndexService（M4）。
