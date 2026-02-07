import { BrowserWindow, WebContents } from 'electron';
import { EventEmitter } from 'events';
import * as path from 'path';
import * as fs from 'fs';
import axios, { CancelToken } from 'axios';
import { spawn } from 'child_process';

interface DownloadTask {
    id: string;
    platform: string;
    url: string;
    filename: string;
    savePath: string;
    progress: number;
    status: 'pending' | 'downloading' | 'paused' | 'completed' | 'cancelled' | 'error';
    totalBytes: number;
    receivedBytes: number;
    error?: string;
    contentId?: string;
    retryCount?: number;
    maxRetries?: number;
    cancelToken?: CancelToken;
    cookies?: string;
    audioUrl?: string; // B站DASH格式需要单独的音频URL
}

const refererUrlMap = {
    'xhs': 'https://www.xiaohongshu.com/',
    'dy': 'https://www.douyin.com/',
    'bili': 'https://www.bilibili.com',
    'ks': 'https://www.kuaishou.com/'
}

const HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Referer': 'https://www.xiaohongshu.com/',
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'Sec-Fetch-Dest': 'image',
    'Sec-Fetch-Mode': 'no-cors',
    'Sec-Fetch-Site': 'cross-site'
};

export class DownloadManager extends EventEmitter {
    private downloads: Map<string, DownloadTask> = new Map();
    private webContents: WebContents;
    private readonly DEFAULT_MAX_RETRIES = 3;
    private readonly DEFAULT_TIMEOUT = 30000; // 30 seconds
    private readonly MAX_CONCURRENT_DOWNLOADS = 3; // 最大并发下载数
    private downloadQueue: string[] = [];
    private activeDownloads: Set<string> = new Set();
    private isProcessingQueue = false;

    constructor(window: BrowserWindow) {
        super();
        this.webContents = window.webContents;
    }

    private emitUpdate(task: DownloadTask) {
        this.webContents.send('download-update', {
            id: task.id,
            filename: task.filename,
            progress: task.progress,
            status: task.status,
            error: task.error,
            totalBytes: task.totalBytes,
            receivedBytes: task.receivedBytes
        });
    }

