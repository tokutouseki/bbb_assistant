#!/usr/bin/env node

/**
 * 崩坏3专属AI陪伴助手 - 打包脚本
 * 用于打包Electron桌面应用
 */

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const archiver = require('archiver');

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

// 获取版本号
function getVersion() {
  try {
    const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
    return packageJson.version || '0.1.0';
  } catch (error) {
    return '0.1.0';
  }
}

// 获取当前时间戳
function getTimestamp() {
  const now = new Date();
  return now.toISOString().replace(/[-:]/g, '').split('.')[0];
}

// 清理目录
function cleanDirectory(dir) {
  if (fs.existsSync(dir)) {
    log(`清理目录: ${dir}`);
    fs.rmSync(dir, { recursive: true, force: true });
  }
  fs.mkdirSync(dir, { recursive: true });
}

// 打包Electron应用
async function packageElectron() {
  logStep('打包Electron桌面应用');
  
  const frontendDir = path.join(process.cwd(), 'frontend');
  if (!fs.existsSync(frontendDir)) {
    logError(`前端目录不存在: ${frontendDir}`);
    return false;
  }
  
  // 构建前端
  log('构建前端应用...');
  if (!runCommand('pnpm build', frontendDir)) {
    return false;
  }
  
  // 打包Electron
  log('打包Electron应用...');
  if (!runCommand('pnpm package', frontendDir)) {
    return false;
  }
  
  // 检查输出
  const releaseDir = path.join(frontendDir, 'release');
  if (!fs.existsSync(releaseDir)) {
    logError(`发布目录不存在: ${releaseDir}`);
    return false;
  }
  
  const files = fs.readdirSync(releaseDir);
  log(`生成的安装包: ${files.join(', ')}`);
  
  return true;
}

// 打包后端服务
async function packageBackend() {
  logStep('打包后端服务');
  
  const backendDir = path.join(process.cwd(), 'backend');
  if (!fs.existsSync(backendDir)) {
    logError(`后端目录不存在: ${backendDir}`);
    return false;
  }
  
  // 创建临时目录
  const tempDir = path.join(process.cwd(), 'temp', 'backend');
  cleanDirectory(tempDir);
  
  // 复制后端文件
  log('复制后端文件...');
  const filesToCopy = [
    'src/**/*',
    'requirements.txt',
    'pyproject.toml',
    'README.md',
    'LICENSE',
  ];
  
  // 简单的文件复制
  function copyRecursive(src, dest) {
    if (fs.statSync(src).isDirectory()) {
      fs.mkdirSync(dest, { recursive: true });
      const items = fs.readdirSync(src);
      for (const item of items) {
        if (item === '__pycache__' || item === '.pyc') continue;
        copyRecursive(path.join(src, item), path.join(dest, item));
      }
    } else {
      fs.copyFileSync(src, dest);
    }
  }
  
  copyRecursive(backendDir, tempDir);
  
  // 清理Python缓存文件
  log('清理Python缓存文件...');
  function cleanPyCache(dir) {
    const items = fs.readdirSync(dir, { withFileTypes: true });
    for (const item of items) {
      const fullPath = path.join(dir, item.name);
      if (item.isDirectory()) {
        if (item.name === '__pycache__') {
          fs.rmSync(fullPath, { recursive: true, force: true });
        } else {
          cleanPyCache(fullPath);
        }
      } else if (item.name.endsWith('.pyc')) {
        fs.unlinkSync(fullPath);
      }
    }
  }
  
  cleanPyCache(tempDir);
  
  // 创建启动脚本
  log('创建启动脚本...');
  const startScript = `@echo off
echo 正在启动崩坏3专属AI陪伴助手后端服务...
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
  echo 错误: Python未安装或不在PATH中
  echo 请安装Python 3.10+ 并添加到系统PATH
  pause
  exit /b 1
)

REM 检查虚拟环境
if exist "venv\\Scripts\\activate.bat" (
  echo 检测到虚拟环境，激活虚拟环境...
  call venv\\Scripts\\activate.bat
)

REM 安装依赖
echo 检查依赖...
pip install -r requirements.txt

REM 启动服务
echo 启动后端服务...
echo API文档: http://localhost:8000/docs
echo 按Ctrl+C停止服务
echo.

python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

pause
`;
  
  fs.writeFileSync(path.join(tempDir, 'start.bat'), startScript, 'utf8');
  
  // 创建Linux启动脚本
  const startScriptLinux = `#!/bin/bash
echo "正在启动崩坏3专属AI陪伴助手后端服务..."

# 检查Python
if ! command -v python3 &> /dev/null; then
  echo "错误: Python3未安装"
  echo "请安装Python 3.10+"
  exit 1
fi

# 检查虚拟环境
if [ -f "venv/bin/activate" ]; then
  echo "检测到虚拟环境，激活虚拟环境..."
  source venv/bin/activate
fi

# 安装依赖
echo "检查依赖..."
pip install -r requirements.txt

# 启动服务
echo "启动后端服务..."
echo "API文档: http://localhost:8000/docs"
echo "按Ctrl+C停止服务"
echo ""

python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000
`;
  
  fs.writeFileSync(path.join(tempDir, 'start.sh'), startScriptLinux, 'utf8');
  fs.chmodSync(path.join(tempDir, 'start.sh'), '755');
  
  // 打包为ZIP
  const version = getVersion();
  const timestamp = getTimestamp();
  const outputFile = path.join(process.cwd(), 'release', `bbb-assistant-backend-v${version}-${timestamp}.zip`);
  
  fs.mkdirSync(path.dirname(outputFile), { recursive: true });
  
  log(`创建ZIP包: ${outputFile}`);
  const output = fs.createWriteStream(outputFile);
  const archive = archiver('zip', { zlib: { level: 9 } });
  
  output.on('close', () => {
    logSuccess(`后端服务打包完成: ${outputFile} (${archive.pointer()} 字节)`);
  });
  
  archive.on('error', (err) => {
    logError(`打包错误: ${err.message}`);
    throw err;
  });
  
  archive.pipe(output);
  archive.directory(tempDir, 'bbb-assistant-backend');
  await archive.finalize();
  
  // 清理临时目录
  fs.rmSync(path.join(process.cwd(), 'temp'), { recursive: true, force: true });
  
  return true;
}

