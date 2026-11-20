from dataclasses import dataclass
from math import hypot, isfinite, radians
from pathlib import Path
from uuid import uuid4

from basic_scene import load_snapshot, read_camera


def vector(text, label):
    values = tuple(float(value) for value in text.replace(",", " ").split())
    if len(values) != 3 or not all(isfinite(value) for value in values):
        raise ValueError(f"{label}에 유한한 숫자 3개를 입력하세요.")
    return values


@dataclass
class RenderJob:
    source: str
    output: str
    frame: int = 0
    analysis: str = "PTM"
    width: int = 2400
    height: int = 1800
    engine: str = "VisRTX"
    samples: int = 64
    occlusion: bool = True
    denoise: bool = True
    cell: bool = False
    transparent: bool = False
    projection: str = "orthographic"
    direction: tuple = (-1, 1, -0.75)
    position: tuple | None = None
    field: float | None = None

    def validate(self):
        source, output = Path(self.source), Path(self.output)
        if not source.is_file():
            raise ValueError("읽을 수 있는 LAMMPS 파일 또는 OVITO 장면을 선택하세요.")
        if output.suffix.lower() != ".png" or not output.parent.is_dir():
            raise ValueError("기존 폴더에 저장할 PNG 경로를 지정하세요.")
        if source.resolve() == output.resolve():
            raise ValueError("입력과 출력에 서로 다른 경로를 지정하세요.")
        if self.frame < 0:
            raise ValueError("프레임 번호는 0 이상이어야 합니다.")
        if not all(1 <= n <= 16384 for n in (self.width, self.height)):
            raise ValueError("가로와 세로는 각각 1–16384 px 범위로 입력하세요.")
        if not 1 <= self.samples <= 4096:
            raise ValueError("픽셀당 샘플은 1–4096 범위로 입력하세요.")
        if self.analysis not in {"PTM", "CNA", "original"}:
            raise ValueError("PTM, CNA 또는 원본 색상을 선택하세요.")
        if self.engine not in {"VisRTX", "Tachyon"}:
            raise ValueError("VisRTX 또는 Tachyon을 선택하세요.")
        if self.projection not in {"orthographic", "perspective"}:
            raise ValueError("직교 또는 원근 투영을 선택하세요.")
        if len(self.direction) != 3 or not all(map(isfinite, self.direction)) or not hypot(*self.direction):
            raise ValueError("시선 방향에 길이가 0보다 큰 벡터를 입력하세요.")
        if self.position is not None and (len(self.position) != 3 or not all(map(isfinite, self.position))):
            raise ValueError("카메라 위치에 유한한 숫자 3개를 입력하세요.")
        if self.field is not None:
            if not isfinite(self.field) or self.field <= 0:
                raise ValueError("시야에 양수를 입력하세요.")
            if self.projection == "perspective" and self.field >= 180:
                raise ValueError("원근 투영의 시야각은 180° 미만이어야 합니다.")


def render(job: RenderJob, staging: Path):
    from ovito.pipeline import Pipeline, StaticSource
    from ovito.vis import AnariRenderer, TachyonRenderer, Viewport

    job.validate()
    camera = read_camera(job.source) if Path(job.source).suffix.casefold() == ".pov" else None
    data = load_snapshot(job.source) if camera else compute_frame(job)
    # Frame zero of this static scene is the selected frame, including during auto-fit.
    scene = Pipeline(source=StaticSource(data=data))
    scene.add_to_scene()
    projection = camera.projection if camera else job.projection
    perspective = projection == "perspective"
    viewport = Viewport(type=Viewport.Type.Perspective if perspective else Viewport.Type.Ortho)
    size = (job.width, job.height)
    if camera:
        viewport.camera_dir = camera.direction
        viewport.camera_up = camera.up
        viewport.camera_pos = camera.position
        viewport.fov = radians(camera.field) if perspective else camera.field
    else:
        viewport.camera_dir = job.direction
        viewport.zoom_all(size=size)
        if job.position is not None:
            viewport.camera_pos = job.position
        if job.field is not None:
            viewport.fov = radians(job.field) if perspective else job.field

    if job.engine == "VisRTX":
        renderer = AnariRenderer(
            samples_per_pixel=job.samples,
            ambient_light_radiance=0.7,
            ambient_occlusion_samples=8 if job.occlusion else 0,
            denoising_enabled=job.denoise,
        )
    else:
        renderer = TachyonRenderer(ambient_occlusion=job.occlusion)

    viewport.render_image(
        filename=str(staging),
        size=size,
        background=camera.background if camera else (1, 1, 1),
        alpha=job.transparent,
        renderer=renderer,
    )
    staging.replace(job.output)


def compute_frame(job):
    from ovito.io import import_file
    from ovito.modifiers import CommonNeighborAnalysisModifier, PolyhedralTemplateMatchingModifier

    pipeline = import_file(job.source)
    if job.frame >= pipeline.num_frames:
        raise ValueError(f"프레임 번호를 0–{pipeline.num_frames - 1} 범위에서 선택하세요.")
    if job.analysis == "PTM":
        pipeline.modifiers.append(PolyhedralTemplateMatchingModifier())
    elif job.analysis == "CNA":
        pipeline.modifiers.append(
            CommonNeighborAnalysisModifier(mode=CommonNeighborAnalysisModifier.Mode.AdaptiveCutoff)
        )

    data = pipeline.compute(job.frame)
    if data.particles is None or data.particles.count == 0:
        raise ValueError("선택한 프레임에 원자가 없습니다.")
    if data.cell is not None:
        data.cell.vis.enabled = job.cell
    return data


def staging_path(output: Path) -> Path:
    return output.with_name(f".atom-render-{uuid4().hex}.png")
