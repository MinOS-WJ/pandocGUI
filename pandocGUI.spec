# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path(SPECPATH)

a = Analysis(
    [str(project_root / "src" / "pandoc_gui" / "__main__.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[
        (
            str(project_root / "Pandoc-GUI.ico"),
            "pandoc_gui/resources",
        )
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="pandocGUI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="x86_64",
    icon=str(project_root / "Pandoc-GUI.ico"),
    version=str(project_root / "packaging" / "windows_version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="pandocGUI",
)
