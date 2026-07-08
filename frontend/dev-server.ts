import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

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

console.log(`\x1b[36m[Dev Manager] Using Python executable: ${pythonPath}\x1b[0m`);

// Spawn backend
const backendProcess: ChildProcess = spawn(pythonPath, ['-m', 'core.modes.web_api'], {
  cwd: rootDir,
  env: {
    ...process.env,
    PYTHONPATH: path.join(rootDir, 'backend')
  },
  stdio: 'inherit'
});

// Spawn frontend (Vite)
const frontendProcess: ChildProcess = spawn('npx', ['vite'], {
  cwd: __dirname,
  stdio: 'inherit',
  shell: true
});

// Handle exits
const cleanup = () => {
  console.log('\n\x1b[33m[Dev Manager] Shutting down backend and frontend servers...\x1b[0m');
  backendProcess.kill();
  frontendProcess.kill();
  process.exit();
};

process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);

backendProcess.on('exit', () => {
  console.log('\x1b[31m[Dev Manager] Backend server exited.\x1b[0m');
  cleanup();
});

frontendProcess.on('exit', () => {
  console.log('\x1b[31m[Dev Manager] Frontend server exited.\x1b[0m');
  cleanup();
});
