"""Exercise the packaged worker, including Qt and OVITO's native renderers."""

import argparse
import json
import struct
import subprocess
from itertools import product
from pathlib import Path
from tempfile import TemporaryDirectory


def make_dump(path):
    basis = ((0, 0, 0), (0, 0.5, 0.5), (0.5, 0, 0.5), (0.5, 0.5, 0))
    frames = []
    for timestep, offset in ((0, 0), (100, 8)):
        atoms = [
            f"{index} 1 {(i + x) * 3.6 + offset} {(j + y) * 3.6} {(k + z) * 3.6}"
            for index, ((i, j, k), (x, y, z)) in enumerate(product(product(range(4), repeat=3), basis), 1)
        ]
        frames.append("\n".join([
            f"ITEM: TIMESTEP\n{timestep}\nITEM: NUMBER OF ATOMS\n{len(atoms)}",
            "ITEM: BOX BOUNDS ff ff ff\n-2 25\n-2 17\n-2 17",
            "ITEM: ATOMS id type x y z", *atoms,
        ]))
    path.write_text("\n".join(frames) + "\n", encoding="ascii")


def make_snapshot(path):
    path.write_text(
        """#version 3.5;
#include "transforms.inc"
background { color rgbt <1, 1, 1, 1>}
camera {
  orthographic
  location <0, 1000000, 0>
  direction <0, -1, 0>
  right <12, 0, 0>
  up <0, 0, 8>
  Axis_Rotate_Trans(<-1, 0, 0>, 90)
  translate <0, 0, -10>
}
SPRTCLE(<0, 0, 0>, 1, rgbt <0.1, 0.8, 0.2, 0>)
CYL(<-3, -1, 0>, <0, 2, 0>, 0.2, rgbt <1, 0.1, 0.1, 0>)
""",
        encoding="ascii",
    )


def smoke(command, engine):
    from PySide6.QtGui import QImage

    with TemporaryDirectory(prefix="atom-render-smoke-") as tmp:
        directory = Path(tmp) / "인코딩 test"
        directory.mkdir()
        source = directory / "샘플.hea"
        make_dump(source)
        snapshot = directory / "장면.pov"
        make_snapshot(snapshot)
        for sample, frame in ((source, 1), (snapshot, 0)):
            output = sample.with_suffix(".png")
            request = sample.with_suffix(".json")
            request.write_text(json.dumps({
                "settings": {
                    "source": str(sample), "output": str(output), "engine": engine,
                    "frame": frame, "width": 360, "height": 240, "samples": 4,
                    "transparent": True,
                },
                "staging": str(directory / "staging.png"),
            }), encoding="utf-8")
            result = subprocess.run([*command, "--render-job", str(request)], timeout=360, check=False)
            if result.returncode:
                error = request.with_suffix(".error")
                raise RuntimeError(error.read_text(encoding="utf-8") if error.is_file() else
                                   f"Process exited with {result.returncode}.")
            with output.open("rb") as stream:
                header = stream.read(29)
            assert header[:8] == b"\x89PNG\r\n\x1a\n"
            assert struct.unpack(">II", header[16:24]) == (360, 240)
            image = QImage(str(output))
            assert image.pixelColor(0, 0).alpha() == 0, "Missing transparent background."
            center = image.pixelColor(180, 120)
            assert center.alpha() > 0, "No atoms at center of selected frame."
            if sample == snapshot:
                assert center.green() > center.red(), "Snapshot particle color did not survive import."
                cylinder = image.pixelColor(90, 120)
                assert cylinder.alpha() > 0 and cylinder.red() > cylinder.green(), "Snapshot cylinder is missing."
            print(f"{engine}: {sample.suffix} source rendered to a 360x240 PNG.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="+")
    parser.add_argument("--engine", choices=("VisRTX", "Tachyon"), default="Tachyon")
    args = parser.parse_args()
    smoke(args.command, args.engine)
