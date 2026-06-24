from pathlib import Path

from app.processing.pdal import run_pdal_pipeline


def convert_to_copc(input_path: str | Path, output_path: str | Path) -> None:
    output = Path(output_path)
    run_pdal_pipeline(
        [
            {"type": "readers.las", "filename": str(input_path)},
            {
                "type": "writers.copc",
                "filename": str(output),
                "forward": "all",
            },
        ],
        output.with_suffix(".pipeline.json"),
    )
