import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.processing.exceptions import ProcessingError
from app.processing.pdal import run_command


@dataclass(frozen=True)
class ValidationResult:
    crs_epsg: int
    t1_bbox: dict[str, float]
    t2_bbox: dict[str, float]
    overlap_bbox: dict[str, float]
    overlap_ratio: float
    origin_x: float
    origin_y: float
    t1_point_count: int | None
    t2_point_count: int | None


def validate_inputs(t1_path: Path, t2_path: Path) -> ValidationResult:
    t1 = _pdal_info(t1_path)
    t2 = _pdal_info(t2_path)

    t1_epsg = _extract_epsg(t1)
    t2_epsg = _extract_epsg(t2)
    if t1_epsg is None or t2_epsg is None:
        raise ProcessingError("CRS EPSG code is missing from one or both point clouds")
    if t1_epsg != t2_epsg:
        raise ProcessingError(f"CRS mismatch: T1 EPSG:{t1_epsg}, T2 EPSG:{t2_epsg}")

    t1_bbox = _extract_bbox(t1)
    t2_bbox = _extract_bbox(t2)
    if t1_bbox is None or t2_bbox is None:
        raise ProcessingError("failed to extract bbox from PDAL metadata")

    overlap_bbox = _intersection_bbox(t1_bbox, t2_bbox)
    if overlap_bbox is None:
        raise ProcessingError("T1 and T2 bbox do not overlap")

    overlap_ratio = _overlap_ratio(t1_bbox, t2_bbox, overlap_bbox)
    origin_x = math.floor(min(t1_bbox["minx"], t2_bbox["minx"]))
    origin_y = math.floor(min(t1_bbox["miny"], t2_bbox["miny"]))

    return ValidationResult(
        crs_epsg=t1_epsg,
        t1_bbox=t1_bbox,
        t2_bbox=t2_bbox,
        overlap_bbox=overlap_bbox,
        overlap_ratio=overlap_ratio,
        origin_x=origin_x,
        origin_y=origin_y,
        t1_point_count=_extract_point_count(t1),
        t2_point_count=_extract_point_count(t2),
    )


def _pdal_info(path: Path) -> dict[str, Any]:
    result = run_command(["pdal", "info", "--all", str(path)])
    return json.loads(result.stdout)


def _extract_epsg(data: dict[str, Any]) -> int | None:
    text = json.dumps(data)
    patterns = [
        r"EPSG[\"':,\s/]+(\d{4,6})",
        r"AUTHORITY\[\s*\"EPSG\"\s*,\s*\"(\d{4,6})\"\s*\]",
        r'"authority"\s*:\s*"EPSG"\s*,\s*"code"\s*:\s*"?(?P<code>\d{4,6})"?',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group("code") if "code" in match.groupdict() else match.group(1))
    return None


def _extract_bbox(value: Any) -> dict[str, float] | None:
    if isinstance(value, dict):
        lowered = {str(key).lower(): item for key, item in value.items()}
        if {"minx", "miny", "maxx", "maxy"}.issubset(lowered):
            return {
                "minx": float(lowered["minx"]),
                "miny": float(lowered["miny"]),
                "maxx": float(lowered["maxx"]),
                "maxy": float(lowered["maxy"]),
            }
        if "bbox" in lowered:
            bbox = _extract_bbox(lowered["bbox"])
            if bbox is not None:
                return bbox
        if "bounds" in lowered:
            bbox = _extract_bbox(lowered["bounds"])
            if bbox is not None:
                return bbox
        for item in value.values():
            bbox = _extract_bbox(item)
            if bbox is not None:
                return bbox
    elif isinstance(value, list):
        for item in value:
            bbox = _extract_bbox(item)
            if bbox is not None:
                return bbox
    return None


def _extract_point_count(value: Any) -> int | None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_lower = str(key).lower()
            if key_lower in {"num_points", "point_count", "count"} and isinstance(item, int):
                return item
            found = _extract_point_count(item)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _extract_point_count(item)
            if found is not None:
                return found
    return None


def _intersection_bbox(
    t1_bbox: dict[str, float],
    t2_bbox: dict[str, float],
) -> dict[str, float] | None:
    minx = max(t1_bbox["minx"], t2_bbox["minx"])
    miny = max(t1_bbox["miny"], t2_bbox["miny"])
    maxx = min(t1_bbox["maxx"], t2_bbox["maxx"])
    maxy = min(t1_bbox["maxy"], t2_bbox["maxy"])
    if minx >= maxx or miny >= maxy:
        return None
    return {"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy}


def _overlap_ratio(
    t1_bbox: dict[str, float],
    t2_bbox: dict[str, float],
    overlap_bbox: dict[str, float],
) -> float:
    overlap_area = _area(overlap_bbox)
    return overlap_area / max(min(_area(t1_bbox), _area(t2_bbox)), 1e-9)


def _area(bbox: dict[str, float]) -> float:
    return max(bbox["maxx"] - bbox["minx"], 0.0) * max(bbox["maxy"] - bbox["miny"], 0.0)
