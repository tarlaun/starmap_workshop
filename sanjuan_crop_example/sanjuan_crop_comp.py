import sys
import geopandas as gpd


def load_and_clean(path):
    print(f"Loading: {path}")
    gdf = gpd.read_file(path)
    print(f"  Rows loaded: {len(gdf)}")

    if gdf.crs is None:
        raise ValueError(f"Input file has no CRS: {path}")

    if gdf.geometry.isna().any():
        gdf = gdf[~gdf.geometry.isna()].copy()

    invalid_count = (~gdf.geometry.is_valid).sum()
    if invalid_count > 0:
        print(f"  Fixing invalid geometries: {invalid_count}")
        gdf["geometry"] = gdf.geometry.buffer(0)

    return gdf


def compute_dominant_vegetation(crops_gdf, watersheds_gdf):
    print("Filtering SAN JUAN watershed")
    san_juan = watersheds_gdf[watersheds_gdf["watershed_name"] == "SAN JUAN"].copy()
    if san_juan.empty:
        raise ValueError('No watershed found with watershed_name == "SAN JUAN"')

    print(f"  SAN JUAN polygons: {len(san_juan)}")

    print("Reprojecting to EPSG:3310 for area calculations")
    crops_3310 = crops_gdf.to_crs(epsg=3310)
    san_juan_3310 = san_juan.to_crs(epsg=3310)

    print("Ensuring valid geometries after reprojection")
    crops_invalid = (~crops_3310.geometry.is_valid).sum()
    if crops_invalid > 0:
        print(f"  Fixing invalid crop geometries: {crops_invalid}")
        crops_3310["geometry"] = crops_3310.geometry.buffer(0)

    watersheds_invalid = (~san_juan_3310.geometry.is_valid).sum()
    if watersheds_invalid > 0:
        print(f"  Fixing invalid watershed geometries: {watersheds_invalid}")
        san_juan_3310["geometry"] = san_juan_3310.geometry.buffer(0)

    print("Computing spatial overlay intersections")
    clipped = gpd.overlay(crops_3310, san_juan_3310, how="intersection")

    if clipped.empty:
        print("  No crop intersections found within SAN JUAN")
        return clipped

    print(f"  Intersections found: {len(clipped)}")
    print("Computing intersected crop acres")
    clipped["crop_acres"] = clipped.geometry.area / 4046.8564224

    if "class_name" in clipped.columns:
        clipped["crop_class"] = clipped["class_name"]
    elif "class" in clipped.columns:
        clipped["crop_class"] = clipped["class"]
    else:
        clipped["crop_class"] = None

    if "subclass_name" in clipped.columns:
        clipped["crop_subclass"] = clipped["subclass_name"]
    elif "subclass" in clipped.columns:
        clipped["crop_subclass"] = clipped["subclass"]
    else:
        clipped["crop_subclass"] = None

    keep_cols = ["crop_class", "crop_subclass", "crop_acres", "geometry"]
    clipped = clipped[keep_cols].copy()

    print("Reprojecting output to EPSG:4326")
    clipped = clipped.to_crs(epsg=4326)

    return clipped


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python script.py <crops_geojson> <watersheds_geojson> <output_geojson>"
        )
        sys.exit(1)

    crops_path = sys.argv[1]
    watersheds_path = sys.argv[2]
    output_path = sys.argv[3]

    crops_gdf = load_and_clean(crops_path)
    watersheds_gdf = load_and_clean(watersheds_path)

    result = compute_dominant_vegetation(crops_gdf, watersheds_gdf)

    print(f"Writing output GeoJSON: {output_path}")
    result.to_file(output_path, driver="GeoJSON")
    print("Done")


if __name__ == "__main__":
    main()