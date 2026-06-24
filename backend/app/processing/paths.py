from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings


@dataclass(frozen=True)
class WorkPaths:
    project_id: str
    root: Path

    @classmethod
    def for_project(cls, project_id: str) -> "WorkPaths":
        root = settings.local_data_dir / "projects" / project_id
        return cls(project_id=project_id, root=root)

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    @property
    def registered_dir(self) -> Path:
        return self.root / "registered"

    @property
    def copc_dir(self) -> Path:
        return self.root / "copc"

    @property
    def tiles_dir(self) -> Path:
        return self.root / "tiles"

    @property
    def tile_results_dir(self) -> Path:
        return self.root / "tile-results"

    @property
    def results_dir(self) -> Path:
        return self.root / "results"

    @property
    def t1_raw(self) -> Path:
        return self.raw_dir / "t1.laz"

    @property
    def t2_raw(self) -> Path:
        return self.raw_dir / "t2.laz"

    @property
    def t2_aligned(self) -> Path:
        return self.registered_dir / "t2_aligned.laz"

    @property
    def t1_copc(self) -> Path:
        return self.copc_dir / "t1.copc.laz"

    @property
    def t2_aligned_copc(self) -> Path:
        return self.copc_dir / "t2_aligned.copc.laz"

    @property
    def change_laz(self) -> Path:
        return self.results_dir / "change.laz"

    @property
    def change_copc(self) -> Path:
        return self.results_dir / "change.copc.laz"

    @property
    def change_geojson(self) -> Path:
        return self.results_dir / "change.geojson"

    def ensure(self) -> None:
        for directory in (
            self.raw_dir,
            self.registered_dir,
            self.copc_dir,
            self.tiles_dir,
            self.tile_results_dir,
            self.results_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
