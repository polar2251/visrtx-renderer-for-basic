from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules, copy_metadata

# OVITO loads its renderer DLLs and Python bindings from ovito/plugins at runtime.
binaries = collect_dynamic_libs("ovito")
datas = copy_metadata("ovito")
hiddenimports = [
    *collect_submodules("ovito._extensions"),
    "ovito.plugins.ovito_bindings",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtNetwork",
    "PySide6.QtWidgets",
    "PySide6.QtXml",
]
