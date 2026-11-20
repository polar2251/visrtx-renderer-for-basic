"""Read the scene snapshot that OVITO Basic 3.14 writes as a POV-Ray file."""

from collections import defaultdict
from dataclasses import dataclass
from math import atan, cos, degrees, hypot, isfinite, radians, sin, tan
from pathlib import Path
import re


_VECTOR = r"<([^<>]+)>"
_PARTICLE = re.compile(rf"(SPRTCLE|CPRTCLE|DPRTCLE|SQPRTCLE)\(\s*{_VECTOR}\s*,\s*([^,]+),\s*rgbt\s*{_VECTOR}\s*\)")
_CYLINDER = re.compile(rf"CYL\(\s*{_VECTOR}\s*,\s*{_VECTOR}\s*,\s*([^,]+),\s*rgbt\s*{_VECTOR}\s*\)")
_CAMERA = re.compile(r"^camera\s*\{(.*?)^\}", re.M | re.S)


@dataclass(frozen=True)
class Camera:
    projection: str
    position: tuple
    direction: tuple
    up: tuple
    field: float
    aspect: float
    background: tuple
    transparent: bool


def numbers(text, length):
    values = tuple(float(value) for value in text.split(","))
    if len(values) != length or not all(map(isfinite, values)):
        raise ValueError("OVITO 장면 파일의 좌표를 읽을 수 없습니다.")
    return values


def ovito_coordinates(vector):
    x, y, z = vector
    return (x, z, y)


def unit_vector(vector):
    length = hypot(*vector)
    if not length:
        raise ValueError("OVITO 장면의 카메라 방향을 읽을 수 없습니다.")
    return tuple(component / length for component in vector)


def rotate(vector, axis, angle):
    x, y, z = vector
    a, b, c = axis
    length = hypot(a, b, c)
    if length == 0:
        return vector
    a, b, c = a / length, b / length, c / length
    dot = a * x + b * y + c * z
    cross = (b * z - c * y, c * x - a * z, a * y - b * x)
    co, si = cos(angle), sin(angle)
    return tuple(co * v + si * k + (1 - co) * dot * n for v, k, n in zip(vector, cross, (a, b, c)))


def read_camera(path):
    with Path(path).open("r", encoding="utf-8-sig") as stream:
        header = stream.read(4096)
    camera = _CAMERA.search(header)
    if camera is None or '#include "transforms.inc"' not in header:
        raise ValueError("OVITO 3.14의 POV-Ray scene 내보내기 파일을 선택하세요.")
    block = camera[1]

    def get_vector(keyword):
        match = re.search(rf"^\s*{keyword}\s+{_VECTOR}", block, re.M)
        if match is None:
            raise ValueError(f"OVITO 장면에서 {keyword} 카메라 설정을 찾지 못했습니다.")
        return numbers(match[1], 3)

    projection = "perspective" if re.search(r"^\s*perspective\b", block, re.M) else "orthographic"
    transform = re.search(rf"Axis_Rotate_Trans\(\s*{_VECTOR}\s*,\s*([^)]*)\)", block)
    if transform is None:
        raise ValueError("OVITO 장면에 카메라 회전 정보가 없습니다.")
    axis, rotation = numbers(transform[1], 3), radians(float(transform[2]))
    up = get_vector("up")
    up_length = hypot(*up)
    right_length = hypot(*get_vector("right"))
    if not up_length or not right_length:
        raise ValueError("OVITO 장면의 화면 비율을 읽을 수 없습니다.")
    aspect = right_length / up_length
    if projection == "perspective":
        output_angle = re.search(r"^\s*angle\s+(\S+)", block, re.M)
        if output_angle is None:
            raise ValueError("OVITO 장면에 카메라 시야각이 없습니다.")
        field = degrees(2 * atan(tan(radians(float(output_angle[1])) / 2) / aspect))
    else:
        field = hypot(*up) / 2

    background = re.search(rf"background\s*\{{\s*color\s+rgbt\s+{_VECTOR}", header)
    red, green, blue, alpha = numbers(background[1], 4) if background else (1, 1, 1, 0)
    direction = get_vector("direction")
    return Camera(
        projection, ovito_coordinates(get_vector("translate")),
        unit_vector(ovito_coordinates(rotate(direction, axis, rotation))),
        unit_vector(ovito_coordinates(rotate(up, axis, rotation))), field, aspect,
        (red, green, blue), alpha > 0.5,
    )


