import json
import subprocess
import sys
import tempfile
import tkinter as tk
from dataclasses import asdict, replace
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from uuid import uuid4

from basic_scene import read_camera
from render import RenderJob, staging_path, vector


class Window:
    def __init__(self, root):
        self.root = root
        self.process = None
        self.poll_task = None
        self.export_check = None
        self.fields = {}
        self.image = None
        self.workspace = tempfile.TemporaryDirectory(prefix="atom-render-")
        self.request = Path(self.workspace.name) / "job.json"
        self.preview_path = self.request.with_name("preview.png")
        self.root.title("Visrtx Renderer for basic")
        self.root.geometry("1070x740")
        self.root.minsize(890, 720)
        self.root.option_add("*Font", ("맑은 고딕", 10))
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        contents = ttk.Frame(root, padding=16)
        contents.pack(fill="both", expand=True)
        contents.columnconfigure(1, weight=1)
        contents.rowconfigure(0, weight=1)
        form = ttk.Frame(contents)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        files = self.section(form, "파일")
        self.source = self.path_field(files, 0, "입력 파일", self.choose_source)
        self.output = self.path_field(files, 1, "PNG 저장 위치", self.choose_output)
        self.frame = self.entry(files, 2, "프레임 (0부터)", "0")
        self.bridge_button = ttk.Button(files, text="열린 OVITO에서 가져오기", command=self.import_open_ovito)
        self.bridge_button.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(6, 2))

        scene = self.section(form, "구조와 카메라")
        self.analysis = self.combo(scene, 0, "원자 색상", ("PTM", "CNA", "원본 색상"))
        self.projection = self.combo(scene, 1, "투영", ("직교", "원근"))
        self.direction = self.entry(scene, 2, "시선 방향 (XYZ)", "-1, 1, -0.75")
        self.position = self.entry(scene, 3, "카메라 위치 (XYZ)", "", "자동")
        self.field = self.entry(scene, 4, "세로 시야", "", "자동")
        ttk.Label(scene, text="원근은 도(°), 직교는 세로 표시 범위의 절반").grid(
            row=5, column=1, columnspan=2, sticky="w", pady=(0, 4)
        )
        self.cell = self.check(scene, 6, "시뮬레이션 셀 표시", False)

        quality = self.section(form, "출력 품질")
        self.engine = self.combo(quality, 0, "렌더러", ("VisRTX", "Tachyon"))
        self.width = self.entry(quality, 1, "가로 (px)", "2400")
        self.height = self.entry(quality, 2, "세로 (px)", "1800")
        self.samples = self.entry(quality, 3, "VisRTX 샘플/픽셀", "64")
        self.occlusion = self.check(quality, 4, "앰비언트 오클루전 (AO)", True)
        self.denoise = self.check(quality, 5, "VisRTX 노이즈 제거", True)
        self.transparent = self.check(quality, 6, "투명 배경", False)

        pane = ttk.Frame(contents)
        pane.grid(row=0, column=1, sticky="nsew")
        ttk.Label(pane, text="구도 미리보기", font=("맑은 고딕", 12, "bold")).pack(anchor="w")
        self.preview = tk.Label(
            pane, text="파일을 선택하고 미리보기를 누르세요.", bg="#e8edf2", fg="#31445b"
        )
        self.preview.pack(fill="both", expand=True, pady=(8, 0))
        self.preview_hint = ttk.Label(pane, text="미리보기는 Tachyon(CPU)으로 구도를 확인합니다.")
        self.preview_hint.pack(anchor="w", pady=8)

        actions = ttk.Frame(contents)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.preview_button = ttk.Button(actions, text="미리보기", command=lambda: self.start(True))
        self.preview_button.pack(side="left")
        self.render_button = ttk.Button(actions, text="PNG 렌더링", command=lambda: self.start(False))
        self.render_button.pack(side="left", padx=8)
        self.cancel_button = ttk.Button(actions, text="취소", command=self.cancel, state="disabled")
        self.cancel_button.pack(side="left")
        self.progress = ttk.Progressbar(actions, mode="indeterminate", length=100)
        self.progress.pack(side="right")
        self.status = tk.StringVar(value="준비")
        ttk.Label(contents, textvariable=self.status, wraplength=840).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

    @staticmethod
    def section(parent, text):
        group = ttk.LabelFrame(parent, text=text, padding=(10, 5))
        group.pack(fill="x", pady=(0, 8))
        group.columnconfigure(1, weight=1)
        return group

    @staticmethod
    def label(parent, row, text):
        ttk.Label(parent, text=text).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=3)

    def entry(self, parent, row, label, default, hint=""):
        value = tk.StringVar(value=default)
        self.label(parent, row, label)
        widget = ttk.Entry(parent, textvariable=value, width=23)
        widget.grid(row=row, column=1, sticky="ew")
        self.fields[str(value)] = widget
        if hint:
            ttk.Label(parent, text=hint).grid(row=row, column=2, padx=(6, 0), sticky="w")
        return value

    def path_field(self, parent, row, label, choose):
        field = self.entry(parent, row, label, "")
        ttk.Button(parent, text="찾기", width=6, command=choose).grid(row=row, column=2, padx=(6, 0))
        return field

    def combo(self, parent, row, label, values):
        self.label(parent, row, label)
        value = tk.StringVar(value=values[0])
        widget = ttk.Combobox(parent, textvariable=value, values=values, state="readonly", width=20)
        widget.grid(row=row, column=1, sticky="ew")
        self.fields[str(value)] = widget
        return value

    def check(self, parent, row, label, default):
        value = tk.BooleanVar(value=default)
        widget = ttk.Checkbutton(parent, text=label, variable=value)
        widget.grid(row=row, column=1, columnspan=2, sticky="w", pady=2)
        self.fields[str(value)] = widget
        return value

    def choose_source(self):
        selected = filedialog.askopenfilename(
            parent=self.root,
            title="시뮬레이션 파일 또는 OVITO 장면 열기",
            filetypes=[("LAMMPS 및 OVITO 장면", "*.dump *.lammpstrj *.hea *.pov *.xyz *.gz *.zst"),
                       ("모든 파일", "*.*")],
        )
        if selected:
            try:
                self.accept_source(Path(selected))
            except (OSError, ValueError) as error:
                messagebox.showerror("파일 열기", str(error), parent=self.root)

    def accept_source(self, path, temporary=False):
        camera = read_camera(path) if path.suffix.casefold() == ".pov" else None
        previous_scene = Path(self.source.get()).suffix.casefold() == ".pov"
        self.source.set(str(path))
        self.frame.set("0")
        for field in (self.frame, self.analysis, self.projection, self.direction, self.position, self.field, self.cell):
            self.fields[str(field)].state(("disabled",) if camera else ("!disabled",))
        if camera:
            try:
                height = max(1, min(16384, int(self.height.get())))
            except ValueError:
                height = 1800
            self.analysis.set("원본 색상")
            self.projection.set("원근" if camera.projection == "perspective" else "직교")
            self.direction.set(", ".join(f"{v:.6g}" for v in camera.direction))
            self.position.set(", ".join(f"{v:.6g}" for v in camera.position))
            self.field.set(f"{camera.field:.6g}")
            scale = min(height, 16384 / camera.aspect)
            self.width.set(str(max(1, round(scale * camera.aspect))))
            self.height.set(str(max(1, round(scale))))
            self.transparent.set(camera.transparent)
        elif previous_scene:
            self.analysis.set("PTM")
            self.projection.set("직교")
            self.direction.set("-1, 1, -0.75")
            self.position.set("")
            self.field.set("")
        if not temporary:
            self.output.set(str(path.with_name(f"{path.stem}_render.png")))
        self.image = None
        self.preview.configure(image="", text="미리보기를 눌러 구도를 확인하세요.")
        self.preview_hint.configure(
            text="내보낸 카메라와 원자 스타일을 적용합니다." if camera
            else "미리보기는 Tachyon(CPU)으로 구도를 확인합니다."
        )

    def import_open_ovito(self):
        if self.export_check is not None:
            self.root.after_cancel(self.export_check)
        exported = self.request.with_name(f"ovito-{uuid4().hex[:8]}.pov")
        self.root.clipboard_clear()
        self.root.clipboard_append(str(exported))
        self.status.set("OVITO의 File → Export File에서 POV-Ray scene을 선택하고 복사된 경로를 붙여 넣으세요.")
        try:
            subprocess.Popen(self.worker_command("--ovito-export"), **self.worker_options())
        except OSError:
            pass
        self.export_check = self.root.after(600, self.check_export, exported, None)

    def check_export(self, exported, previous):
        self.export_check = None
        try:
            stat = exported.stat()
            current = (stat.st_size, stat.st_mtime_ns)
        except OSError:
            current = None
        if current and current[0] and current == previous and self.process is None:
            try:
                self.accept_source(exported, temporary=True)
            except (OSError, ValueError) as error:
                self.status.set(str(error))
                return
            self.status.set("OVITO 장면을 가져왔습니다. 미리보기 또는 PNG 렌더링을 누르세요.")
        else:
            self.export_check = self.root.after(600, self.check_export, exported, current)

    def choose_output(self):
        proposed = Path(self.output.get())
        initialdir = str(proposed.parent) if proposed.name else str(Path.home())
        initialfile = proposed.name or "ovito_render.png"
        selected = filedialog.asksaveasfilename(
            parent=self.root, title="PNG 저장 위치", defaultextension=".png",
            initialdir=initialdir, initialfile=initialfile,
            filetypes=[("PNG 이미지", "*.png")], confirmoverwrite=False,
        )
        if selected:
            self.output.set(selected)

    @staticmethod
    def worker_command(*args):
        if getattr(sys, "frozen", False):
            return [sys.executable, *args]
        return [sys.executable, str(Path(__file__).with_name("app.py")), *args]

    @staticmethod
    def worker_options():
        return {
            "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }

    def job(self, preview):
        position = self.position.get().strip()
        field = self.field.get().strip()
        analysis = self.analysis.get()
        snapshot = Path(self.source.get().strip()).suffix.casefold() == ".pov"
        engine = "Tachyon" if preview and not snapshot else self.engine.get()
        job = RenderJob(
            source=self.source.get().strip(),
            output=str(self.preview_path) if preview else self.output.get().strip(),
            frame=int(self.frame.get()),
            analysis="original" if analysis == "원본 색상" else analysis,
            width=int(self.width.get()),
            height=int(self.height.get()),
            engine=engine,
            samples=(4 if preview else int(self.samples.get())) if engine == "VisRTX" else 1,
            occlusion=self.occlusion.get(),
            denoise=self.denoise.get(),
            cell=self.cell.get(),
            transparent=self.transparent.get(),
            projection="perspective" if self.projection.get() == "원근" else "orthographic",
            direction=vector(self.direction.get(), "시선 방향"),
            position=vector(position, "카메라 위치") if position else None,
            field=float(field) if field else None,
        )
        job.validate()
        if preview:
            scale = min(1, (self.preview.winfo_width() - 12) / job.width,
                        (self.preview.winfo_height() - 12) / job.height)
            job = replace(job, width=max(1, round(job.width * scale)), height=max(1, round(job.height * scale)))
        return job

    def start(self, preview):
        if not preview and not self.output.get().strip():
            self.choose_output()
            if not self.output.get().strip():
                return
        try:
            job = self.job(preview)
            output = Path(job.output).resolve()
            if not preview and output.exists() and not messagebox.askyesno(
                "PNG 덮어쓰기", f"다음 파일을 덮어쓸까요?\n\n{output}", parent=self.root
            ):
                return

            self.staging = staging_path(output)
            self.error_report = self.request.with_suffix(".error")
            self.error_report.unlink(missing_ok=True)
            self.request.write_text(
                json.dumps({"settings": asdict(job), "staging": str(self.staging)}), encoding="utf-8"
            )
            self.process = subprocess.Popen(
                self.worker_command("--render-job", str(self.request)), **self.worker_options(),
            )
        except (OSError, ValueError) as error:
            messagebox.showerror("입력 확인", str(error), parent=self.root)
            return

        self.set_busy(True)
        self.status.set("미리보기 생성 중…" if preview else f"{job.engine} 렌더링 중…")
        self.poll_task = self.root.after(150, self.poll, preview, output, job.engine)

    def set_busy(self, busy):
        self.preview_button.configure(state="disabled" if busy else "normal")
        self.render_button.configure(state="disabled" if busy else "normal")
        self.cancel_button.configure(state="normal" if busy else "disabled")
        self.bridge_button.configure(state="disabled" if busy else "normal")
        if busy:
            self.progress.start(15)
        else:
            self.progress.stop()

    def poll(self, preview, output, engine):
        self.poll_task = None
        exit_code = self.process.poll()
        if exit_code is None:
            self.poll_task = self.root.after(150, self.poll, preview, output, engine)
            return

        self.process = None
        self.set_busy(False)
        if exit_code != 0:
            self.staging.unlink(missing_ok=True)
            self.status.set("렌더링 실패")
            if self.error_report.exists():
                detail = self.error_report.read_text(encoding="utf-8").splitlines()[-1]
            else:
                detail = f"렌더러 프로세스 종료 코드 0x{exit_code & 0xffffffff:08X}."
            if engine == "VisRTX":
                detail += "\n\nNVIDIA 드라이버를 확인하거나 렌더러에서 Tachyon을 선택하세요."
            messagebox.showerror("렌더링 실패", detail, parent=self.root)
            return

        if preview:
            self.image = tk.PhotoImage(file=str(output))
            self.preview.configure(image=self.image, text="")
            self.status.set("미리보기 완료")
        else:
            self.status.set(f"저장 완료 · {output}")

    def cancel(self):
        if self.process is not None:
            self.root.after_cancel(self.poll_task)
            self.poll_task = None
            self.process.terminate()
            self.process.wait()
            self.process = None
            self.staging.unlink(missing_ok=True)
            self.set_busy(False)
            self.status.set("취소됨")

    def close(self):
        self.cancel()
        if self.export_check is not None:
            self.root.after_cancel(self.export_check)
        self.workspace.cleanup()
        self.root.destroy()


def launch():
    root = tk.Tk()
    Window(root)
    root.mainloop()