    async addDownload(platform: string, id: string, url: string, filename: string, savePath: string, contentId?: string, cookies?: string, audioUrl?: string) {
        console.log(savePath, filename, contentId);
        
        // 如果提供了contentId，则在保存路径中创建以contentId命名的子目录
        let finalSavePath = savePath;
        if (contentId) {
            // 清理contentId，移除可能导致文件夹创建失败的字符
            const cleanContentId = contentId.replace(/[\\/:*?"<>|]/g, '_').slice(0, 50);
            finalSavePath = path.join(savePath, cleanContentId);
        }
        
        const task: DownloadTask = {
            id,
            url,
            filename,
            platform,
            savePath: path.join(finalSavePath, filename),
            progress: 0,
            status: 'pending',
            totalBytes: 0,
            receivedBytes: 0,
            contentId,
            retryCount: 0,
            maxRetries: this.DEFAULT_MAX_RETRIES,
            cancelToken: axios.CancelToken.source().token,
            cookies,
            audioUrl
        };
        this.downloads.set(id, task);
        
        // 添加到下载队列
        this.downloadQueue.push(id);
        this.emitUpdate(task);
        
        // 开始处理队列
        this.processDownloadQueue();
        
        return true;
    }

    private async processDownloadQueue(): Promise<void> {
        if (this.isProcessingQueue) {
            return;
        }
        
        this.isProcessingQueue = true;
        
        while (this.downloadQueue.length > 0 && this.activeDownloads.size < this.MAX_CONCURRENT_DOWNLOADS) {
            const taskId = this.downloadQueue.shift();
            if (!taskId) continue;
            
            const task = this.downloads.get(taskId);
            if (!task || task.status === 'cancelled') {
                continue;
            }
            
            this.activeDownloads.add(taskId);
            
            // 异步执行下载，不等待完成
            this.performDownload(task).finally(() => {
                this.activeDownloads.delete(taskId);
                // 继续处理队列
                setTimeout(() => this.processDownloadQueue(), 100);
            });
        }
        
        this.isProcessingQueue = false;
    }

    private async performDownload(task: DownloadTask): Promise<boolean> {
        try {
            // B站DASH格式需要特殊处理
            if (task.platform === 'bili' && task.audioUrl) {
                return await this.performBilibiliDashDownload(task);
            }
            
            // 确保目录存在            
            const dir = path.dirname(task.savePath);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }

            // 根据文件扩展名判断是图片还是视频
            const isImage = /\.(jpg|jpeg|png|gif|webp)$/i.test(task.filename);
            let headers = {
                ...HEADERS,
                'Sec-Fetch-Dest': isImage ? 'image' : 'video',
                'Referer': refererUrlMap[task.platform] || refererUrlMap['xhs']
            };

            // B站特殊处理
            if (task.platform === 'bili') {
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
                    'Referer': 'https://www.bilibili.com',
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Sec-Fetch-Dest': isImage ? 'image' : 'video',
                    'Sec-Fetch-Mode': 'no-cors',
                    'Sec-Fetch-Site': 'cross-site'
                };
                
                // 添加Cookie（如果有）
                if (task.cookies) {
                    headers['Cookie'] = task.cookies;
                }
            }

            // 获取文件大小
            const headResponse = await axios.head(task.url, { 
                headers,
                timeout: this.DEFAULT_TIMEOUT,
                cancelToken: task.cancelToken
            });
            const contentLength = parseInt(headResponse.headers['content-length'] || '0');
            task.totalBytes = contentLength;

            console.log(`[Download] File size: ${contentLength} bytes`);

            // 创建写入流
            const writer = fs.createWriteStream(task.savePath);

            // 开始下载
            task.status = 'downloading';
            this.emitUpdate(task);

            const response = await axios({
                url: task.url,
                method: 'GET',
                responseType: 'stream',
                headers,
                timeout: this.DEFAULT_TIMEOUT,
                cancelToken: task.cancelToken
            });

            // 写入文件
            response.data.pipe(writer);

            // 添加数据块监听来跟踪下载进度
            response.data.on('data', (chunk: Buffer) => {
                if (task.status === 'cancelled') {
                    return;
                }
                task.receivedBytes += chunk.length;
                task.progress = task.totalBytes > 0 ? (task.receivedBytes / task.totalBytes) * 100 : 0;
                this.emitUpdate(task);
            });

            return new Promise(async (resolve, reject) => {
                writer.on('finish', () => {
                    if (task.status === 'cancelled') {
                        resolve(false);
                        return;
                    }
                    task.status = 'completed';
                    task.progress = 100;
                    this.emitUpdate(task);
                    console.log(`[Download] Completed: ${task.filename}`);
                    resolve(true);
                });

                writer.on('error', async (error: Error) => {
                    console.error(`[Download] Writer Error: ${error.message}`);
                    await this.handleDownloadError(task, error, resolve, reject);
                });

                response.data.on('error', async (error: Error) => {
                    console.error(`[Download] Stream Error: ${error.message}`);
                    writer.end();
                    await this.handleDownloadError(task, error, resolve, reject);
                });
            });

        } catch (error: any) {
            console.error(`[Download] Error: ${error.message}`);
            return new Promise(async (resolve, reject) => {
                await this.handleDownloadError(task, error, resolve, reject);
            });
        }
    }

