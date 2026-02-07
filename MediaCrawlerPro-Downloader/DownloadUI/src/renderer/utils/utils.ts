export const openExternal = async (url: string) => {
    if (window.electronAPI) {
        await window.electronAPI.openExternal(url);
    }
};