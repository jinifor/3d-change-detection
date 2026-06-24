import json
import subprocess
from pathlib import Path
from typing import Any

from app.processing.exceptions import ProcessingError


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise ProcessingError(f"{' '.join(command)} failed: {message}")
    return result


def run_pdal_pipeline(stages: list[dict[str, Any]], pipeline_path: Path) -> None:
    pipeline_path.parent.mkdir(parents=True, exist_ok=True)
    pipeline_path.write_text(json.dumps({"pipeline": stages}), encoding="utf-8")
    run_command(["pdal", "pipeline", str(pipeline_path)])


def crop_las(input_path: Path, output_path: Path, bbox: dict[str, float]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bounds = (
        f"([{bbox['minx']},{bbox['maxx']}],"
        f"[{bbox['miny']},{bbox['maxy']}])"
    )
    run_pdal_pipeline(
        [
            {"type": "readers.las", "filename": str(input_path)},
            {"type": "filters.crop", "bounds": bounds},
            {"type": "writers.las", "filename": str(output_path)},
        ],
        output_path.with_suffix(".pipeline.json"),
    )
