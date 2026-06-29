/**
 * Digital Photo Frame - Electron 桌面客户端主进程
 *
 * 职责：
 * - 启动本地 Flask 服务（Python 子进程）
 * - 管理 BrowserWindow + 加载态
 * - 文件夹选择 / 授权管理
 * - 系统托盘（含可见图标）
 * - 应用生命周期管理
 */
const {
  app, BrowserWindow, dialog, ipcMain, Tray, Menu, shell, nativeImage, session,
} = require('electron');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const { spawn } = require('child_process');
const http = require('http');

// ─── 路径常量 ─────────────────────────────────────────
const USER_DATA_DIR = app.getPath('userData');
const CONFIG_FILE = path.join(USER_DATA_DIR, 'desktop-config.json');
const LOG_FILE = path.join(USER_DATA_DIR, 'flask-server.log');
const DEFAULT_PORT = 15620;
const MAX_FLASK_RESTARTS = 3;

let FLASK_PORT = 0;
let flaskProcess = null;
let mainWindow = null;
let loadingWindow = null;
let tray = null;
let isQuitting = false;
let flaskRestartCount = 0;

// ─── 配置管理 ─────────────────────────────────────────

function loadConfig() {
  try {
    if (fs.existsSync(CONFIG_FILE)) {
      return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf-8'));
    }
  } catch (e) {
    console.error('Failed to load config:', e);
  }
  return { folders: [], flask_port: 0, auth: null, secret_key: null };
}

function saveConfig(config) {
  try {
    fs.mkdirSync(path.dirname(CONFIG_FILE), { recursive: true });
    fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2), 'utf-8');
  } catch (e) {
    console.error('Failed to save config:', e);
  }
}

/** 确保 config 中有稳定的 secret_key 和 auth */
function ensureStableSecrets(config) {
  let changed = false;

  if (!config.secret_key) {
    config.secret_key = crypto.randomBytes(32).toString('hex');
    changed = true;
  }

  if (!config.auth) {
    const randomPass = crypto.randomBytes(8).toString('hex');
    config.auth = `local:${randomPass}`;
    changed = true;
  }

  if (changed) saveConfig(config);
  return config;
}

// ─── Python 环境检测 ──────────────────────────────────

/** 返回 venv 目录下的 Python 可执行文件路径（跨平台） */
function getVenvPython(venvDir) {
  return process.platform === 'win32'
    ? path.join(venvDir, 'Scripts', 'python.exe')
    : path.join(venvDir, 'bin', 'python');
}

function findPython() {
  const candidates = [];

  // 检查项目虚拟环境（优先级最高）
  const projectVenvPython = getVenvPython(path.join(__dirname, '..', 'venv'));
  if (fs.existsSync(projectVenvPython)) candidates.push(projectVenvPython);

  // 打包模式：检查 USER_DATA_DIR 下的 venv（首次启动时自动创建）
  const userDataVenvPython = getVenvPython(path.join(USER_DATA_DIR, 'venv'));
  if (fs.existsSync(userDataVenvPython)) {
    candidates.unshift(userDataVenvPython);  // 最高优先级
  }

  // 系统 Python
  if (process.platform === 'win32') {
    candidates.push('python', 'python3', 'py');
    // Windows 常见路径
    const localApp = process.env.LOCALAPPDATA || '';
    if (localApp) {
      candidates.push(path.join(localApp, 'Programs', 'Python', 'Python311', 'python.exe'));
      candidates.push(path.join(localApp, 'Programs', 'Python', 'Python312', 'python.exe'));
      candidates.push(path.join(localApp, 'Programs', 'Python', 'Python313', 'python.exe'));
    }
  } else {
    candidates.push('python3', 'python', '/usr/bin/python3', '/usr/local/bin/python3');
    if (process.platform === 'darwin') {
      candidates.push('/opt/homebrew/bin/python3');
    }
  }

  const { execSync } = require('child_process');
  for (const cmd of candidates) {
    try {
      const version = execSync(`"${cmd}" --version`, { stdio: 'pipe', timeout: 5000 })
        .toString().trim();
      console.log(`Found Python: ${cmd} (${version})`);
      return cmd;
    } catch (_) {}
  }
  return null;
}

/**
 * 确保 USER_DATA_DIR 下存在可用的 Python venv（打包模式首次启动时调用）。
 *
 * 流程：
 * 1. 如果 venv 已存在且有效，直接跳过
 * 2. 用系统 Python 创建 venv
 * 3. pip install -r requirements.txt
 *
 * @returns {string|null} venv Python 路径，失败返回 null
 */
