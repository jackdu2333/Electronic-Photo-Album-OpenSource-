/**
 * Electron preload 脚本
 *
 * 通过 contextBridge 安全地暴露桌面端 API 给 Web Core。
 * Web Core 通过 window.desktopAPI 调用原生能力。
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('desktopAPI', {
  // 选择本地相册文件夹
  selectFolders: () => ipcRenderer.invoke('select-folders'),

  // 获取当前配置（含授权文件夹列表）
  getConfig: () => ipcRenderer.invoke('get-config'),

  // 获取 Flask 服务端口
  getPort: () => ipcRenderer.invoke('get-port'),

  // 重新扫描照片源
  rescan: () => ipcRenderer.invoke('rescan'),

  // 移除文件夹
  removeFolder: (folderPath) => ipcRenderer.invoke('remove-folder', folderPath),

  // 检测是否在桌面客户端中运行
  isDesktop: true,

  // 平台信息
  platform: process.platform,
});
