"""
啟動腳本 - 簡化部署
"""

import os
import sys
import subprocess
import platform

def main():
    print("台灣求職避雷器 - 啟動助手")
    print("=" * 50)
    
    # 檢查 Python 版本
    if sys.version_info < (3, 8):
        print("❌ 需要 Python 3.8 或更高版本")
        sys.exit(1)
    
    print("✓ Python 版本檢查通過")
    
    # 檢查虛擬環境
    backend_path = os.path.join(os.path.dirname(__file__), 'backend')
    os.chdir(backend_path)
    
    venv_path = os.path.join(backend_path, 'venv')
    if not os.path.exists(venv_path):
        print("\\n📦 創建虛擬環境...")
        subprocess.run([sys.executable, '-m', 'venv', 'venv'])
    
    # 激活虛擬環境
    if platform.system() == 'Windows':
        python_exe = os.path.join(venv_path, 'Scripts', 'python.exe')
        pip_exe = os.path.join(venv_path, 'Scripts', 'pip.exe')
    else:
        python_exe = os.path.join(venv_path, 'bin', 'python')
        pip_exe = os.path.join(venv_path, 'bin', 'pip')
    
    # 安裝依賴
    print("\\n📥 安裝依賴...")
    subprocess.run([pip_exe, 'install', '-r', 'requirements.txt'])
    
    # 檢查配置文件
    if not os.path.exists('.env'):
        print("\\n⚙️  複製環境配置...")
        with open('.env.example', 'r') as f:
            example = f.read()
        with open('.env', 'w') as f:
            f.write(example)
        print("⚠️  請編輯 backend/.env 文件填入 API Key")
    
    # 啟動後端
    print("\\n🚀 啟動後端服務...")
    print("服務運行在 http://localhost:5000")
    print("按 Ctrl+C 停止服務\\n")
    
    subprocess.run([python_exe, 'app.py'])

if __name__ == '__main__':
    main()