function ensureUserDataVenv() {
  const { execSync } = require('child_process');
  const venvDir = path.join(USER_DATA_DIR, 'venv');
  const venvPython = getVenvPython(venvDir);

  // 已存在且可用
  if (fs.existsSync(venvPython)) {
    try {
      execSync(`"${venvPython}" -c "import flask"`, { stdio: 'pipe', timeout: 5000 });
      console.log(`[venv] existing venv OK: ${venvPython}`);
      return venvPython;
    } catch (_) {
      console.log('[venv] existing venv broken, recreating...');
      fs.rmSync(venvDir, { recursive: true, force: true });
    }
  }

  // 找系统 Python 用于创建 venv
  const sysPythonCandidates = process.platform === 'win32'
    ? ['python', 'python3', 'py']
    : ['python3', 'python', '/usr/bin/python3', '/usr/local/bin/python3', '/opt/homebrew/bin/python3'];

  let sysPython = null;
  for (const cmd of sysPythonCandidates) {
    try {
      execSync(`"${cmd}" --version`, { stdio: 'pipe', timeout: 5000 });
      sysPython = cmd;
      break;
    } catch (_) {}
  }

  if (!sysPython) {
    console.error('[venv] no system Python found');
    return null;
  }

  // 找 requirements.txt
  const serverDir = getFlaskServerDir();
  const reqFile = path.join(serverDir, 'requirements.txt');
  if (!fs.existsSync(reqFile)) {
    console.error(`[venv] requirements.txt not found at ${reqFile}`);
    return null;
  }

  try {
    console.log(`[venv] creating venv with ${sysPython} at ${venvDir}...`);
    execSync(`"${sysPython}" -m venv "${venvDir}"`, { stdio: 'pipe', timeout: 60000 });

    console.log(`[venv] installing dependencies from ${reqFile}...`);
    execSync(`"${venvPython}" -m pip install --upgrade pip`, { stdio: 'pipe', timeout: 60000 });
    execSync(`"${venvPython}" -m pip install -r "${reqFile}"`, { stdio: 'pipe', timeout: 300000 });

    console.log(`[venv] setup complete: ${venvPython}`);
    return venvPython;
  } catch (err) {
    console.error(`[venv] setup failed: ${err.message}`);
    return null;
  }
}

// ─── Flask 服务管理 ────────────────────────────────────

function getFlaskServerDir() {
  // 开发模式：直接引用项目根目录
  const devDir = path.join(__dirname, '..');
  if (fs.existsSync(path.join(devDir, 'app.py'))) {
    return devDir;
  }

  // 打包模式：从 extraResources 读取
  const resourceDir = path.join(process.resourcesPath || '', 'flask-server');
  if (fs.existsSync(path.join(resourceDir, 'app.py'))) {
    return resourceDir;
  }

  return devDir;
}

