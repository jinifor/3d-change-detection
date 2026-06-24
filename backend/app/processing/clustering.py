from pathlib import Path

import numpy as np
from geoalchemy2 import WKTElement
from scipy.spatial import ConvexHull
from shapely.geometry import MultiPoint, Point, box, mapping
from sklearn.cluster import DBSCAN
from sqlalchemy.orm import Session

from app.db.models import Candidate, Tile
from app.processing.exceptions import ProcessingError
from app.processing.paths import WorkPaths
from app.schemas import ProcessingParameters


def cluster_change_points(
    db: Session,
    project_id: str,
    crs_epsg: int,
    origin_x: float,
    origin_y: float,
    paths: WorkPaths,
    parameters: ProcessingParameters,
) -> list[dict]:
    files = sorted(paths.tile_results_dir.glob("*.npz"))
    if not files:
        return []

    all_points: list[np.ndarray] = []
    all_distances: list[np.ndarray] = []
    all_tile_ids: list[np.ndarray] = []
    tile_id_to_index: dict[str, int] = {}

    for file in files:
        data = np.load(file)
        points = data["points"]
        distances = data["distances"]
        tile_id = str(data["tile_id"].item())
        if points.size == 0:
            continue
        tile_id_to_index.setdefault(tile_id, len(tile_id_to_index))
        all_points.append(points)
        all_distances.append(distances)
        all_tile_ids.append(np.full(points.shape[0], tile_id_to_index[tile_id], dtype=np.int32))

    if not all_points:
        return []

    points_local = np.vstack(all_points)
    distances = np.concatenate(all_distances)
    tile_indices = np.concatenate(all_tile_ids)

    labels = DBSCAN(
        eps=parameters.cluster_size_m,
        min_samples=parameters.cluster_min_samples,
    ).fit_predict(points_local[:, :2])

    candidates_geojson: list[dict] = []
    unique_labels = [label for label in sorted(set(labels)) if label != -1]

    for label in unique_labels:
        mask = labels == label
        cluster_points_local = points_local[mask]
        cluster_distances = distances[mask]
        if cluster_points_local.shape[0] < parameters.cluster_min_samples:
            continue

        cluster_points_world = cluster_points_local.copy()
        cluster_points_world[:, 0] += origin_x
        cluster_points_world[:, 1] += origin_y

        footprint = _footprint_polygon(cluster_points_world[:, :2], parameters.cluster_size_m)
        centroid = footprint.centroid
        bounds = footprint.bounds
        representative_tile_id = _most_frequent_tile_id(tile_indices[mask], tile_id_to_index)
        tile = db.get(Tile, representative_tile_id) if representative_tile_id else None

        candidate = Candidate(
            project_id=project_id,
            tile_id=tile.id if tile else None,
            geometry=WKTElement(footprint.wkt, srid=crs_epsg),
            centroid=WKTElement(centroid.wkt, srid=crs_epsg),
            bbox={"minx": bounds[0], "miny": bounds[1], "maxx": bounds[2], "maxy": bounds[3]},
            area=float(footprint.area),
            point_count=int(cluster_points_local.shape[0]),
            distance_mean=float(np.mean(cluster_distances)),
            distance_max=float(np.max(np.abs(cluster_distances))),
            volume=None,
            height=None,
        )
        db.add(candidate)
        db.flush()

        candidates_geojson.append(
            {
                "type": "Feature",
                "id": candidate.id,
                "geometry": mapping(footprint),
                "properties": {
                    "id": candidate.id,
                    "point_count": candidate.point_count,
                    "area": candidate.area,
                    "distance_mean": candidate.distance_mean,
                    "distance_max": candidate.distance_max,
                    "volume": None,
                    "height": None,
                },
            }
        )

    db.commit()
    _write_geojson(paths.results_dir / "change.geojson", candidates_geojson)
    return candidates_geojson


def _footprint_polygon(points_xy: np.ndarray, cluster_size_m: float):
    if len(points_xy) == 1:
        return Point(points_xy[0]).buffer(cluster_size_m / 2)
    multipoint = MultiPoint(points_xy)
    hull = multipoint.convex_hull
    if hull.geom_type == "Polygon":
        return hull
    if hull.geom_type == "LineString":
        return hull.buffer(cluster_size_m / 2, cap_style="square")
    if points_xy.shape[0] >= 3:
        try:
            ConvexHull(points_xy)
            return multipoint.convex_hull
        except Exception as exc:  # noqa: BLE001
            raise ProcessingError(f"failed to build candidate footprint: {exc}") from exc
    bounds = multipoint.bounds
    return box(*bounds).buffer(cluster_size_m / 2)


def _most_frequent_tile_id(tile_indices: np.ndarray, tile_id_to_index: dict[str, int]) -> str | None:
    if tile_indices.size == 0:
        return None
    inverse = {value: key for key, value in tile_id_to_index.items()}
    index = int(np.bincount(tile_indices).argmax())
    return inverse.get(index)


def _write_geojson(path: Path, features: list[dict]) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
        encoding="utf-8",
    )
