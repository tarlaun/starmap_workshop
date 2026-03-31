#!/usr/bin/env python3
"""
data_comp.py — Starmap Workshop: Data Composition Step

Computes the dominant vegetation type for each park in Riverside by
intersecting Riverside_Parks with Riverside_VegetationTypes and keeping
the vegetation class with the greatest overlap area per park.

Output: a GeoJSON file (EPSG:4326) ready for MVT tile generation.

Usage
-----
    python3 data_comp.py <parks_geojson> <vegetation_geojson> <output_geojson>

Example
-------
    python3 data_comp.py Riverside_Parks.geojson Riverside_VegetationTypes.geojson \
        Riverside_Parks_DominantVegetation.geojson
"""

import sys
import geopandas as gpd

# ── Constants ────────────────────────────────────────────────────────────────

CRS_EQUAL_AREA = "EPSG:3310"  # California Albers — preserves area for overlap calc
CRS_WGS84 = "EPSG:4326"  # Output CRS expected by Starlet / web maps


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_and_clean(path: str, columns: list[str], crs: str) -> gpd.GeoDataFrame:
    """Load a GeoJSON, keep only the requested columns, reproject, and fix geometries."""
    gdf = gpd.read_file(path)[columns + ["geometry"]]
    gdf = gdf.to_crs(crs)
    gdf = gdf[gdf.geometry.notnull() & ~gdf.geometry.is_empty].copy()
    gdf["geometry"] = gdf.geometry.buffer(0)  # repair any topology issues
    return gdf


def dominant_vegetation(parks: gpd.GeoDataFrame,
                        veg: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    For each park polygon, find the vegetation class whose intersection area
    is largest.  Parks with no overlap receive the label 'Unknown'.
    """
    intersections = gpd.overlay(parks, veg, how="intersection", keep_geom_type=False)

    if intersections.empty:
        result = parks.copy()
        result["dominant_vegetation"] = "Unknown"
        return result

    intersections["overlap_area"] = intersections.geometry.area

    dominant = (
        intersections
        .sort_values(["PARK_NAME", "overlap_area"], ascending=[True, False])
        .drop_duplicates(subset=["PARK_NAME"])
        [["PARK_NAME", "VEGDESC"]]
        .rename(columns={"VEGDESC": "dominant_vegetation"})
    )

    result = parks.merge(dominant, on="PARK_NAME", how="left")
    result["dominant_vegetation"] = result["dominant_vegetation"].fillna("Unknown")
    return result


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    parks_path, veg_path, output_path = sys.argv[1], sys.argv[2], sys.argv[3]

    print("Loading parks …")
    parks = load_and_clean(parks_path, ["PARK_NAME"], CRS_EQUAL_AREA)

    print("Loading vegetation types …")
    veg = load_and_clean(veg_path, ["VEGDESC"], CRS_EQUAL_AREA)

    print(f"  {len(parks)} parks | {len(veg)} vegetation polygons")

    print("Intersecting and computing dominant vegetation …")
    result = dominant_vegetation(parks, veg)

    output = result[["PARK_NAME", "dominant_vegetation", "geometry"]].to_crs(CRS_WGS84)
    output.to_file(output_path, driver="GeoJSON")

    classes = output["dominant_vegetation"].value_counts().to_dict()
    print(f"\nSaved → {output_path}")
    print(f"  {len(output)} parks  |  {len(classes)} vegetation classes")
    for cls, count in sorted(classes.items(), key=lambda x: -x[1]):
        print(f"    {count:>3}  {cls}")


if __name__ == "__main__":
    main()
