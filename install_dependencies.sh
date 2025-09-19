#!/bin/bash

# 这是一个为本项目提供一键式安装的脚本。
# 它会自动处理系统依赖（为 Python 3.10 添加 PPA）、
# 创建一个独立的 Python 虚拟环境，
# 并将所需的包安装到其中。

# 确保脚本从其自身所在的目录运行
cd "$(dirname "$0")" || exit

echo "开始一键安装流程..."

# --- 步骤 1: 安装系统依赖 (Python 3.10) ---
# 检查 python3.10 是否已安装
if ! command -v python3.10 &> /dev/null
then
    echo "未找到 Python 3.10，现在开始安装..."
    # 更新包列表并安装 PPA 管理工具
    sudo apt-get update
    sudo apt-get install -y software-properties-common
    # 添加 deadsnakes PPA 以获取最新的 Python 版本
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    # 再次更新包列表并安装 Python 3.10
    sudo apt-get update
    sudo apt-get install -y python3.10 python3.10-venv
else
    echo "Python 3.10 已安装。"
fi

# --- 步骤 2: 创建 Python 虚拟环境 ---
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "正在 './$VENV_DIR' 目录中创建 Python 虚拟环境..."
    python3.10 -m venv "$VENV_DIR"
else
    echo "虚拟环境 './$VENV_DIR' 已存在。"
fi

# --- 步骤 3: 安装 Python 依赖包 ---
echo "正在将 requirements.txt 中的 Python 依赖包安装到虚拟环境中..."
# 使用虚拟环境中的 pip 来安装依赖包，并先升级 pip
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r requirements.txt

# --- 完成提示 ---
echo ""
echo "-----------------------------------------------------------------"
echo "安装完成！"
echo "要运行此应用，您必须先激活虚拟环境。"
echo "请在此项目录下运行以下命令来激活环境:"
echo ""
echo "source venv/bin/activate"
echo ""
echo "激活后，您就可以运行应用的主程序了。"
echo "-----------------------------------------------------------------"