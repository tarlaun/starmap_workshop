#!/usr/bin/env python3
"""
serve_map.py — Starmap Workshop: Build tiles and serve the map.

Builds a Starlet MVT tile pyramid from a GeoJSON file, then starts a local
Flask server and opens map.html in the browser.

Usage
-----
    python3 serve_map.py <input_geojson> <dataset_name>

Example
-------
    python3 serve_map.py Riverside_Parks_DominantVegetation.geojson Parks_DominantVeg
"""

import json
import sys
import threading
import time
import warnings
import webbrowser
from pathlib import Path

import starlet
from flask import Flask, Response, abort, jsonify, send_file

warnings.filterwarnings("ignore", category=FutureWarning)

DATASET_ROOT = Path("./datasets")
HOST = "127.0.0.1"
PORT = 8765
BUILD_ZOOM = 10
BUILD_THRESHOLD = 0

def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    input_data = sys.argv[1]
    dataset_name = sys.argv[2]
    outdir = DATASET_ROOT / dataset_name

    DATASET_ROOT.mkdir(parents=True, exist_ok=True)

    print(f"Building tiles for '{dataset_name}' ...")
    tile_result, mvt_result = starlet.build(
        input=input_data,
        outdir=str(outdir),
        num_tiles=40,
        zoom=BUILD_ZOOM,
        threshold=BUILD_THRESHOLD,
    )

    print(f"  rows:        {tile_result.total_rows}")
    print(f"  bbox:        {tile_result.bbox}")
    print(f"  zoom levels: {mvt_result.zoom_levels}")
    print(f"  tile count:  {mvt_result.tile_count}")

    bbox = list(tile_result.bbox) if tile_result.bbox is not None else None

    map_file = Path(__file__).resolve().parent / "map.html"
    if not map_file.exists():
        raise FileNotFoundError(f"map.html not found at {map_file}")

    app = Flask(__name__)

    @app.route("/")
    def index() -> Response:
        return Response(map_file.read_text(encoding="utf-8"), mimetype="text/html")

    @app.route("/config.json")
    def config():
        return jsonify({
            "dataset": dataset_name,
            "bbox": bbox,          # [minx, miny, maxx, maxy] in lon/lat
            "max_zoom": BUILD_ZOOM
        })

    @app.route("/datasets/<dataset>/mvt/<int:z>/<int:x>/<int:y>.mvt")
    def serve_mvt(dataset: str, z: int, x: int, y: int):
        # Prevent requests above built zoom from looking like mysterious failures.
        if z > BUILD_ZOOM:
            abort(404)

        tile_path = DATASET_ROOT / dataset / "mvt" / str(z) / str(x) / f"{y}.mvt"
        if not tile_path.exists():
            abort(404)

        return send_file(
            tile_path,
            mimetype="application/vnd.mapbox-vector-tile",
            conditional=True
        )

    thread = threading.Thread(
        target=lambda: app.run(host=HOST, port=PORT, debug=False, use_reloader=False),
        daemon=True,
    )
    thread.start()
    time.sleep(1.5)

    url = f"http://{HOST}:{PORT}/"
    print(f"\nOpening {url}")
    webbrowser.open(url)

    print("Server running — press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping.")


if __name__ == "__main__":
    main()