// 创建完整发布包
async function createFullRelease() {
  logStep('创建完整发布包');
  
  const version = getVersion();
  const timestamp = getTimestamp();
  const releaseDir = path.join(process.cwd(), 'release', `bbb-assistant-v${version}-${timestamp}`);
  
  cleanDirectory(releaseDir);
  
  // 打包前端
  log('打包前端应用...');
  const frontendSuccess = await packageElectron();
  if (!frontendSuccess) {
    return false;
  }
  
  // 复制前端安装包
  const frontendReleaseDir = path.join(process.cwd(), 'frontend', 'release');
  if (fs.existsSync(frontendReleaseDir)) {
    const files = fs.readdirSync(frontendReleaseDir);
    for (const file of files) {
      const src = path.join(frontendReleaseDir, file);
      const dest = path.join(releaseDir, 'desktop', file);
      fs.mkdirSync(path.dirname(dest), { recursive: true });
      fs.copyFileSync(src, dest);
      logInfo(`复制桌面应用: ${file}`);
    }
  }
  
  // 打包后端
  log('打包后端服务...');
  const backendSuccess = await packageBackend();
  if (!backendSuccess) {
    return false;
  }
  
  // 复制后端ZIP包
  const backendZips = fs.readdirSync(path.join(process.cwd(), 'release')).filter(f => f.includes('backend'));
  for (const zip of backendZips) {
    const src = path.join(process.cwd(), 'release', zip);
    const dest = path.join(releaseDir, 'backend', zip);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(src, dest);
    logInfo(`复制后端服务: ${zip}`);
  }
  
  // 创建README
  log('创建发布说明...');
  const readme = `# 崩坏3专属AI陪伴助手 v${version}

## 发布说明
- 版本: v${version}
- 构建时间: ${new Date().toISOString()}
- 包含组件: 桌面应用 + 后端服务

## 安装指南

### 桌面应用 (Windows)
1. 进入 \`desktop/\` 目录
2. 运行 \`bbb-assistant Setup ${version}.exe\`
3. 按照安装向导完成安装

### 后端服务
1. 进入 \`backend/\` 目录
2. 解压后端ZIP包
3. 运行 \`start.bat\` (Windows) 或 \`start.sh\` (Linux/Mac)
4. 访问 http://localhost:8000/docs 查看API文档

## 系统要求
- **桌面应用**: Windows 10/11 64位
- **后端服务**: Python 3.10+, 4GB RAM

## 注意事项
1. 首次运行需要安装Python依赖，请确保网络连接
2. 后端服务默认使用8000端口，请确保端口未被占用
3. 模型文件需要额外下载，首次运行时会自动下载

## 更新日志
查看项目仓库获取详细更新日志。

## 技术支持
如有问题，请提交Issue到项目仓库。

---
崩坏3专属AI陪伴助手团队
${new Date().getFullYear()}
`;
  
  fs.writeFileSync(path.join(releaseDir, 'README.txt'), readme, 'utf8');
  
  logSuccess(`完整发布包创建完成: ${releaseDir}`);
  
  // 显示发布包内容
  logStep('发布包内容');
  function listDir(dir, prefix = '') {
    const items = fs.readdirSync(dir);
    for (const item of items) {
      const fullPath = path.join(dir, item);
      const stat = fs.statSync(fullPath);
      if (stat.isDirectory()) {
        logInfo(`${prefix}├── ${item}/`);
        listDir(fullPath, prefix + '│   ');
      } else {
        const size = (stat.size / 1024 / 1024).toFixed(2);
        logInfo(`${prefix}├── ${item} (${size} MB)`);
      }
    }
  }
  
  listDir(releaseDir);
  
  return true;
}

