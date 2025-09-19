# 令牌管理系统 - 最终项目结构

```
token-manager/
├── src/                           # 源代码目录
│   ├── __init__.py               # Python包初始化文件
│   ├── gui_main.py               # 主GUI界面 (32KB)
│   ├── token_query_service.py     # 令牌查询服务 (13KB)
│   ├── database_manager.py       # 数据库管理 (14KB)
│   ├── config_manager.py         # 配置管理 (8KB)
│   ├── export_dialog.py          # 导出对话框 (16KB)
│   ├── settings_dialog.py        # 设置对话框 (15KB)
│   ├── proxy_server.py           # API代理服务器
│   └── proxy_settings_dialog.py  # 代理设置对话框
├── database/                     # 数据库目录
│   └── token_manager.db         # SQLite数据库文件 (45KB)
├── requirements.txt              # Python依赖包列表
├── config.json                  # 应用配置文件
├── icon.ico                     # 应用程序图标 (7KB, 多尺寸)
├── icon.png                     # PNG格式图标 (1.4KB)
├── main.py                      # 程序入口文件
├── README.md                    # 项目说明文档
├── PROJECT_STRUCTURE.md         # 项目结构说明
├── .gitignore                   # Git忽略文件
└── LICENSE                      # MIT开源许可证
```

## 核心功能模块

### GUI主界面 (`src/gui_main.py`)
- 令牌管理主窗口
- 令牌列表显示和排序
- 状态栏和控制面板
- 日志显示区域
- 所有UI事件处理
- 代理服务器控制集成
- 代理状态实时显示

### API代理服务器 (`src/proxy_server.py`)
- 轻量级HTTP代理服务器（基于Flask）
- 密钥轮询和负载均衡算法
- 自动故障检测和恢复机制
- 请求日志和统计信息
- 多线程安全的密钥池管理

### 令牌查询服务 (`src/token_query_service.py`)
- SiliconFlow API请求处理
- 多线程令牌处理
- 令牌状态分类算法
- 批处理和导入功能

### 数据库管理 (`src/database_manager.py`)
- SQLite数据库操作
- 令牌增删改查
- 状态统计和批量操作
- 数据迁移工具集成

### 配置管理 (`src/config_manager.py`)
- JSON配置文件读写
- 应用设置管理
- 窗口大小和刷新间隔配置
- 代理服务器配置管理

### 对话框模块
- **导出对话框** (`src/export_dialog.py`): 令牌导出功能
- **设置对话框** (`src/settings_dialog.py`): 应用配置界面
- **代理设置对话框** (`src/proxy_settings_dialog.py`): 代理服务器配置界面

## 资源文件

### 图标文件
- `icon.ico`: 多尺寸ICO图标文件，支持任务栏显示
- `icon.png`: PNG格式图标，用于其他用途

### 配置文件
- `config.json`: 默认配置文件，包含API端点和UI设置
- `requirements.txt`: Python依赖包列表

## 文档文件

- `README.md`: 详细的项目说明和使用指南
- `PROJECT_STRUCTURE.md`: 项目结构说明
- `LICENSE`: MIT开源许可证

## 数据文件

- `database/token_manager.db`: SQLite数据库文件，存储所有令牌数据

## 目录说明

- `database/`: SQLite数据库存储目录
- `.git/`: Git版本控制目录
- `__pycache__/`: Python字节码缓存目录（运行时生成）

## 总览

本项目是一个完整的Python/Tkinter桌面应用程序，具有现代化的GUI界面和完整的令牌管理功能。项目结构清晰，模块化设计，易于维护和扩展。

### 最终打包说明

为创建可执行文件，可以使用PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=icon.ico main.py
```

这将生成一个独立的可执行文件，无需安装Python环境即可运行。