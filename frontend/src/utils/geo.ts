import proj4 from "proj4";
import type { CandidateRead } from "../types";

export type FeatureCollection = {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    id: string;
    geometry: {
      type: "Polygon";
      coordinates: number[][][];
    };
    properties: Record<string, unknown>;
  }>;
};

function transformerForEpsg(epsg: number | null): ((xy: [number, number]) => [number, number]) | null {
  if (!epsg || epsg === 4326) return (xy) => xy;

  if (epsg === 3857) {
    return ([x, y]) => {
      const lon = (x / 20037508.34) * 180;
      const latRadians = (Math.PI / 2) - 2 * Math.atan(Math.exp((-y / 20037508.34) * Math.PI));
      return [lon, (latRadians * 180) / Math.PI];
    };
  }

  const isNorthUtm = epsg >= 32601 && epsg <= 32660;
  const isSouthUtm = epsg >= 32701 && epsg <= 32760;
  if (isNorthUtm || isSouthUtm) {
    const zone = epsg - (isNorthUtm ? 32600 : 32700);
    const source = `+proj=utm +zone=${zone} +datum=WGS84 +units=m +no_defs${
      isSouthUtm ? " +south" : ""
    }`;
    return ([x, y]) => proj4(source, "WGS84", [x, y]) as [number, number];
  }

  return null;
}

export function candidatesToFeatureCollection(
  candidates: CandidateRead[],
  epsg: number | null,
): FeatureCollection {
  const transform = transformerForEpsg(epsg);

  return {
    type: "FeatureCollection",
    features: candidates.map((candidate) => {
      const { minx, miny, maxx, maxy } = candidate.bbox;
      const ring: [number, number][] = [
        [minx, miny],
        [maxx, miny],
        [maxx, maxy],
        [minx, maxy],
        [minx, miny],
      ];
      const coordinates = ring.map((xy) => (transform ? transform(xy) : xy));

      return {
        type: "Feature",
        id: candidate.id,
        geometry: {
          type: "Polygon",
          coordinates: [coordinates],
        },
        properties: {
          id: candidate.id,
          tile_id: candidate.tile_id,
          area: candidate.area,
          point_count: candidate.point_count,
          distance_mean: candidate.distance_mean,
          distance_max: candidate.distance_max,
          volume: candidate.volume,
          height: candidate.height,
        },
      };
    }),
  };
}

export function bboxCenter(candidate: CandidateRead, epsg: number | null): [number, number] | null {
  const transform = transformerForEpsg(epsg);
  if (!transform) return null;

  const center: [number, number] = [
    (candidate.bbox.minx + candidate.bbox.maxx) / 2,
    (candidate.bbox.miny + candidate.bbox.maxy) / 2,
  ];
  return transform(center);
}