    private async handleDownloadError(task: DownloadTask, error: any, resolve?: Function, reject?: Function): Promise<boolean> {
        task.retryCount = (task.retryCount || 0) + 1;
        
        // 如果是取消操作，不进行重试
        if (task.status === 'cancelled') {
            if (resolve) resolve(false);
            return false;
        }

        // 如果还有重试次数，则重试
        if (task.retryCount <= (task.maxRetries || this.DEFAULT_MAX_RETRIES)) {
            console.log(`[Download] Retrying (${task.retryCount}/${task.maxRetries}): ${task.filename}`);
            
            // 重置任务状态
            task.status = 'pending';
            task.progress = 0;
            task.receivedBytes = 0;
            task.cancelToken = axios.CancelToken.source().token;
            
            this.emitUpdate(task);
            
            // 延迟重试
            await new Promise(resolve => setTimeout(resolve, 1000 * (task.retryCount || 1)));
            
            // 检查是否在重试期间被取消
            const currentTask = this.downloads.get(task.id);
            if (!currentTask || currentTask.status === 'cancelled') {
                if (resolve) resolve(false);
                return false;
            }
            
            try {
                const result = await this.performDownload(task);
                if (resolve) resolve(result);
                return result;
            } catch (retryError) {
                return this.handleDownloadError(task, retryError, resolve, reject);
            }
        } else {
            // 重试次数已用完
            task.status = 'error';
            task.error = `下载失败 (重试 ${(task.retryCount || 1) - 1} 次): ${error.message}`;
            task.progress = 0; // 重置进度
            this.emitUpdate(task);
            console.log(`[Download] Final failure after ${task.retryCount - 1} retries: ${task.filename}`);
            
            if (reject) {
                reject(error);
            } else if (resolve) {
                resolve(false);
            }
            return false;
        }
    }

    cancelDownload(id: string) {
        const task = this.downloads.get(id);
        if (task) {
            // 中止下载
            task.status = 'cancelled';
            this.emitUpdate(task);
            
            // 从队列中移除
            const queueIndex = this.downloadQueue.indexOf(id);
            if (queueIndex > -1) {
                this.downloadQueue.splice(queueIndex, 1);
            }
            
            // 从活动下载中移除
            this.activeDownloads.delete(id);

            // 删除已下载的部分文件
            if (fs.existsSync(task.savePath)) {
                try {
                    fs.unlinkSync(task.savePath);
                    console.log(`[Download] Cancelled and deleted: ${task.filename}`);
                } catch (error) {
                    console.error(`[Download] Error deleting file: ${error}`);
                }
            }
        }
    }

    getDownload(id: string) {
        return this.downloads.get(id);
    }

    getAllDownloads() {
        return Array.from(this.downloads.values());
    }

    clearDownloads() {
        // 取消所有正在进行的下载
        for (const [id, task] of Array.from(this.downloads.entries())) {
            if (task.status === 'downloading' || task.status === 'pending') {
                this.cancelDownload(id);
            }
        }
        // 清空队列和活动下载
        this.downloadQueue.length = 0;
        this.activeDownloads.clear();
        // 清空下载列表
        this.downloads.clear();
        console.log('[Download] All downloads cleared');
    }

    private async performBilibiliDashDownload(task: DownloadTask): Promise<boolean> {
        try {
            // 确保目录存在
            const dir = path.dirname(task.savePath);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }

            // B站专用headers
            const headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
                'Referer': 'https://www.bilibili.com',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Connection': 'keep-alive',
                'Cookie': task.cookies || ''
            };

            // 临时文件路径
            const videoTempPath = task.savePath.replace('.mp4', '_video.m4s');
            const audioTempPath = task.savePath.replace('.mp4', '_audio.m4s');

            task.status = 'downloading';
            this.emitUpdate(task);

            // 下载视频流
            console.log('[Download] Downloading video stream...');
            const videoResult = await this.downloadStream(task.url, videoTempPath, headers, task, 0.7); // 视频占70%进度
            const currentTaskAfterVideo = this.downloads.get(task.id);
            if (!videoResult && (!currentTaskAfterVideo || currentTaskAfterVideo.status !== 'cancelled')) {
                throw new Error('Video stream download failed');
            }

            // 检查任务是否被取消
            const currentTask = this.downloads.get(task.id);
            if (!currentTask || currentTask.status === 'cancelled') {
                return false;
            }

            // 下载音频流
            console.log('[Download] Downloading audio stream...');
            const audioResult = await this.downloadStream(task.audioUrl!, audioTempPath, headers, task, 0.3, 70); // 音频占30%进度，从70%开始
            const currentTaskAfterAudio = this.downloads.get(task.id);
            if (!audioResult && (!currentTaskAfterAudio || currentTaskAfterAudio.status !== 'cancelled')) {
                throw new Error('Audio stream download failed');
            }

