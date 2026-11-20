"""Open the existing OVITO window's standard export menu on explicit request."""

import time


def action_name(control):
    return control.Name.split("\t", 1)[0].replace("&", "").rstrip(".…").strip().casefold()


def open_export_menu():
    import uiautomation as ui

    processes = {item.pid for item in ui.GetProcesses(detailedInfo=False)
                 if item.exeName.casefold() in {"ovito.exe", "ovito-basic.exe"}}
    if len(processes) != 1:
        return False
    desktop = ui.GetRootControl()
    windows = [window for window in desktop.GetChildren()
               if window.ProcessId in processes and "ovito" in window.Name.casefold()]
    if len(windows) != 1:
        return False

    def find_item(roots, label):
        return next((control for window in roots
                     for control, _ in ui.WalkControl(window, maxDepth=5)
                     if control.ControlType == ui.ControlType.MenuItemControl
                     and action_name(control) == label and control.IsEnabled), None)

    main = windows[0]
    export = find_item(windows, "export file")
    if export is None:
        menu = find_item(windows, "file")
        if menu is None:
            return False
        pattern = menu.GetPattern(ui.PatternId.ExpandCollapsePattern)
        if pattern is None:
            return False
        pattern.Expand()
        for _ in range(4):
            time.sleep(0.1)
            roots = [window for window in desktop.GetChildren() if window.ProcessId == main.ProcessId]
            export = find_item(roots, "export file")
            if export is not None:
                break
    if export is None:
        return False
    invoke = export.GetPattern(ui.PatternId.InvokePattern)
    if invoke is None:
        return False
    invoke.Invoke()
    return True
