const { createWindowsInstaller } = require('electron-winstaller');
const path = require('path');

async function build() {
  console.log('Generating Windows Setup Installer (.exe)...');
  try {
    await createWindowsInstaller({
      appDirectory: path.join(__dirname, 'dist-exe/Gokul Cycle & Tyres-win32-x64'),
      outputDirectory: path.join(__dirname, 'dist-installer'),
      authors: 'Gokul Cycle & Tyres',
      exe: 'Gokul Cycle & Tyres.exe',
      setupExe: 'GokulCycleTyresSetup.exe',
      noMsi: true,
      description: 'Gokul Cycle & Tyres Inventory Management System Installer'
    });
    console.log('Successfully created Windows installer! Look inside the "dist-installer" directory.');
  } catch (error) {
    console.error('Failed to create Windows installer:', error.message);
  }
}

build();