            // 再次检查任务是否被取消
            const finalTask = this.downloads.get(task.id);
            if (!finalTask || finalTask.status === 'cancelled') {
                return false;
            }

            // 使用FFmpeg合成
            console.log('[Download] Merging video and audio streams...');
            task.progress = 90;
            this.emitUpdate(task);

            const mergeResult = await this.mergeVideoAudio(videoTempPath, audioTempPath, task.savePath);
            if (!mergeResult) {
                throw new Error('Video and audio merge failed');
            }

            // 清理临时文件
            if (fs.existsSync(videoTempPath)) fs.unlinkSync(videoTempPath);
            if (fs.existsSync(audioTempPath)) fs.unlinkSync(audioTempPath);

            task.status = 'completed';
            task.progress = 100;
            this.emitUpdate(task);
            console.log(`[Download] B站DASH格式下载完成: ${task.filename}`);

            return true;

        } catch (error: any) {
            console.error(`[Download] B站DASH下载失败: ${error.message}`);
            // 清理临时文件
            const videoTempPath = task.savePath.replace('.mp4', '_video.m4s');
            const audioTempPath = task.savePath.replace('.mp4', '_audio.m4s');
            if (fs.existsSync(videoTempPath)) fs.unlinkSync(videoTempPath);
            if (fs.existsSync(audioTempPath)) fs.unlinkSync(audioTempPath);
            
            return new Promise(async (resolve, reject) => {
                await this.handleDownloadError(task, error, resolve, reject);
            });
        }
    }

    private async downloadStream(url: string, savePath: string, headers: any, task: DownloadTask, progressWeight: number, progressOffset: number = 0): Promise<boolean> {
        return new Promise(async (resolve, reject) => {
            try {
                const response = await axios({
                    url,
                    method: 'GET',
                    responseType: 'stream',
                    headers,
                    timeout: this.DEFAULT_TIMEOUT,
                    cancelToken: task.cancelToken
                });

                const writer = fs.createWriteStream(savePath);
                response.data.pipe(writer);

                let receivedBytes = 0;
                const contentLength = parseInt(response.headers['content-length'] || '0');

                response.data.on('data', (chunk: Buffer) => {
                    if (task.status === 'cancelled') {
                        writer.end();
                        resolve(false);
                        return;
                    }
                    receivedBytes += chunk.length;
                    const streamProgress = contentLength > 0 ? (receivedBytes / contentLength) * progressWeight * 100 : 0;
                    task.progress = progressOffset + streamProgress;
                    this.emitUpdate(task);
                });

                writer.on('finish', () => {
                    if (task.status === 'cancelled') {
                        resolve(false);
                        return;
                    }
                    resolve(true);
                });

                writer.on('error', (error: Error) => {
                    console.error(`[Download] Stream writer error: ${error.message}`);
                    reject(error);
                });

                response.data.on('error', (error: Error) => {
                    console.error(`[Download] Stream error: ${error.message}`);
                    writer.end();
                    reject(error);
                });

            } catch (error) {
                console.error(`[Download] Stream request error: ${error}`);
                reject(error);
            }
        });
    }

    private async mergeVideoAudio(videoPath: string, audioPath: string, outputPath: string): Promise<boolean> {
        return new Promise((resolve) => {
            const ffmpeg = spawn('ffmpeg', [
                '-i', videoPath,
                '-i', audioPath,
                '-c', 'copy',
                '-y', // 覆盖输出文件
                outputPath
            ]);

            ffmpeg.on('close', (code) => {
                if (code === 0) {
                    console.log('[Download] FFmpeg merge completed successfully');
                    resolve(true);
                } else {
                    console.error(`[Download] FFmpeg merge failed with code: ${code}`);
                    resolve(false);
                }
            });

            ffmpeg.on('error', (error) => {
                console.error(`[Download] FFmpeg error: ${error.message}`);
                resolve(false);
            });
        });
    }
} 