function startFlaskServer(port) {
  return new Promise((resolve, reject) => {
    // 打包模式：确保 USER_DATA_DIR 有可用的 venv
    let python = findPython();

    // 如果是系统 Python（非 venv），尝试确保 USER_DATA_DIR venv
    const isVenvPython = python && (
      python.includes('venv') || python.includes('.venv')
    );
    if (!isVenvPython) {
      const venvPython = ensureUserDataVenv();
      if (venvPython) {
        python = venvPython;
      }
    }

    if (!python) {
      reject(new Error(
        '未找到 Python 环境。\n\n' +
        '请通过以下任一方式安装：\n' +
        '1. 访问 python.org 下载 Python 3.11+\n' +
        '2. macOS: brew install python3\n' +
        '3. 在项目根目录创建虚拟环境: python3 -m venv venv && pip install -r requirements.txt'
      ));
      return;
    }

    const serverDir = getFlaskServerDir();
    const config = loadConfig();
    ensureStableSecrets(config);

    const env = {
      ...process.env,
      FLASK_DEBUG: 'false',
      FLASK_RUN_PORT: String(port),
      PORT: String(port),
      SECRET_KEY: config.secret_key,  // 稳定的 SECRET_KEY
      ADMIN_USERS: config.auth,
    };

    // 桌面端文件夹配置
    if (config.folders && config.folders.length > 0) {
      env.DESKTOP_PHOTO_FOLDERS = config.folders.join(',');
    }

    // 数据目录（独立于项目）
    const dataDir = path.join(USER_DATA_DIR, 'data');
    fs.mkdirSync(dataDir, { recursive: true });
    env.DATABASE_FILE = path.join(dataDir, 'photos.db');
    env.METADATA_FILE = path.join(dataDir, 'photo_metadata.json');
    env.MESSAGES_FILE = path.join(dataDir, 'messages.json');
    env.UPLOAD_FOLDER = path.join(dataDir, 'uploads');
    fs.mkdirSync(env.UPLOAD_FOLDER, { recursive: true });

    console.log(`Starting Flask: ${python} app.py (port=${port}, dir=${serverDir})`);

    flaskProcess = spawn(python, ['app.py'], {
      cwd: serverDir,
      env,
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    const logStream = fs.createWriteStream(LOG_FILE, { flags: 'a' });
    flaskProcess.stdout.pipe(logStream);
    flaskProcess.stderr.pipe(logStream);

    flaskProcess.stdout.on('data', (data) => {
      console.log('[Flask]', data.toString().trim());
    });

    flaskProcess.stderr.on('data', (data) => {
      console.error('[Flask]', data.toString().trim());
    });

    flaskProcess.on('error', (err) => {
      reject(new Error(`Flask 启动失败: ${err.message}`));
    });

    // Track whether waitForServer is still pending to prevent double-restart
    let waitPending = true;

    flaskProcess.on('exit', (code) => {
      console.log(`Flask exited with code ${code}`);
      flaskProcess = null;
      if (!isQuitting && waitPending) {
        waitPending = false;
        flaskRestartCount++;
        if (flaskRestartCount <= MAX_FLASK_RESTARTS) {
          console.log(`Flask restart attempt ${flaskRestartCount}/${MAX_FLASK_RESTARTS}...`);
          setTimeout(() => {
            if (!isQuitting) startFlaskServer(port).then(resolve).catch(reject);
          }, 2000 * flaskRestartCount);
        } else {
          dialog.showErrorBox(
            'Flask 服务异常',
            `Flask 服务连续崩溃 ${MAX_FLASK_RESTARTS} 次，已停止重启。\n\n` +
            `请检查日志: ${LOG_FILE}`
          );
        }
      }
    });

    // 等待 Flask 启动
    waitForServer(port, 20000)
      .then(() => {
        waitPending = false;
        flaskRestartCount = 0;
        resolve(port);
      })
      .catch((err) => {
        waitPending = false;
        reject(err);
      });
  });
}

function waitForServer(port, timeout) {
  return new Promise((resolve, reject) => {
    const start = Date.now();

    function check() {
      if (Date.now() - start > timeout) {
        reject(new Error('Flask 服务启动超时（20秒）'));
        return;
      }

      const req = http.get(`http://127.0.0.1:${port}/health/live`, (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else {
          setTimeout(check, 500);
        }
      });

      req.on('error', () => setTimeout(check, 500));
      req.setTimeout(1000, () => { req.destroy(); setTimeout(check, 500); });
    }

    check();
  });
}

function stopFlaskServer() {
  if (flaskProcess) {
    isQuitting = true;
    flaskProcess.kill('SIGTERM');
    setTimeout(() => {
      if (flaskProcess) {
        flaskProcess.kill('SIGKILL');
        flaskProcess = null;
      }
    }, 3000);
  }
}

// ─── 加载窗口 ──────────────────────────────────────────

function showLoadingWindow() {
  loadingWindow = new BrowserWindow({
    width: 400,
    height: 280,
    frame: false,
    transparent: true,
    resizable: false,
    alwaysOnTop: true,
    webPreferences: { nodeIntegration: false },
  });

  const loadingHTML = `data:text/html;charset=utf-8,${encodeURIComponent(`
    <!DOCTYPE html>
    <html>
    <head><style>
      * { margin: 0; padding: 0; }
      body {
        background: rgba(20, 20, 20, 0.95);
        color: #e0e0e0;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        height: 100vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        border-radius: 16px;
        -webkit-app-region: drag;
      }
      .logo { font-size: 48px; margin-bottom: 20px; }
      h2 { font-size: 18px; font-weight: 500; margin-bottom: 8px; color: #fff; }
      p { font-size: 13px; color: #888; margin-bottom: 24px; }
      .spinner {
        width: 24px; height: 24px;
        border: 3px solid rgba(255,255,255,0.15);
        border-top-color: #4a90d9;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
      }
      @keyframes spin { to { transform: rotate(360deg); } }
    </style></head>
    <body>
      <div class="logo">🖼️</div>
      <h2>电子相框</h2>
      <p>正在启动本地服务...</p>
      <div class="spinner"></div>
    </body>
    </html>
  `)}`;

  loadingWindow.loadURL(loadingHTML);
  loadingWindow.center();
  loadingWindow.show();
}

function closeLoadingWindow() {
  if (loadingWindow) {
    loadingWindow.close();
    loadingWindow = null;
  }
}

// ─── 托盘图标 ──────────────────────────────────────────

function createTrayIcon() {
  // 内嵌 16x16 PNG（相框图标）
  const iconBase64 = 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAA' +
    'mUlEQVQ4T2NkoBAwUqifYdAb8P9/LgMDQwEDA8N8mKFYGvMZEfIw' +
    'BfgMYKBG5GMYQpEGpCH/MQz5z8DAsICJiWkhVEE+MQZgGvIfyJHf' +
    'gOx8BgYGJgaGBXgNwWcAI8gGIPsfIwOD8H8GBuH/DAwCxAQTPgPy' +
    'gQbMB3L5GZiYFuAzBCsXJAAAOIuK8djfLKsAAAAASUVORK5CYII=';

  try {
    return nativeImage.createFromBuffer(Buffer.from(iconBase64, 'base64'));
  } catch (_) {
    // 如果 base64 解码失败，创建一个纯色图标
    const size = 16;
    const img = nativeImage.createEmpty();
    return img;
  }
}

// ─── 窗口管理 ──────────────────────────────────────────

function setupAuthInterceptor(config) {
  if (config.auth) {
    const authBase64 = Buffer.from(config.auth).toString('base64');
    session.defaultSession.webRequest.onBeforeSendHeaders(
      { urls: [`http://127.0.0.1:${FLASK_PORT}/**`] },
      (details, callback) => {
        details.requestHeaders['Authorization'] = `Basic ${authBase64}`;
        callback({ requestHeaders: details.requestHeaders });
      }
    );
  }
}

function createMainWindow() {
  const config = loadConfig();
  setupAuthInterceptor(config);

  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: '电子相框',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      // 安全加固：渲染进程沙箱化。preload 仅使用 contextBridge + ipcRenderer，
      // 二者在 sandbox 模式下仍可用，故不影响现有 IPC 能力。
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
    },
    show: false,
  });

  const hasFolders = config.folders && config.folders.length > 0;

  if (hasFolders) {
    mainWindow.loadURL(`http://127.0.0.1:${FLASK_PORT}`);
  } else {
    const onboardingPath = path.join(__dirname, 'renderer', 'onboarding.html');
    mainWindow.loadFile(onboardingPath);
  }

  mainWindow.once('ready-to-show', () => {
    closeLoadingWindow();
    mainWindow.show();
  });

  mainWindow.on('close', (e) => {
    if (!isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  return mainWindow;
}

// ─── 系统托盘 ──────────────────────────────────────────

function createTray() {
  const icon = createTrayIcon();
  tray = new Tray(icon);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示窗口',
      click: () => {
        if (mainWindow) { mainWindow.show(); mainWindow.focus(); }
      },
    },
    { type: 'separator' },
    {
      label: '添加相册文件夹',
      click: () => selectFolders(),
    },
    {
      label: '重新扫描照片',
      click: () => rescanPhotos(),
    },
    { type: 'separator' },
    {
      label: '管理后台',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.loadURL(`http://127.0.0.1:${FLASK_PORT}/admin`);
        }
      },
    },
    {
      label: '照片整理',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.loadURL(`http://127.0.0.1:${FLASK_PORT}/admin/manage`);
        }
      },
    },
    { type: 'separator' },
    {
      label: '打开数据目录',
      click: () => shell.openPath(USER_DATA_DIR),
    },
    {
      label: '查看日志',
      click: () => shell.openPath(LOG_FILE),
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => { isQuitting = true; app.quit(); },
    },
  ]);

  tray.setToolTip('电子相框 - 本地客户端');
  tray.setContextMenu(contextMenu);

  tray.on('click', () => {
    if (mainWindow) { mainWindow.show(); mainWindow.focus(); }
  });
}

