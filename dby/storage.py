"""项目存档。实验要跑 7~14 天，所以项目必须能存下来、过几天再打开。"""

from __future__ import annotations

from pathlib import Path

from .models import Project

DEFAULT_DIR = Path(__file__).resolve().parent.parent / "data" / "projects"


def save(p: Project, folder: Path = DEFAULT_DIR) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{p.id}.json"
    path.write_text(p.model_dump_json(indent=2), encoding="utf-8")
    return path


def load(project_id: str, folder: Path = DEFAULT_DIR) -> Project:
    return Project.model_validate_json((folder / f"{project_id}.json").read_text(encoding="utf-8"))


def list_projects(folder: Path = DEFAULT_DIR) -> list[Project]:
    if not folder.exists():
        return []
    out = []
    for f in folder.glob("p_*.json"):
        try:
            out.append(Project.model_validate_json(f.read_text(encoding="utf-8")))
        except Exception:
            continue  # 坏文件直接跳过
    return sorted(out, key=lambda p: p.created_at, reverse=True)