// 帮助信息
function showHelp() {
  log(`${colors.bright}崩坏3专属AI陪伴助手 - 打包工具${colors.reset}`);
  log(`用法: node scripts/package.js [目标]`);
  log('');
  log(`可用目标:`);
  log(`  ${colors.cyan}all${colors.reset}       创建完整发布包 (默认)`);
  log(`  ${colors.cyan}electron${colors.reset}  仅打包Electron桌面应用`);
  log(`  ${colors.cyan}backend${colors.reset}   仅打包后端服务`);
  log(`  ${colors.cyan}--help${colors.reset}    显示此帮助信息`);
  log('');
  log(`示例:`);
  log(`  node scripts/package.js           # 创建完整发布包`);
  log(`  node scripts/package.js electron  # 仅打包桌面应用`);
  log(`  node scripts/package.js backend   # 仅打包后端服务`);
}

// 主函数
async function main() {
  log(`${colors.bright}${colors.magenta}崩坏3专属AI陪伴助手 - 打包工具${colors.reset}`);
  log(`版本: v${getVersion()}`);
  log(`工作目录: ${process.cwd()}`);
  
  const args = process.argv.slice(2);
  
  if (args.includes('--help') || args.includes('-h')) {
    showHelp();
    return;
  }
  
  const target = args[0] || 'all';
  
  // 创建release目录
  const releaseDir = path.join(process.cwd(), 'release');
  fs.mkdirSync(releaseDir, { recursive: true });
  
  let success = false;
  
  switch (target) {
    case 'all':
      success = await createFullRelease();
      break;
    case 'electron':
      success = await packageElectron();
      break;
    case 'backend':
      success = await packageBackend();
      break;
    default:
      logError(`未知目标: ${target}`);
      showHelp();
      process.exit(1);
  }
  
  if (success) {
    logSuccess('打包完成！');
  } else {
    logError('打包失败！');
    process.exit(1);
  }
}

// 执行
if (require.main === module) {
  main().catch(error => {
    logError(`打包过程中出现错误: ${error.message}`);
    console.error(error);
    process.exit(1);
  });
}

module.exports = { packageElectron, packageBackend, createFullRelease };