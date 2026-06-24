import json

import laspy
import numpy as np

from app.processing.copc import convert_to_copc
from app.processing.paths import WorkPaths
from app.processing.storage_keys import StorageKeys
from app.services.storage import get_storage_client


def publish_results(project_id: str, paths: WorkPaths, origin_x: float, origin_y: float) -> None:
    _write_change_las(paths, origin_x, origin_y)
    if paths.change_laz.exists():
        convert_to_copc(str(paths.change_laz), str(paths.change_copc))

    storage = get_storage_client()
    if paths.change_copc.exists():
        storage.upload_file(paths.change_copc, StorageKeys.result_change_copc(project_id))
    if paths.change_geojson.exists():
        storage.upload_file(paths.change_geojson, StorageKeys.result_change_geojson(project_id))


def _write_change_las(paths: WorkPaths, origin_x: float, origin_y: float) -> None:
    files = sorted(paths.tile_results_dir.glob("*.npz"))
    points: list[np.ndarray] = []
    distances: list[np.ndarray] = []
    for file in files:
        data = np.load(file)
        if data["points"].size == 0:
            continue
        points.append(data["points"])
        distances.append(data["distances"])

    if not points:
        paths.results_dir.mkdir(parents=True, exist_ok=True)
        paths.change_geojson.write_text(
            json.dumps({"type": "FeatureCollection", "features": []}),
            encoding="utf-8",
        )
        laspy.LasData(_result_header(paths)).write(paths.change_laz)
        return

    all_points = np.vstack(points)
    all_distances = np.concatenate(distances)
    all_points[:, 0] += origin_x
    all_points[:, 1] += origin_y

    header = _result_header(paths)
    las = laspy.LasData(header)
    las.x = all_points[:, 0]
    las.y = all_points[:, 1]
    las.z = all_points[:, 2]
    las.m3c2_distance = all_distances
    las.red, las.green, las.blue = _distance_colors(all_distances)

    paths.results_dir.mkdir(parents=True, exist_ok=True)
    las.write(paths.change_laz)


def _result_header(paths: WorkPaths) -> laspy.LasHeader:
    with laspy.open(paths.t1_raw) as source:
        source_header = source.header
        header = laspy.LasHeader(point_format=3, version="1.4")
        header.scales = source_header.scales
        header.offsets = source_header.offsets
        crs = source_header.parse_crs()
        if crs is not None:
            header.add_crs(crs)
    header.add_extra_dim(laspy.ExtraBytesParams(name="m3c2_distance", type=np.float64))
    return header


def _distance_colors(distances: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if distances.size == 0:
        empty = np.array([], dtype=np.uint16)
        return empty, empty, empty
    max_abs = max(float(np.max(np.abs(distances))), 1e-9)
    normalized = np.clip(distances / max_abs, -1.0, 1.0)
    red = np.where(normalized > 0, normalized, 0.0)
    blue = np.where(normalized < 0, -normalized, 0.0)
    green = 1.0 - np.abs(normalized)
    scale = np.iinfo(np.uint16).max
    return (
        (red * scale).astype(np.uint16),
        (green * scale).astype(np.uint16),
        (blue * scale).astype(np.uint16),
    )
