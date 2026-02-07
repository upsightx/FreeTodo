import { app, BrowserWindow, ipcMain, session, dialog, shell } from 'electron';
import { join } from 'path';
import { DownloadManager } from './download-manager';

let downloadManager: DownloadManager;

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 900,
    // 开启开发者工具

    // resizable: false, // 禁止调整大小
    webPreferences: {
      preload: join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      // webSecurity: false, // 不需要了，使用请求拦截器处理B站图片
    }
  });

  mainWindow.webContents.openDevTools();

  downloadManager = new DownloadManager(mainWindow);

  // 为B站图片设置Referer头
  session.defaultSession.webRequest.onBeforeSendHeaders((details, callback) => {
    if (details.url.includes('hdslb.com') || details.url.includes('bilibili.com')) {
      details.requestHeaders['Referer'] = 'https://www.bilibili.com/';
      details.requestHeaders['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36';
    }
    callback({ requestHeaders: details.requestHeaders });
  });

  // 配置默认下载行为
  session.defaultSession.on('will-download', (event, item, webContents) => {
    // 阻止默认的保存对话框
    event.preventDefault();

    const taskId = item.getURLChain()[0];
    const task = downloadManager.getDownload(taskId);

    if (!task) {
      item.cancel();
      return;
    }

    // 设置保存路径
    item.setSavePath(task.savePath);
    console.log(`开始下载文件到: ${task.savePath}`);

    // 监听下载进度
    item.on('updated', (event, state) => {
      if (state === 'interrupted') {
        console.error(`下载中断: ${task.filename}`);
        mainWindow.webContents.send('download-message', {
          type: 'error',
          message: `下载中断: ${task.filename}`
        });
      } else if (state === 'progressing') {
        if (item.isPaused()) {
          console.log(`下载暂停: ${task.filename}`);
        } else {
          const percent = item.getReceivedBytes() / item.getTotalBytes() * 100;
          console.log(`下载进度 ${task.filename}: ${percent.toFixed(2)}%`);
          mainWindow.webContents.send('download-progress', {
            id: taskId,
            progress: percent,
            filename: task.filename
          });
        }
      }
    });

    // 监听下载完成
    item.once('done', (event, state) => {
      if (state === 'completed') {
        console.log(`下载完成: ${task.filename}`);
        mainWindow.webContents.send('download-message', {
          type: 'success',
          message: `下载完成: ${task.filename}`
        });
      } else {
        console.error(`下载失败: ${task.filename}`);
        mainWindow.webContents.send('download-message', {
          type: 'error',
          message: `下载失败: ${task.filename}`
        });
      }
    });
  });

  if (process.env.NODE_ENV === 'development') {
    const rendererPort = process.argv[2];
    mainWindow.loadURL(`http://localhost:${rendererPort}`);
    // mainWindow.webContents.openDevTools(); // 开启F12调试
  }
  else {
    mainWindow.loadFile(join(app.getAppPath(), 'renderer', 'index.html'));
  }

  // 显示警告信息对话框
  mainWindow.webContents.on('did-finish-load', () => {
    dialog.showMessageBox(mainWindow, {
      type: 'warning',
      title: '免责声明',
      message: '本项目所涉及的爬虫技术仅用于学习和研究，不得用于对其他平台进行大规模爬虫或其他非法行为。\n\n本项目的所有内容仅供学习和参考之用，禁止用于商业用途。任何人或组织不得将本项目的内容用于非法用途或侵犯他人合法权益。\n\n对于因使用本项目内容而引起的任何法律责任，本项目不承担任何责任。使用本项目的内容即表示您同意本免责声明的所有条款和条件。',
      buttons: ['我已知晓'],
      defaultId: 0,
    });
  });

  // 处理下载相关的 IPC 调用
  ipcMain.handle('start-download', async (_, platform, videoId, url, filename, savePath, contentId, cookies, audioUrl) => {
    return downloadManager.addDownload(platform, videoId, url, filename, savePath, contentId, cookies, audioUrl);
  });

  ipcMain.handle('cancel-download', (_, videoId) => {
    downloadManager.cancelDownload(videoId);
  });

  ipcMain.handle('clear-downloads', () => {
    downloadManager.clearDownloads();
  });
}

app.whenReady().then(() => {
  createWindow();
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': ['script-src \'self\'']
      }
    })
  })

  app.on('activate', function () {
    // On macOS it's common to re-create a window in the app when the
    // dock icon is clicked and there are no other windows open.
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit()
});

ipcMain.handle('open-directory-dialog', async () => {
  console.log('Handling open-directory-dialog');
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory']
  });
  console.log('Directory dialog result:', result);
  return result;
});

ipcMain.handle('set-window-size', (event, { width, height }) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  if (!win) return;
  win.setSize(width, height);
});

ipcMain.handle('disable-resize', (event) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  if (!win) return;
  win.setResizable(false);
});

// 处理在系统默认浏览器中打开 URL 的请求
ipcMain.handle('open-external', async (event, url) => {
  await shell.openExternal(url);
});