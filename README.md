# Starlet Workshop — Simple End-to-End Example

This project demonstrates a minimal pipeline for:

1. Preparing geospatial data  
2. Building vector tiles with Starlet  
3. Serving and visualizing them in a browser  

Everything runs using **just Python scripts** — no Jupyter notebook required.

---

## Requirements

- Python 3.10+
- Install dependencies:

```bash
pip install geopandas flask starlet datasketch mapbox-vector-tile pyproj flask-cors
```
---


## Step 1 — (Optional) Prepare Data

If starting from raw datasets (e.g., parks + vegetation types), run:
```bash
python3 data_comp.py \
  Riverside_Parks.geojson \
  Riverside_VegetationTypes.geojson \
  Riverside_Parks_DominantVegetation.geojson
```
This will:
- Compute dominant vegetation per park
- Output a clean GeoJSON
- Add a dominant_vegetation attribute

---

## Step 2 — Build Tiles + Serve Map

Run:
```bash
python3 serve_map.py Riverside_Parks_DominantVegetation.geojson Parks_DominantVeg
```
This script will:
1. Build a vector tile pyramid using Starlet  
2. Start a local Flask server  
3. Open the map automatically in your browser  

---

## Step 3 — View the Map

The browser will open automatically at:

http://127.0.0.1:8765/

---

## What Happens Internally

### Tile Generation

Starlet builds tiles into:

datasets/<dataset_name>/mvt/{z}/{x}/{y}.mvt

### Server Endpoints

| Endpoint | Purpose |
|--------|--------|
| / | Serves map.html |
| /config.json | Provides dataset + bbox + zoom |
| /datasets/.../*.mvt | Serves vector tiles |

---

## Common Issues

### Map shows nothing
- Check tiles exist:
  datasets/<dataset>/mvt/
- Ensure dataset is not empty  
- Check geometry validity  

---

### Many 404 tile requests
This is normal if:
- Requests fall outside dataset extent  
- Zoom exceeds built level (default: 10)  
---
