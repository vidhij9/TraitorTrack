const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');

// Function to execute a command and return a promise
function executeCommand(command) {
  return new Promise((resolve, reject) => {
    console.log(`Executing: ${command}`);
    exec(command, (error, stdout, stderr) => {
      if (error) {
        console.error(`Error executing command: ${error.message}`);
        reject(error);
        return;
      }
      if (stderr) {
        console.log(`Command stderr: ${stderr}`);
      }
      console.log(`Command stdout: ${stdout}`);
      resolve(stdout);
    });
  });
}

async function initCapacitor() {
  try {
    // Make sure we have android platform added
    if (!fs.existsSync(path.join(__dirname, 'android'))) {
      console.log('Adding Android platform...');
      await executeCommand('npx cap add android');
    }

    // Sync web assets to native project
    console.log('Syncing assets with Android project...');
    await executeCommand('npx cap sync android');
    
    console.log('Capacitor initialization complete!');
  } catch (error) {
    console.error('Initialization failed:', error);
  }
}

// Run the initialization
initCapacitor();