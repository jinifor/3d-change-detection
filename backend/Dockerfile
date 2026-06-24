FROM mambaorg/micromamba:2.8.1 AS pdal

RUN micromamba install -y -n base -c conda-forge pdal \
    && micromamba clean --all --yes


FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1
ENV PATH="${PATH}:/opt/conda/bin"
ENV LD_LIBRARY_PATH="/opt/conda/lib"
ENV PROJ_LIB="/opt/conda/share/proj"
ENV GDAL_DATA="/opt/conda/share/gdal"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=pdal /opt/conda /opt/conda

WORKDIR /srv/app

COPY backend/pyproject.toml /srv/app/pyproject.toml
COPY backend/app /srv/app/app
COPY backend/alembic.ini /srv/app/alembic.ini
COPY backend/alembic /srv/app/alembic
RUN uv pip install --system -e .
RUN pdal --version

EXPOSE 8000
