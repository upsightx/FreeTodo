import type { OpenDialogReturnValue } from 'electron';

interface ElectronApi {
    openDirectory: () => Promise<OpenDialogReturnValue>;
    setWindowSize: (width: number, height: number) => Promise<void>;
    disableResize: () => Promise<void>;
    openExternal: (url: string) => Promise<void>;
    startDownload: (platform: string, videoId: string, url: string, filename: string, savePath: string, contentId?: string, cookies?: string, audioUrl?: string) => Promise<boolean>;
    pauseDownload: (videoId: string) => Promise<void>;
    resumeDownload: (videoId: string) => Promise<void>;
    cancelDownload: (videoId: string) => Promise<void>;
    onDownloadUpdate: (callback: (data: DownloadUpdateData) => void) => void;
    onDownloadMessage: (callback: (data: { type: string; message: string }) => void) => void;
    clearDownloads: () => Promise<void>;
}

interface DownloadUpdateData {
    id: string;
    filename: string;
    progress: number;
    status: string;
    error?: string;
    totalBytes: number;
    receivedBytes: number;
}

declare global {
    interface Window {
        electronAPI: ElectronApi;
    }
}

export { }; 