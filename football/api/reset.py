import json
import shutil
from pathlib import Path
from uuid import uuid4

from db.mysql_helper import MysqlHelper


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RESULT_FILES = [
    PROJECT_ROOT / "data" / "latest_result.json",
    PROJECT_ROOT / "data" / "latest_result.mp4",
    PROJECT_ROOT / "data" / "latest_result_preview.jpg",
    PROJECT_ROOT / "data" / "avg_speeds.json",
    PROJECT_ROOT / "data" / "avg_accs.json",
    PROJECT_ROOT / "data" / "max_speeds.json",
    PROJECT_ROOT / "data" / "max_accs.json",
    PROJECT_ROOT / "data" / "world_tracks.json",
    PROJECT_ROOT / "avg_speed.png",
    PROJECT_ROOT / "avg_acc.png",
    PROJECT_ROOT / "max_speed.png",
    PROJECT_ROOT / "max_acc.png",
    PROJECT_ROOT / "trajectory.png",
]

RESULT_DIRS = [
    PROJECT_ROOT / "output",
    PROJECT_ROOT / "outputs",
    PROJECT_ROOT / "results",
    PROJECT_ROOT / "runs",
    PROJECT_ROOT / "processed",
    PROJECT_ROOT / "cache",
    PROJECT_ROOT / "data" / "output",
    PROJECT_ROOT / "data" / "outputs",
    PROJECT_ROOT / "data" / "results",
    PROJECT_ROOT / "data" / "processed",
    PROJECT_ROOT / "data" / "cache",
]

GENERATED_FILE_PATTERNS = [
    "processed_*.mp4",
    "*_processed.mp4",
    "tracked_*.mp4",
    "*_tracked.mp4",
    "annotated_*.mp4",
    "*_annotated.mp4",
    "output_*.mp4",
    "*_output.mp4",
    "processed_*.avi",
    "*_processed.avi",
    "tracked_*.avi",
    "*_tracked.avi",
    "annotated_*.avi",
    "*_annotated.avi",
    "output_*.avi",
    "*_output.avi",
]

GENERATED_SEARCH_DIRS = [
    PROJECT_ROOT,
    PROJECT_ROOT / "data",
]

PROTECTED_NAMES = {
    "analysis",
    "api",
    "data",
    "db",
    "football_system",
    "mapping",
    "Ultralytics",
    "vision",
    "visualize",
    "__pycache__",
}

PROTECTED_FILES = {
    PROJECT_ROOT / "data" / "match.mp4",
    PROJECT_ROOT / "data" / "homography.json",
    PROJECT_ROOT / "yolov8n.pt",
}


def _is_inside_project(path):
    try:
        path.resolve().relative_to(PROJECT_ROOT)
        return True
    except ValueError:
        return False


def _safe_unlink(path, warnings):
    if not path.exists() or not path.is_file() or not _is_inside_project(path):
        return False
    if path.resolve() in {p.resolve() for p in PROTECTED_FILES if p.exists()}:
        return False
    try:
        path.unlink()
        return True
    except PermissionError as exc:
        pending_path = path.with_name(f"{path.stem}.delete_pending_{uuid4().hex[:8]}{path.suffix}")
        try:
            path.rename(pending_path)
            pending_path.unlink()
            return True
        except OSError:
            warnings.append(f"文件被占用，已跳过：{path} ({exc})")
            return False
    except OSError as exc:
        warnings.append(f"文件删除失败，已跳过：{path} ({exc})")
        return False


def _safe_rmtree(path, warnings):
    if not path.exists() or not path.is_dir() or not _is_inside_project(path):
        return False
    if path.resolve() == PROJECT_ROOT or path.name in PROTECTED_NAMES:
        return False
    try:
        shutil.rmtree(path)
        return True
    except PermissionError as exc:
        pending_path = path.with_name(f"{path.name}.delete_pending_{uuid4().hex[:8]}")
        try:
            path.rename(pending_path)
            shutil.rmtree(pending_path)
            return True
        except OSError:
            warnings.append(f"目录中有文件被占用，已跳过：{path} ({exc})")
            return False
    except OSError as exc:
        warnings.append(f"目录删除失败，已跳过：{path} ({exc})")
        return False


def clear_results():
    deleted_files = []
    deleted_dirs = []
    warnings = []

    MysqlHelper.clear_results()

    for path in RESULT_FILES:
        if _safe_unlink(path, warnings):
            deleted_files.append(str(path))

    for search_dir in GENERATED_SEARCH_DIRS:
        if not search_dir.exists() or not search_dir.is_dir():
            continue
        for pattern in GENERATED_FILE_PATTERNS:
            for path in search_dir.glob(pattern):
                if _safe_unlink(path, warnings):
                    deleted_files.append(str(path))

    for path in RESULT_DIRS:
        if _safe_rmtree(path, warnings):
            deleted_dirs.append(str(path))

    return {
        "success": True,
        "message": "历史结果已清空",
        "deleted_files": deleted_files,
        "deleted_dirs": deleted_dirs,
        "warnings": warnings,
    }


def main():
    print(json.dumps(clear_results(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
