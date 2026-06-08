const { app, BrowserWindow } = require('electron');
const path = require('path');

let mainWindow;

function createWindow() {
  // Create browser window
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    title: "Gokul Cycle & Tyres",
    icon: path.join(__dirname, 'app/static/logo.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      partition: 'persist:gokul_session' // Keeps user authenticated across app launches
    }
  });

  // Load the live Vercel deployment URL
  mainWindow.loadURL('https://gokul-cycle-tyres.vercel.app');

  // Hide default top menu bar
  mainWindow.setMenuBarVisibility(false);

  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

// Start Electron window when app is ready
app.whenReady().then(() => {
  createWindow();

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

// Quit when all windows are closed (except Mac OS)
app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});
