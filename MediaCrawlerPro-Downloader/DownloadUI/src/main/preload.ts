const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  openDirectory: () => ipcRenderer.invoke('open-directory-dialog'),
  setWindowSize: (width: number, height: number) => ipcRenderer.invoke('set-window-size', { width, height }),
  disableResize: () => ipcRenderer.invoke('disable-resize'),
  openExternal: (url: string) => ipcRenderer.invoke('open-external', url),
  startDownload: (platform: string, videoId: string, url: string, filename: string, savePath: string, contentId?: string, cookies?: string, audioUrl?: string) =>
    ipcRenderer.invoke('start-download', platform, videoId, url, filename, savePath, contentId, cookies, audioUrl),
  cancelDownload: (videoId: string) =>
    ipcRenderer.invoke('cancel-download', videoId),
  onDownloadUpdate: (callback: (data: any) => void) =>
    ipcRenderer.on('download-update', (_, data) => callback(data)),
  onDownloadMessage: (callback: (data: any) => void) =>
    ipcRenderer.on('download-message', (_, data) => callback(data)),
  clearDownloads: () => ipcRenderer.invoke('clear-downloads')
});