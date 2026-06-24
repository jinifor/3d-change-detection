from collections.abc import Iterator
from pathlib import Path

import laspy
import numpy as np
from sqlalchemy.orm import Session

from app.db.models import Tile
from app.processing.exceptions import ProcessingError
from app.processing.paths import WorkPaths
from app.processing.pdal import crop_las
from app.schemas import ProcessingParameters


def process_tiles_m3c2(
    db: Session,
    project_id: str,
    origin_x: float,
    origin_y: float,
    paths: WorkPaths,
    parameters: ProcessingParameters,
) -> Iterator[tuple[Tile, Path]]:
    tiles = db.query(Tile).filter(Tile.project_id == project_id).order_by(Tile.tile_key).all()
    for tile in tiles:
        try:
            result = process_tile_m3c2(tile, origin_x, origin_y, paths, parameters)
            tile.status = "DONE"
            db.commit()
            yield tile, result
        except Exception:
            tile.status = "FAILED"
            db.commit()
            raise


def process_tile_m3c2(
    tile: Tile,
    origin_x: float,
    origin_y: float,
    paths: WorkPaths,
    parameters: ProcessingParameters,
) -> Path:
    tile_dir = paths.tiles_dir / tile.tile_key
    tile_dir.mkdir(parents=True, exist_ok=True)

    buffer_m = max(parameters.m3c2_scale_m, parameters.normal_radius_m)
    bbox = tile.bbox
    buffered_bbox = {
        "minx": bbox["minx"] - buffer_m,
        "miny": bbox["miny"] - buffer_m,
        "maxx": bbox["maxx"] + buffer_m,
        "maxy": bbox["maxy"] + buffer_m,
    }

    t1_tile = tile_dir / "t1.laz"
    t2_tile = tile_dir / "t2.laz"
    crop_las(paths.t1_copc, t1_tile, buffered_bbox)
    crop_las(paths.t2_aligned_copc, t2_tile, buffered_bbox)

    points_t1 = _read_local_points(t1_tile, origin_x, origin_y)
    points_t2 = _read_local_points(t2_tile, origin_x, origin_y)
    if points_t1.size == 0 or points_t2.size == 0:
        return _write_tile_result(paths, tile.id, tile.tile_key, np.empty((0, 3)), np.empty((0,)))

    corepoints = _voxel_downsample(points_t1, parameters.voxel_size_m)
    distances = _run_py4dgeo_m3c2(
        points_t1=points_t1,
        points_t2=points_t2,
        corepoints=corepoints,
        normal_radius=parameters.normal_radius_m,
        m3c2_scale=parameters.m3c2_scale_m,
    )

    mask = np.abs(distances) > parameters.distance_threshold_m
    change_points = corepoints[mask]
    change_distances = distances[mask]
    return _write_tile_result(paths, tile.id, tile.tile_key, change_points, change_distances)


def _read_local_points(path: Path, origin_x: float, origin_y: float) -> np.ndarray:
    with laspy.open(path) as reader:
        las = reader.read()
    points = np.vstack((las.x, las.y, las.z)).T.astype(np.float64, copy=False)
    points[:, 0] -= origin_x
    points[:, 1] -= origin_y
    return points


def _voxel_downsample(points: np.ndarray, voxel_size: float) -> np.ndarray:
    if points.size == 0:
        return points
    keys = np.floor(points / voxel_size).astype(np.int64)
    _, unique_indices = np.unique(keys, axis=0, return_index=True)
    return points[np.sort(unique_indices)]


def _run_py4dgeo_m3c2(
    points_t1: np.ndarray,
    points_t2: np.ndarray,
    corepoints: np.ndarray,
    normal_radius: float,
    m3c2_scale: float,
) -> np.ndarray:
    try:
        import py4dgeo
    except ImportError as exc:
        raise ProcessingError("py4dgeo is required for MVP M3C2 change detection") from exc

    if not hasattr(py4dgeo, "Epoch") or not hasattr(py4dgeo, "M3C2"):
        raise ProcessingError("installed py4dgeo does not expose the expected Epoch/M3C2 API")

    epoch1 = py4dgeo.Epoch(points_t1)
    epoch2 = py4dgeo.Epoch(points_t2)

    try:
        m3c2 = py4dgeo.M3C2(
            epochs=(epoch1, epoch2),
            corepoints=corepoints,
            normal_radii=[normal_radius],
            cyl_radius=m3c2_scale,
        )
        result = m3c2.run()
    except TypeError as exc:
        raise ProcessingError(
            "py4dgeo M3C2 API differs from the expected signature; adapter update is required"
        ) from exc

    if isinstance(result, tuple):
        distances = result[0]
    else:
        distances = result
    distances_array = np.asarray(distances, dtype=np.float64)
    if distances_array.shape[0] != corepoints.shape[0]:
        raise ProcessingError("py4dgeo M3C2 returned a distance array with unexpected length")
    return distances_array


def _write_tile_result(
    paths: WorkPaths,
    tile_id: str,
    tile_key: str,
    points: np.ndarray,
    distances: np.ndarray,
) -> Path:
    paths.tile_results_dir.mkdir(parents=True, exist_ok=True)
    output = paths.tile_results_dir / f"{tile_key}.npz"
    np.savez_compressed(output, tile_id=tile_id, points=points, distances=distances)
    return output
