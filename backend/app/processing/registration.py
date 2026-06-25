from dataclasses import dataclass
from pathlib import Path

import laspy
import numpy as np
from scipy.spatial import cKDTree

from app.processing.exceptions import ProcessingError
from app.processing.paths import WorkPaths
from app.processing.pdal import run_pdal_pipeline
from app.schemas import ProcessingParameters

ICP_MAX_POINTS = 100_000
ICP_MAX_ITERATIONS = 30
ICP_RMSE_TOLERANCE_M = 1e-5


@dataclass(frozen=True)
class RegistrationResult:
    matrix: list[list[float]]
    rmse: float


def register_t2_to_t1(
    paths: WorkPaths,
    parameters: ProcessingParameters,
    origin_x: float,
    origin_y: float,
) -> RegistrationResult:
    stable_dir = paths.registered_dir / "stable"
    stable_dir.mkdir(parents=True, exist_ok=True)
    t1_stable = stable_dir / "t1_stable.laz"
    t2_stable = stable_dir / "t2_stable.laz"
    _extract_stable_surface(paths.t1_raw, t1_stable, parameters.voxel_size_m)
    _extract_stable_surface(paths.t2_raw, t2_stable, parameters.voxel_size_m)

    local_matrix, rmse = _icp_point_to_point(t1_stable, t2_stable, origin_x, origin_y)
    world_matrix = _local_to_world_matrix(local_matrix, origin_x, origin_y)
    _apply_transformation(paths.t2_raw, paths.t2_aligned, world_matrix)
    return RegistrationResult(matrix=world_matrix.tolist(), rmse=rmse)


def _extract_stable_surface(input_path: Path, output_path: Path, voxel_size_m: float) -> None:
    run_pdal_pipeline(
        [
            {"type": "readers.las", "filename": str(input_path)},
            {"type": "filters.smrf"},
            {"type": "filters.range", "limits": "Classification[2:2]"},
            {"type": "filters.voxelcenternearestneighbor", "cell": voxel_size_m},
            {"type": "writers.las", "filename": str(output_path)},
        ],
        output_path.with_suffix(".pipeline.json"),
    )


def _icp_point_to_point(
    t1_stable: Path,
    t2_stable: Path,
    origin_x: float,
    origin_y: float,
) -> tuple[np.ndarray, float]:
    target_points = _limit_points(_read_points(t1_stable, origin_x, origin_y), ICP_MAX_POINTS)
    source_points = _limit_points(_read_points(t2_stable, origin_x, origin_y), ICP_MAX_POINTS)
    if len(target_points) < 10 or len(source_points) < 10:
        raise ProcessingError("not enough stable-surface points for ICP registration")

    threshold = _registration_threshold(target_points)
    target_tree = cKDTree(target_points)
    transform = np.eye(4, dtype=np.float64)
    previous_rmse = np.inf
    rmse = np.inf

    for _ in range(ICP_MAX_ITERATIONS):
        transformed_source = _transform_points(source_points, transform)
        distances, indices = target_tree.query(transformed_source, distance_upper_bound=threshold)
        matched = np.isfinite(distances)
        if int(np.count_nonzero(matched)) < 10:
            raise ProcessingError("not enough ICP correspondences within registration threshold")

        matched_source = transformed_source[matched]
        matched_target = target_points[indices[matched]]
        delta = _best_fit_transform(matched_source, matched_target)
        transform = delta @ transform

        adjusted_source = _transform_points(matched_source, delta)
        residuals = adjusted_source - matched_target
        rmse = float(np.sqrt(np.mean(np.sum(residuals * residuals, axis=1))))
        if abs(previous_rmse - rmse) < ICP_RMSE_TOLERANCE_M:
            break
        previous_rmse = rmse

    return transform, rmse


def _limit_points(points: np.ndarray, max_points: int) -> np.ndarray:
    if len(points) <= max_points:
        return points
    step = int(np.ceil(len(points) / max_points))
    return np.ascontiguousarray(points[::step][:max_points])


def _transform_points(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    return points @ matrix[:3, :3].T + matrix[:3, 3]


def _best_fit_transform(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    source_centroid = np.mean(source, axis=0)
    target_centroid = np.mean(target, axis=0)
    source_centered = source - source_centroid
    target_centered = target - target_centroid

    covariance = source_centered.T @ target_centered
    u, _, vt = np.linalg.svd(covariance)
    rotation = vt.T @ u.T
    if np.linalg.det(rotation) < 0:
        vt[-1, :] *= -1
        rotation = vt.T @ u.T

    translation = target_centroid - rotation @ source_centroid
    matrix = np.eye(4, dtype=np.float64)
    matrix[:3, :3] = rotation
    matrix[:3, 3] = translation
    return matrix


def _registration_threshold(points: np.ndarray) -> float:
    extent = np.ptp(points[:, :2], axis=0)
    return max(float(np.linalg.norm(extent)) * 0.01, 1.0)


def _read_points(path: Path, origin_x: float, origin_y: float) -> np.ndarray:
    with laspy.open(path) as reader:
        las = reader.read()
    points = np.vstack((las.x, las.y, las.z)).T.astype(np.float64, copy=False)
    points[:, 0] -= origin_x
    points[:, 1] -= origin_y
    return np.ascontiguousarray(points)


def _local_to_world_matrix(local_matrix: np.ndarray, origin_x: float, origin_y: float) -> np.ndarray:
    origin = np.array([origin_x, origin_y, 0.0], dtype=np.float64)
    rotation = local_matrix[:3, :3]
    translation = local_matrix[:3, 3]
    world_matrix = local_matrix.copy()
    world_matrix[:3, 3] = translation + origin - rotation @ origin
    return world_matrix


def _apply_transformation(input_path: Path, output_path: Path, matrix: np.ndarray) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    matrix_text = " ".join(str(float(value)) for value in matrix.reshape(-1))
    run_pdal_pipeline(
        [
            {"type": "readers.las", "filename": str(input_path)},
            {"type": "filters.transformation", "matrix": matrix_text},
            {"type": "writers.las", "filename": str(output_path)},
        ],
        output_path.with_suffix(".pipeline.json"),
    )
