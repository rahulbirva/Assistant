/**
 * Preload: exposes a narrow, safe IPC surface to the renderer.
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
  closeHud:    () => ipcRenderer.send('close-hud'),
  minimizeHud: () => ipcRenderer.send('minimize-hud'),
  toggleHud:   () => ipcRenderer.send('toggle-hud'),
  togglePin:   (pinned) => ipcRenderer.send('toggle-pin', pinned),
});