// ─── IPC 处理 ──────────────────────────────────────────

async function selectFolders() {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: '选择本地相册文件夹',
    properties: ['openDirectory', 'multiSelections'],
  });

  if (result.canceled || result.filePaths.length === 0) return;

  const config = loadConfig();
  config.folders = [...new Set([...(config.folders || []), ...result.filePaths])];
  saveConfig(config);

  // 重启 Flask 以应用新文件夹（因为 DESKTOP_PHOTO_FOLDERS 是启动时传入的）
  await restartFlaskWithNewConfig();

  if (mainWindow) {
    mainWindow.loadURL(`http://127.0.0.1:${FLASK_PORT}`);
  }
}

async function restartFlaskWithNewConfig() {
  // 停止当前 Flask
  if (flaskProcess) {
    isQuitting = true;  // 防止自动重启
    flaskProcess.kill('SIGTERM');
    await new Promise(r => setTimeout(r, 1500));
    isQuitting = false;
  }

  // 重新启动
  try {
    await startFlaskServer(FLASK_PORT);
    await rescanPhotos();
  } catch (e) {
    console.error('Restart failed:', e);
  }
}

async function rescanPhotos() {
  const config = loadConfig();
  if (!config.auth) return null;

  const auth = Buffer.from(config.auth).toString('base64');

  return new Promise((resolve) => {
    const req = http.request(
      {
        hostname: '127.0.0.1',
        port: FLASK_PORT,
        path: '/api/photo-sources/rescan',
        method: 'POST',
        headers: {
          Authorization: `Basic ${auth}`,
          'Content-Type': 'application/json',
        },
      },
      (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          console.log('Rescan result:', data);
          resolve(data);
        });
      }
    );
    req.on('error', (e) => { console.error('Rescan failed:', e); resolve(null); });
    req.end();
  });
}

