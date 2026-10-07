import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import net from 'net';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Paths
const rootDir = path.resolve(__dirname, '..');
const envPath = path.join(rootDir, '.env');

// Read .env file for PYTHON_PATH
let pythonPath = 'python'; // fallback
if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, 'utf8');
  const match = envContent.match(/PYTHON_PATH\s*=\s*["']?([^"'\r\n]+)["']?/);
  if (match && match[1]) {
    pythonPath = match[1];
  }
}

// Function to check if a port is already listening
function isPortInUse(port: number, host = '127.0.0.1'): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(500);
    socket.once('connect', () => {
      socket.destroy();
      resolve(true);
    });
    socket.once('timeout', () => {
      socket.destroy();
      resolve(false);
    });
    socket.once('error', () => {
      resolve(false);
    });
    socket.connect(port, host);
  });
}

async function start() {
  const backendAlreadyRunning = await isPortInUse(8000);
  let backendProcess: ChildProcess | null = null;

  if (backendAlreadyRunning) {
    console.log('\x1b[33m[Dev Manager] Port 8000 is already active. Reusing existing backend server.\x1b[0m');
  } else {
    console.log(`\x1b[36m[Dev Manager] Using Python executable: ${pythonPath}\x1b[0m`);
    // Spawn backend
    backendProcess = spawn(pythonPath, ['-m', 'core.modes.web_api'], {
      cwd: rootDir,
      env: {
        ...process.env,
        PYTHONPATH: path.join(rootDir, 'backend')
      },
      stdio: 'inherit'
    });

    backendProcess.on('exit', () => {
      console.log('\x1b[31m[Dev Manager] Backend server exited.\x1b[0m');
      cleanup();
    });
  }

  // Spawn frontend (Vite)
  const frontendProcess: ChildProcess = spawn('npx', ['vite'], {
    cwd: __dirname,
    stdio: 'inherit',
    shell: true
  });

  // Handle exits
  const cleanup = () => {
    console.log('\n\x1b[33m[Dev Manager] Shutting down backend and frontend servers...\x1b[0m');
    if (backendProcess && !backendProcess.killed) {
      backendProcess.kill();
    }
    if (!frontendProcess.killed) {
      frontendProcess.kill();
    }
    process.exit();
  };

  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);

  frontendProcess.on('exit', () => {
    console.log('\x1b[31m[Dev Manager] Frontend server exited.\x1b[0m');
    cleanup();
  });
}

start();