def load_snapshot(path):
    import numpy as np
    from ovito.data import DataCollection, Particles
    from ovito.vis import ParticlesVis

    particles_by_shape = defaultdict(list)
    cylinders = []
    unsupported = set()
    inside_macro = False
    with Path(path).open("r", encoding="utf-8-sig") as stream:
        for line in stream:
            line = line.strip()
            if line.startswith("#macro "):
                inside_macro = True
            elif line == "#end":
                inside_macro = False
            elif not inside_macro:
                atom = _PARTICLE.fullmatch(line)
                segment = _CYLINDER.fullmatch(line)
                if atom:
                    position = ovito_coordinates(numbers(atom[2], 3))
                    rgba = numbers(atom[4], 4)
                    particles_by_shape[atom[1]].append((*position, float(atom[3]), *rgba))
                elif segment:
                    origin = ovito_coordinates(numbers(segment[1], 3))
                    direction = ovito_coordinates(numbers(segment[2], 3))
                    cylinders.append((*origin, *direction, float(segment[3]), *numbers(segment[4], 4)))
                elif re.match(r"(?:mesh2?|object|polygon|sphere|cylinder|triangle|smooth_triangle|quadric|cone|box|text)\s*\{", line):
                    unsupported.add(line.split("{", 1)[0].strip())

    if not particles_by_shape and not cylinders:
        raise ValueError("OVITO 장면에 가져올 원자 또는 실린더가 없습니다.")
    if unsupported:
        raise ValueError(f"이 장면에는 지원하지 않는 객체가 있습니다 ({', '.join(sorted(unsupported))}).")

    shapes = {
        "SPRTCLE": ParticlesVis.Shape.Sphere, "CPRTCLE": ParticlesVis.Shape.Box,
        "DPRTCLE": ParticlesVis.Shape.Circle, "SQPRTCLE": ParticlesVis.Shape.Square,
    }
    data = DataCollection()
    for code, rows in particles_by_shape.items():
        values = np.asarray(rows)
        system = Particles(identifier=code)
        system.vis.shape = shapes[code]
        system.create_property("Position", data=values[:, :3])
        system.create_property("Radius", data=values[:, 3])
        system.create_property("Color", data=values[:, 4:7])
        system.create_property("Transparency", data=values[:, 7])
        data.objects.append(system)
    if cylinders:
        values = np.asarray(cylinders)
        segments = values[:, 3:6]
        lengths = np.linalg.norm(segments, axis=1)
        keep = lengths > 0
        values, segments, lengths = values[keep], segments[keep], lengths[keep]
        if len(lengths):
            unit = segments / lengths[:, None]
            rotations = np.column_stack((-unit[:, 1], unit[:, 0], np.zeros(len(unit)), 1 + unit[:, 2]))
            backwards = np.linalg.norm(rotations, axis=1) < 1e-12
            rotations[backwards] = (1, 0, 0, 0)
            rotations /= np.linalg.norm(rotations, axis=1)[:, None]
            system = Particles(identifier="cylinders")
            system.vis.shape = ParticlesVis.Shape.Cylinder
            system.create_property("Position", data=values[:, :3] + segments / 2)
            system.create_property("Aspherical Shape", data=np.column_stack((values[:, 6], values[:, 6], lengths)))
            system.create_property("Orientation", data=rotations)
            system.create_property("Color", data=values[:, 7:10])
            system.create_property("Transparency", data=values[:, 10])
            data.objects.append(system)
    return data