ipcMain.handle('select-folders', async () => {
  await selectFolders();
  return loadConfig().folders || [];
});

ipcMain.handle('get-config', () => loadConfig());
ipcMain.handle('get-port', () => FLASK_PORT);
ipcMain.handle('rescan', async () => await rescanPhotos());

ipcMain.handle('remove-folder', async (event, folderPath) => {
  const config = loadConfig();
  config.folders = (config.folders || []).filter((f) => f !== folderPath);
  saveConfig(config);

  // 同步 Flask 后端：移除文件夹 + 重新扫描
  if (config.auth && FLASK_PORT) {
    const auth = Buffer.from(config.auth).toString('base64');
    try {
      await new Promise((resolve) => {
        const req = http.request(
          {
            hostname: '127.0.0.1',
            port: FLASK_PORT,
            path: '/api/photo-sources/folders',
            method: 'DELETE',
            headers: {
              Authorization: `Basic ${auth}`,
              'Content-Type': 'application/json',
            },
          },
          (res) => {
            let data = '';
            res.on('data', (chunk) => (data += chunk));
            res.on('end', () => resolve(data));
          }
        );
        req.on('error', (e) => { console.error('Flask remove-folder failed:', e); resolve(); });
        req.write(JSON.stringify({ folder: folderPath }));
        req.end();
      });
      // 重新扫描以更新索引
      await rescanPhotos();
    } catch (e) {
      console.error('Sync Flask after remove-folder failed:', e);
    }
  }

  return config.folders;
});

// ─── 应用生命周期 ──────────────────────────────────────

app.whenReady().then(async () => {
  console.log('App ready. User data:', USER_DATA_DIR);

  // 加载配置并确保密钥稳定
  const config = loadConfig();
  ensureStableSecrets(config);

  // 端口策略：优先用配置端口，失败则随机
  FLASK_PORT = config.flask_port || DEFAULT_PORT;

  // 显示加载窗口
  showLoadingWindow();

  try {
    await startFlaskServer(FLASK_PORT);
    console.log(`Flask server started on port ${FLASK_PORT}`);
  } catch (e) {
    // 默认端口失败，回退到随机端口
    if (FLASK_PORT === DEFAULT_PORT) {
      console.log(`Port ${DEFAULT_PORT} failed, trying random port...`);
      FLASK_PORT = 0;
      try {
        // 需要重新检测可用端口
        const port = await findAvailablePort();
        FLASK_PORT = port;
        await startFlaskServer(port);
        console.log(`Flask started on fallback port ${port}`);
      } catch (e2) {
        closeLoadingWindow();
        dialog.showErrorBox('启动失败', e2.message);
        app.quit();
        return;
      }
    } else {
      closeLoadingWindow();
      dialog.showErrorBox('启动失败', e.message);
      app.quit();
      return;
    }
  }

  createMainWindow();
  createTray();
});

/** 查找可用端口 */
function findAvailablePort() {
  return new Promise((resolve, reject) => {
    const server = http.createServer();
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
    server.on('error', reject);
  });
}

app.on('before-quit', () => {
  isQuitting = true;
  stopFlaskServer();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (mainWindow) {
    mainWindow.show();
  } else {
    createMainWindow();
  }
});
