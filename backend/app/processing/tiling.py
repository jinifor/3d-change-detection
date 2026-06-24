import math

from sqlalchemy.orm import Session

from app.db.models import Tile


def create_tiles(
    db: Session,
    project_id: str,
    bbox: dict[str, float],
    tile_size_m: float,
) -> list[Tile]:
    db.query(Tile).filter(Tile.project_id == project_id).delete()
    tiles: list[Tile] = []

    minx = bbox["minx"]
    miny = bbox["miny"]
    maxx = bbox["maxx"]
    maxy = bbox["maxy"]

    cols = max(1, math.ceil((maxx - minx) / tile_size_m))
    rows = max(1, math.ceil((maxy - miny) / tile_size_m))

    for row in range(rows):
        y0 = miny + row * tile_size_m
        y1 = min(y0 + tile_size_m, maxy)
        for col in range(cols):
            x0 = minx + col * tile_size_m
            x1 = min(x0 + tile_size_m, maxx)
            tile = Tile(
                project_id=project_id,
                tile_key=f"x{col:04d}_y{row:04d}",
                status="PENDING",
                bbox={"minx": x0, "miny": y0, "maxx": x1, "maxy": y1},
            )
            db.add(tile)
            tiles.append(tile)

    db.commit()
    return tiles
