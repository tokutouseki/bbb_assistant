#!/usr/bin/env node

/**
 * 崩坏3专属AI陪伴助手 - 构建脚本
 * 用于构建前端和后端项目
 */

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

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

function runCommand(command, cwd = process.cwd()) {
  try {
    execSync(command, { cwd, stdio: 'inherit' });
    return true;
  } catch (error) {
    logError(`命令执行失败: ${command}`);
    logError(`错误信息: ${error.message}`);
    return false;
  }
}

// 主构建函数
async function build() {
  log(`${colors.bright}${colors.magenta}崩坏3专属AI陪伴助手 - 构建工具${colors.reset}`);
  log(`工作目录: ${process.cwd()}`);
  
  const args = process.argv.slice(2);
  const target = args[0] || 'all';
  
  logStep(`开始构建目标: ${target}`);
  
  const startTime = Date.now();
  let success = true;
  
  switch (target) {
    case 'all':
      success = await buildFrontend() && await buildBackend();
      break;
    case 'frontend':
      success = await buildFrontend();
      break;
    case 'backend':
      success = await buildBackend();
      break;
    case 'electron':
      success = await buildElectron();
      break;
    default:
      logError(`未知构建目标: ${target}`);
      log(`可用目标: all, frontend, backend, electron`);
      process.exit(1);
  }
  
  const endTime = Date.now();
  const duration = ((endTime - startTime) / 1000).toFixed(2);
  
  if (success) {
    logSuccess(`构建完成！耗时: ${duration} 秒`);
  } else {
    logError(`构建失败！耗时: ${duration} 秒`);
    process.exit(1);
  }
}

// 构建前端
async function buildFrontend() {
  logStep('构建前端应用 (Vue3 + Electron)');
  
  const frontendDir = path.join(process.cwd(), 'frontend');
  if (!fs.existsSync(frontendDir)) {
    logError(`前端目录不存在: ${frontendDir}`);
    return false;
  }
  
  log('安装前端依赖...');
  if (!runCommand('pnpm install', frontendDir)) {
    return false;
  }
  
  log('构建Vue应用...');
  if (!runCommand('pnpm build', frontendDir)) {
    return false;
  }
  
  logSuccess('前端构建完成');
  return true;
}

// 构建后端
async function buildBackend() {
  logStep('构建后端服务 (Python + FastAPI)');
  
  const backendDir = path.join(process.cwd(), 'backend');
  if (!fs.existsSync(backendDir)) {
    logError(`后端目录不存在: ${backendDir}`);
    return false;
  }
  
  // 检查Python环境
  try {
    execSync('python --version', { stdio: 'pipe' });
  } catch (error) {
    logError('Python未安装或不在PATH中');
    return false;
  }
  
  // 检查requirements.txt
  const requirementsFile = path.join(backendDir, 'requirements.txt');
  if (!fs.existsSync(requirementsFile)) {
    logError(`requirements.txt不存在: ${requirementsFile}`);
    return false;
  }
  
  log('安装Python依赖...');
  if (!runCommand('pip install -r requirements.txt', backendDir)) {
    return false;
  }
  
  log('类型检查...');
  if (fs.existsSync(path.join(backendDir, 'pyproject.toml'))) {
    runCommand('mypy src/', backendDir);
  }
  
  logSuccess('后端构建完成');
  return true;
}

// 构建Electron应用
async function buildElectron() {
  logStep('打包Electron桌面应用');
  
  const frontendDir = path.join(process.cwd(), 'frontend');
  if (!fs.existsSync(frontendDir)) {
    logError(`前端目录不存在: ${frontendDir}`);
    return false;
  }
  
  log('打包Electron应用...');
  if (!runCommand('pnpm package', frontendDir)) {
    return false;
  }
  
  // 检查输出文件
  const releaseDir = path.join(frontendDir, 'release');
  if (fs.existsSync(releaseDir)) {
    const files = fs.readdirSync(releaseDir);
    log(`生成的文件: ${files.join(', ')}`);
  }
  
  logSuccess('Electron应用打包完成');
  return true;
}

// 环境检查
function checkEnvironment() {
  logStep('检查开发环境');
  
  const checks = [
    { name: 'Node.js', command: 'node --version', minVersion: 'v18.0.0' },
    { name: 'npm', command: 'npm --version', minVersion: '9.0.0' },
    { name: 'pnpm', command: 'pnpm --version', minVersion: '8.0.0' },
    { name: 'Python', command: 'python --version', minVersion: '3.10.0' },
    { name: 'pip', command: 'pip --version', minVersion: '21.0.0' },
  ];
  
  let allPassed = true;
  
  for (const check of checks) {
    try {
      const output = execSync(check.command, { encoding: 'utf8' }).trim();
      const version = output.match(/\d+\.\d+\.\d+/)?.[0] || '未知';
      
      // 简化版本比较
      const majorVersion = parseInt(version.split('.')[0]);
      const requiredMajor = parseInt(check.minVersion.split('.')[0]);
      
      if (majorVersion >= requiredMajor) {
        logSuccess(`${check.name}: ${version} (要求: ${check.minVersion}+)`);
      } else {
        logError(`${check.name}: ${version} (需要: ${check.minVersion}+)`);
        allPassed = false;
      }
    } catch (error) {
      logError(`${check.name}: 未安装`);
      allPassed = false;
    }
  }
  
  return allPassed;
}

// 帮助信息
function showHelp() {
  log(`${colors.bright}崩坏3专属AI陪伴助手 - 构建工具${colors.reset}`);
  log(`用法: node scripts/build.js [目标]`);
  log('');
  log(`可用目标:`);
  log(`  ${colors.cyan}all${colors.reset}      构建前端和后端 (默认)`);
  log(`  ${colors.cyan}frontend${colors.reset} 仅构建前端`);
  log(`  ${colors.cyan}backend${colors.reset}  仅构建后端`);
  log(`  ${colors.cyan}electron${colors.reset} 打包Electron桌面应用`);
  log(`  ${colors.cyan}check${colors.reset}    检查开发环境`);
  log('');
  log(`示例:`);
  log(`  node scripts/build.js           # 构建所有`);
  log(`  node scripts/build.js frontend  # 仅构建前端`);
  log(`  node scripts/build.js check     # 检查环境`);
}

// 主函数
async function main() {
  const args = process.argv.slice(2);
  
  if (args.includes('--help') || args.includes('-h')) {
    showHelp();
    return;
  }
  
  if (args.includes('check')) {
    checkEnvironment();
    return;
  }
  
  // 环境检查
  if (!checkEnvironment()) {
    logError('环境检查未通过，请确保所有依赖已正确安装');
    process.exit(1);
  }
  
  // 执行构建
  await build();
}

// 执行
if (require.main === module) {
  main().catch(error => {
    logError(`构建过程中出现错误: ${error.message}`);
    console.error(error);
    process.exit(1);
  });
}

module.exports = { build, checkEnvironment };