#!/usr/bin/env node

/**
 * 崩坏3专属AI陪伴助手 - 开发服务器脚本
 * 用于启动前端和后端开发服务器
 */

const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const readline = require('readline');

// 颜色输出
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

function log(message, color = colors.reset) {
  console.log(`${color}${message}${colors.reset}`);
}

function logStep(step) {
  console.log(`\n${colors.bright}${colors.cyan}▶ ${step}${colors.reset}`);
}

function logSuccess(message) {
  console.log(`${colors.green}✓ ${message}${colors.reset}`);
}

function logError(message) {
  console.log(`${colors.red}✗ ${message}${colors.reset}`);
}

function logInfo(message) {
  console.log(`${colors.blue}ℹ ${message}${colors.reset}`);
}

function logWarn(message) {
  console.log(`${colors.yellow}⚠ ${message}${colors.reset}`);
}

// 进程管理
const processes = [];

function cleanup() {
  logStep('正在关闭所有进程...');
  
  for (const proc of processes) {
    if (proc && !proc.killed) {
      log(`关闭进程: ${proc.name}`);
      proc.kill('SIGTERM');
    }
  }
  
  logSuccess('所有进程已关闭');
  process.exit(0);
}

// 设置进程退出处理
process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);
process.on('exit', cleanup);

// 启动进程
function startProcess(name, command, args, cwd, env = {}) {
  log(`启动 ${name}...`);
  
  const fullEnv = { ...process.env, ...env };
  const proc = spawn(command, args, { cwd, env: fullEnv, stdio: 'pipe' });
  
  proc.name = name;
  
  // 输出处理
  proc.stdout.on('data', (data) => {
    const lines = data.toString().split('\n');
    lines.forEach(line => {
      if (line.trim()) {
        console.log(`[${name}] ${line}`);
      }
    });
  });
  
  proc.stderr.on('data', (data) => {
    const lines = data.toString().split('\n');
    lines.forEach(line => {
      if (line.trim()) {
        console.log(`[${name} ERR] ${line}`);
      }
    });
  });
  
  proc.on('close', (code) => {
    if (code !== 0 && code !== null) {
      logError(`${name} 进程退出，代码: ${code}`);
      cleanup();
    }
  });
  
  processes.push(proc);
  return proc;
}

// 检查端口占用
function checkPort(port) {
  try {
    execSync(`netstat -ano | findstr :${port}`, { stdio: 'pipe' });
    return true;
  } catch (error) {
    return false;
  }
}

// 启动前端开发服务器
function startFrontend() {
  logStep('启动前端开发服务器 (Vue3 + Electron)');
  
  const frontendDir = path.join(process.cwd(), 'frontend');
  if (!fs.existsSync(frontendDir)) {
    logError(`前端目录不存在: ${frontendDir}`);
    return null;
  }
  
  // 检查是否已安装依赖
  const nodeModules = path.join(frontendDir, 'node_modules');
  if (!fs.existsSync(nodeModules)) {
    logWarn('前端依赖未安装，正在安装...');
    try {
      execSync('pnpm install', { cwd: frontendDir, stdio: 'inherit' });
    } catch (error) {
      logError('前端依赖安装失败');
      return null;
    }
  }
  
  // 启动Vite开发服务器
  const viteProcess = startProcess(
    'Vite',
    'pnpm',
    ['dev'],
    frontendDir,
    { FORCE_COLOR: 'true' }
  );
  
  return viteProcess;
}

// 启动后端开发服务器
function startBackend() {
  logStep('启动后端开发服务器 (Python + FastAPI)');
  
  const backendDir = path.join(process.cwd(), 'backend');
  if (!fs.existsSync(backendDir)) {
    logError(`后端目录不存在: ${backendDir}`);
    return null;
  }
  
  // 检查Python环境
  try {
    execSync('python --version', { stdio: 'pipe' });
  } catch (error) {
    logError('Python未安装或不在PATH中');
    return null;
  }
  
  // 检查虚拟环境
  const venvDir = path.join(backendDir, 'venv');
  const useVenv = fs.existsSync(venvDir);
  
  if (useVenv) {
    logInfo('检测到虚拟环境，使用 venv');
  } else {
    logWarn('未检测到虚拟环境，使用系统Python');
  }
  
  // 检查依赖
  const requirementsFile = path.join(backendDir, 'requirements.txt');
  if (!fs.existsSync(requirementsFile)) {
    logError(`requirements.txt不存在: ${requirementsFile}`);
    return null;
  }
  
  // 启动FastAPI服务器
  const pythonCommand = useVenv 
    ? path.join(venvDir, 'Scripts', 'python.exe')
    : 'python';
  
  const fastapiProcess = startProcess(
    'FastAPI',
    pythonCommand,
    ['-m', 'uvicorn', 'src.main:app', '--reload', '--host', '0.0.0.0', '--port', '8000'],
    backendDir,
    { PYTHONUNBUFFERED: '1' }
  );
  
  return fastapiProcess;
}

