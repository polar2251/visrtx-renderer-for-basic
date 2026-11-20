from PyInstaller.isolated import call
from PyInstaller.utils.hooks import collect_dynamic_libs, copy_metadata


def windows_uia_modules():
    import comtypes.client

    module = comtypes.client.GetModule("UIAutomationCore.dll")
    return [module.__name__, module.__wrapper_module__.__name__]


binaries = collect_dynamic_libs("uiautomation")
datas = copy_metadata("uiautomation") + copy_metadata("comtypes")
hiddenimports = call(windows_uia_modules)
