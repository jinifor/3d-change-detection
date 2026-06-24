from dataclasses import dataclass
from pathlib import Path

import laspy
import numpy as np

from app.processing.exceptions import ProcessingError
from app.processing.paths import WorkPaths
from app.processing.pdal import run_pdal_pipeline
from app.schemas import ProcessingParameters


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

    local_matrix, rmse = _icp_point_to_plane(t1_stable, t2_stable, origin_x, origin_y)
    world_matrix = _local_to_world_matrix(local_matrix, origin_x, origin_y)
    _apply_transformation(paths.t2_raw, paths.t2_aligned, world_matrix)
    return RegistrationResult(matrix=world_matrix.tolist(), rmse=rmse)


def _extract_stable_surface(input_path: Path, output_path: Path, voxel_size_m: float) -> None:
    run_pdal_pipeline(
        [
            {"type": "readers.las", "filename": str(input_path)},
            {"type": "filters.smrf"},
            {"type": "filters.range", "limits": "Classification[2:2]"},
            {"type": "filters.voxelcentroid", "cell": voxel_size_m},
            {"type": "writers.las", "filename": str(output_path)},
        ],
        output_path.with_suffix(".pipeline.json"),
    )


def _icp_point_to_plane(
    t1_stable: Path,
    t2_stable: Path,
    origin_x: float,
    origin_y: float,
) -> tuple[np.ndarray, float]:
    try:
        import open3d as o3d
    except ImportError as exc:
        raise ProcessingError("Open3D is required for ICP registration") from exc

    target_points = _read_points(t1_stable, origin_x, origin_y)
    source_points = _read_points(t2_stable, origin_x, origin_y)
    if len(target_points) < 10 or len(source_points) < 10:
        raise ProcessingError("not enough stable-surface points for ICP registration")

    target = o3d.geometry.PointCloud()
    target.points = o3d.utility.Vector3dVector(target_points)
    source = o3d.geometry.PointCloud()
    source.points = o3d.utility.Vector3dVector(source_points)

    target.estimate_normals()
    threshold = _registration_threshold(target_points)
    result = o3d.pipelines.registration.registration_icp(
        source,
        target,
        threshold,
        np.eye(4),
        o3d.pipelines.registration.TransformationEstimationPointToPlane(),
    )
    return np.asarray(result.transformation, dtype=np.float64), float(result.inlier_rmse)


def _registration_threshold(points: np.ndarray) -> float:
    extent = np.ptp(points[:, :2], axis=0)
    return max(float(np.linalg.norm(extent)) * 0.01, 1.0)


def _read_points(path: Path, origin_x: float, origin_y: float) -> np.ndarray:
    with laspy.open(path) as reader:
        las = reader.read()
    points = np.vstack((las.x, las.y, las.z)).T.astype(np.float64, copy=False)
    points[:, 0] -= origin_x
    points[:, 1] -= origin_y
    return points


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
