/**
 * JARVIS HUD — Electron Main Process (Phase 6)
 * Frameless, always-on-top overlay. Positioned bottom-right.
 * Communicates state from Python backend via WebSocket on port 7789.
 */

const { app, BrowserWindow, ipcMain, screen, Tray, Menu, nativeImage } = require('electron');
const path = require('path');

let win = null;
let tray = null;
let isVisible = true;

function createWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  win = new BrowserWindow({
    width: 360,
    height: 490,
    x: width - 378,
    y: height - 508,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    movable: true,
    skipTaskbar: true,
    hasShadow: false,
    roundedCorners: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      backgroundThrottling: false,
    },
  });

  win.loadFile(path.join(__dirname, 'index.html'));
  win.setAlwaysOnTop(true, 'screen-saver');
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: false });

  // Development: open devtools
  if (process.argv.includes('--dev')) {
    win.webContents.openDevTools({ mode: 'detach' });
  }
}

function createTray() {
  // 16x16 colored square as tray icon (minimal)
  const img = nativeImage.createFromDataURL(
    'data:image/png;base64,' +
    'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAKklEQVQ4jWNg' +
    'YGD4TwczUMkAoxoYGBgYqGQAIxoYGBgYqGQAIxqoAgAHwAABHwABHwABHwABHw==',
  );
  tray = new Tray(img);
  tray.setToolTip('JARVIS HUD');
  const menu = Menu.buildFromTemplate([
    { label: 'Show HUD',   click: () => { win?.show(); isVisible = true; } },
    { label: 'Hide HUD',   click: () => { win?.hide(); isVisible = false; } },
    { type: 'separator' },
    { label: 'Quit HUD',   click: () => app.quit() },
  ]);
  tray.setContextMenu(menu);
  tray.on('click', () => {
    if (isVisible) { win?.hide(); isVisible = false; }
    else           { win?.show(); isVisible = true;  }
  });
}

// IPC from renderer
ipcMain.on('close-hud',    () => { win?.hide(); isVisible = false; });
ipcMain.on('minimize-hud', () => { win?.minimize(); });
ipcMain.on('toggle-hud',   () => {
  if (isVisible) { win?.hide(); isVisible = false; }
  else           { win?.show(); isVisible = true;  }
});

// Keep app alive even if all windows close
app.on('window-all-closed', (e) => e.preventDefault());

app.whenReady().then(() => {
  createWindow();
  createTray();
});

app.on('before-quit', () => {
  tray?.destroy();
});
