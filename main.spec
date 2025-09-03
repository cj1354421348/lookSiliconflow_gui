# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# 获取当前目录
current_dir = os.path.abspath('.')
src_path = os.path.join(current_dir, 'src')

# 添加src目录中的所有文件和子目录到datas中
datas = []
if os.path.exists(src_path):
    for root, dirs, files in os.walk(src_path):
        for file in files:
            file_path = os.path.join(root, file)
            # 计算相对于项目根目录的路径
            rel_path = os.path.relpath(file_path, current_dir)
            # 添加到datas中，保持目录结构
            datas.append((file_path, os.path.dirname(rel_path)))

# 添加图标文件
icon_files = []
if os.path.exists('icon.ico'):
    datas.append(('icon.ico', '.'))
    icon_files.append('icon.ico')
if os.path.exists('icon.icns'):
    datas.append(('icon.icns', '.'))
    icon_files.append('icon.icns')

a = Analysis(
    ['main.py'],
    pathex=[current_dir],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'src',
        'src.gui_main',
        'src.database_manager',
        'src.config_manager',
        'src.token_query_service',
        'src.settings_dialog',
        'src.export_dialog',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'tkinter.scrolledtext',
        'requests',
        'sqlite3',
        'hashlib',
        'json',
        'threading',
        'concurrent.futures',
        'datetime',
        'pathlib',
        'logging',
        'typing'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='token-manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_files[0] if icon_files else None,
)