// 启动Electron主进程
function startElectron() {
  logStep('启动Electron主进程');
  
  const frontendDir = path.join(process.cwd(), 'frontend');
  if (!fs.existsSync(frontendDir)) {
    logError(`前端目录不存在: ${frontendDir}`);
    return null;
  }
  
  // 等待Vite服务器启动
  setTimeout(() => {
    const electronProcess = startProcess(
      'Electron',
      'pnpm',
      ['electron:dev'],
      frontendDir
    );
    
    electronProcess.on('close', (code) => {
      if (code !== 0) {
        logError('Electron进程异常退出');
      }
    });
  }, 5000); // 等待5秒让Vite服务器启动
  
  return null;
}

// 显示开发信息
function showDevInfo() {
  logStep('开发服务器信息');
  
  logInfo('前端开发服务器: http://localhost:5173');
  logInfo('后端API文档: http://localhost:8000/docs');
  logInfo('后端API服务器: http://localhost:8000');
  logInfo('WebSocket端点: ws://localhost:8000/ws');
  
  console.log('');
  logInfo('可用快捷键:');
  logInfo('  Ctrl+C - 关闭所有服务器');
  logInfo('  r      - 重启所有服务器');
  logInfo('  s      - 显示服务器状态');
  logInfo('  q      - 退出');
}

// 监控键盘输入
function setupKeyboardMonitoring() {
  if (process.stdin.isTTY) {
    process.stdin.setRawMode(true);
    process.stdin.resume();
    process.stdin.setEncoding('utf8');
    
    process.stdin.on('data', (key) => {
      switch (key) {
        case '\u0003': // Ctrl+C
          cleanup();
          break;
        case 'r':
        case 'R':
          logStep('重启所有服务器...');
          cleanup();
          setTimeout(() => {
            startAllServers();
          }, 1000);
          break;
        case 's':
        case 'S':
          showDevInfo();
          break;
        case 'q':
        case 'Q':
          cleanup();
          break;
      }
    });
  }
}

// 启动所有服务器
function startAllServers() {
  log(`${colors.bright}${colors.magenta}崩坏3专属AI陪伴助手 - 开发服务器${colors.reset}`);
  log(`工作目录: ${process.cwd()}`);
  
  // 检查端口占用
  const ports = [5173, 8000];
  for (const port of ports) {
    if (checkPort(port)) {
      logWarn(`端口 ${port} 已被占用，可能会影响服务器启动`);
    }
  }
  
  // 启动服务器
  const frontendProcess = startFrontend();
  const backendProcess = startBackend();
  
  if (!frontendProcess || !backendProcess) {
    logError('服务器启动失败');
    cleanup();
    return;
  }
  
  // 等待后端启动后启动Electron
  setTimeout(() => {
    startElectron();
  }, 3000);
  
  // 显示信息
  setTimeout(() => {
    showDevInfo();
    setupKeyboardMonitoring();
  }, 8000);
}

// 帮助信息
function showHelp() {
  log(`${colors.bright}崩坏3专属AI陪伴助手 - 开发服务器${colors.reset}`);
  log(`用法: node scripts/dev.js [选项]`);
  log('');
  log(`可用选项:`);
  log(`  ${colors.cyan}--frontend${colors.reset}  仅启动前端服务器`);
  log(`  ${colors.cyan}--backend${colors.reset}   仅启动后端服务器`);
  log(`  ${colors.cyan}--all${colors.reset}       启动所有服务器 (默认)`);
  log(`  ${colors.cyan}--help${colors.reset}      显示此帮助信息`);
  log('');
  log(`示例:`);
  log(`  node scripts/dev.js              # 启动所有服务器`);
  log(`  node scripts/dev.js --frontend   # 仅启动前端`);
  log(`  node scripts/dev.js --backend    # 仅启动后端`);
}

// 主函数
async function main() {
  const args = process.argv.slice(2);
  
  if (args.includes('--help') || args.includes('-h')) {
    showHelp();
    return;
  }
  
  if (args.includes('--frontend')) {
    logStep('仅启动前端服务器');
    startFrontend();
    setupKeyboardMonitoring();
  } else if (args.includes('--backend')) {
    logStep('仅启动后端服务器');
    startBackend();
    setupKeyboardMonitoring();
  } else {
    // 默认启动所有
    startAllServers();
  }
}

// 执行
if (require.main === module) {
  main().catch(error => {
    logError(`开发服务器启动失败: ${error.message}`);
    console.error(error);
    process.exit(1);
  });
}

module.exports = { startFrontend, startBackend, startElectron };