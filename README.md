# Codroid Robot Python SDK

Codroid 机器人 Python 软件开发工具包。支持 TCP 指令控制、实时数据 (CRI) 监控以及运动路径规划。


[![PyPI - Version](https://img.shields.io/pypi/v/codroid-robot-sdk.svg)](https://pypi.org/project/codroid-robot-sdk)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/codroid-robot-sdk.svg)](https://pypi.org/project/codroid-robot-sdk)

-----

## Table of Contents

- [Codroid Robot Python SDK](#codroid-robot-python-sdk)
  - [Table of Contents](#table-of-contents)
  - [🚀 快速开始](#-快速开始)
    - [1. 前置条件](#1-前置条件)
    - [2. 获取代码与初始化](#2-获取代码与初始化)
    - [3. 运行示例程序](#3-运行示例程序)
  - [Installation](#installation)
  - [Basic Usage](#basic-usage)
- [🛠️ Hatch 开发工作流](#️-hatch-开发工作流)
  - [进入开发 Shell](#进入开发-shell)
  - [构建项目](#构建项目)
  - [文档预览](#文档预览)
- [📂 目录结构说明](#-目录结构说明)
  - [License](#license)



## 🚀 快速开始
### 1. 前置条件
- Python: 3.8 及以上版本。
- Hatch: 本项目使用 Hatch 作为项目管理工具。

安装 Hatch:
```bash
pipx install hatch
# 或者使用 pip (如果系统允许)
pip install hatch
```
### 2. 获取代码与初始化
```Bash
git clone <your-repo-url>
cd CodroidSDK/python
```
### 3. 运行示例程序
使用 Hatch 运行示例是最简单的方法，它会自动处理所有依赖和环境路径。
```Bash
# 运行基础使用示例
hatch run python examples/01_basic_usage.py
```

## Installation

```console
pip install codroid-robot-sdk
```

## Basic Usage
```python
from codroid import CodroidControlInterface

# Initialize and connect automatically
with CodroidControlInterface(host="192.168.1.136") as robot:
    robot.to_remote()
    robot.switch_on()
```

# 🛠️ Hatch 开发工作流
本项目采用了现代 Python 的 src 布局，建议通过以下命令进行开发：
## 进入开发 Shell
如果你想在一个持久的虚拟环境中工作，可以进入 Hatch Shell：
```Bash
hatch shell
# 进入 shell 后直接运行 python
python examples/01_basic_usage.py
```
## 构建项目
生成可分发的 .whl 和 .tar.gz 文件：
```Bash
hatch build
```
## 文档预览
本项目配置了 mkdocs 文档环境：
```Bash
# 启动本地文档服务器
hatch run docs:serve
```
# 📂 目录结构说明
- src/codroid/: SDK 核心源码。
  - CodroidControlInterface.py: 主控制类。
  - cri.py: 实时数据流处理。
  - models.py: 数据模型与枚举定义。
- examples/: 示例程序目录。
- pyproject.toml: 项目配置文件 (Hatch 配置)。



## License

`codroid` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
