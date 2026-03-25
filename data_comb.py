import geopandas as gpd
import pandas as pd
import folium
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from branca.element import MacroElement
from jinja2 import Template

# -----------------------------
# Input / output paths
# -----------------------------
parks_path = "/Users/tarlan/Downloads/Riverside_Parks.geojson"
veg_path = "/Users/tarlan/Downloads/Riverside_VegetationTypes.geojson"

output_geojson = "/Users/tarlan/Downloads/Riverside_Parks_DominantVegetation.geojson"
output_html = "Riverside_Parks_DominantVegetation_Map.html"

# -----------------------------
# Load data
# -----------------------------
parks = gpd.read_file(parks_path)[["PARK_NAME", "geometry"]].copy()
veg = gpd.read_file(veg_path)[["VEGDESC", "geometry"]].copy()

# -----------------------------
# Project to an equal-area CRS so overlap areas are meaningful
# -----------------------------
target_crs = "EPSG:3310"  # California Albers
parks = parks.to_crs(target_crs)
veg = veg.to_crs(target_crs)

# -----------------------------
# Keep only valid geometries
# -----------------------------
parks = parks[parks.geometry.notnull() & ~parks.geometry.is_empty].copy()
veg = veg[veg.geometry.notnull() & ~veg.geometry.is_empty].copy()

parks["geometry"] = parks.geometry.buffer(0)
veg["geometry"] = veg.geometry.buffer(0)

# -----------------------------
# Intersect parks with vegetation polygons
# -----------------------------
intersections = gpd.overlay(
    parks,
    veg,
    how="intersection",
    keep_geom_type=False
)

# If no overlaps are found, create output with Unknown vegetation
if intersections.empty:
    result = parks.copy()
    result["dominant_vegetation"] = "Unknown"
else:
    # Compute overlap area
    intersections["overlap_area"] = intersections.geometry.area

    # For each park, keep the vegetation class with largest overlap area
    dominant = (
        intersections.sort_values(["PARK_NAME", "overlap_area"], ascending=[True, False])
        .drop_duplicates(subset=["PARK_NAME"])
        [["PARK_NAME", "VEGDESC"]]
        .rename(columns={"VEGDESC": "dominant_vegetation"})
    )

    # Merge back onto parks
    result = parks.merge(dominant, on="PARK_NAME", how="left")
    result["dominant_vegetation"] = result["dominant_vegetation"].fillna("Unknown")

# -----------------------------
# Keep only requested columns
# -----------------------------
result = result[["PARK_NAME", "dominant_vegetation", "geometry"]].copy()

# -----------------------------
# Save derived dataset
# -----------------------------
result_wgs84 = result.to_crs("EPSG:4326")
result_wgs84.to_file(output_geojson, driver="GeoJSON")

# -----------------------------
# Build map
# -----------------------------
unique_veg = sorted(result_wgs84["dominant_vegetation"].dropna().unique().tolist())
n = max(len(unique_veg), 1)

# Generate categorical colors
cmap = plt.get_cmap("tab20", n)
color_map = {
    veg_name: mcolors.to_hex(cmap(i))
    for i, veg_name in enumerate(unique_veg)
}

# Center map
centroids = result_wgs84.geometry.centroid
center_lat = centroids.y.mean()
center_lon = centroids.x.mean()

m = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="CartoDB positron")

def style_function(feature):
    veg_name = feature["properties"]["dominant_vegetation"]
    return {
        "fillColor": color_map.get(veg_name, "#999999"),
        "color": "black",
        "weight": 0.6,
        "fillOpacity": 0.7,
    }

tooltip = folium.GeoJsonTooltip(
    fields=["PARK_NAME", "dominant_vegetation"],
    aliases=["Park", "Dominant vegetation"],
    localize=True,
    sticky=False
)

folium.GeoJson(
    result_wgs84,
    style_function=style_function,
    tooltip=tooltip,
    name="Dominant vegetation by park"
).add_to(m)

# -----------------------------
# Add legend
# -----------------------------
legend_items = "".join(
    f"""
    <div style="display:flex; align-items:center; margin-bottom:4px;">
        <span style="
            display:inline-block;
            width:14px;
            height:14px;
            background:{color_map[v]};
            border:1px solid #333;
            margin-right:8px;
        "></span>
        <span>{v}</span>
    </div>
    """
    for v in unique_veg
)

legend_html = f"""
{{% macro html(this, kwargs) %}}
<div style="
    position: fixed;
    bottom: 30px;
    left: 30px;
    z-index: 9999;
    background: white;
    border: 2px solid #444;
    border-radius: 6px;
    padding: 10px 12px;
    font-size: 12px;
    max-height: 300px;
    overflow-y: auto;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
">
    <div style="font-weight:bold; margin-bottom:8px;">Dominant vegetation</div>
    {legend_items}
</div>
{{% endmacro %}}
"""

legend = MacroElement()
legend._template = Template(legend_html)
m.get_root().add_child(legend)

folium.LayerControl().add_to(m)
m.save(output_html)

print(f"Saved dataset: {output_geojson}")
print(f"Saved map: {output_html}")