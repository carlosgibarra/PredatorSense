# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

from PyInstaller.utils.hooks import collect_submodules


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('app_icon.ico', '.'), ('fonts', 'fonts'), ('PredatorLogo.png', '.'), ('LinuxPredatorSense.png', '.')],
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui', 
        'PyQt5.QtWidgets',
        'PyQt5.QtChart',
        'PyQt5.QtChart.QChart',
        'PyQt5.QtChart.QLineSeries',
        'PyQt5.QtChart.QAreaSeries',
        'PyQt5.QtChart.QChartView',
        'PyQt5.sip',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
