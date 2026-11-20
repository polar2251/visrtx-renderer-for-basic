import json
import sys
import traceback
from pathlib import Path

from render import RenderJob, render


def run_worker(request: Path):
    job = json.loads(request.read_text(encoding="utf-8"))
    staging = Path(job["staging"])
    try:
        render(RenderJob(**job["settings"]), staging)
    except Exception:
        request.with_suffix(".error").write_text(traceback.format_exc(), encoding="utf-8")
        return 1
    finally:
        staging.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--render-job":
        raise SystemExit(run_worker(Path(sys.argv[2])))
    if sys.argv[1:] == ["--ovito-export"]:
        from ovito_window import open_export_menu

        raise SystemExit(0 if open_export_menu() else 2)

    from gui import launch

    launch()
