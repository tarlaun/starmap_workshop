#!/usr/bin/env python3
from __future__ import annotations

import threading
import time
import warnings
import webbrowser
from pathlib import Path

import starlet
from flask import Flask, Response, abort, send_file

warnings.filterwarnings("ignore", category=FutureWarning)
# INPUT_DATA = "TIGER2018_COUNTY.geojson"
INPUT_DATA = "/Users/tarlan/Downloads/TIGER2018_COUNTY.geojson"
DATASET_ROOT = Path("./datasets")
DATASET_NAME = "TIGER2018_COUNTY"
OUTDIR = DATASET_ROOT / DATASET_NAME

HOST = "127.0.0.1"
PORT = 8765


def main() -> None:
    DATASET_ROOT.mkdir(parents=True, exist_ok=True)

    tile_result, mvt_result = starlet.build(
        input=INPUT_DATA,
        outdir=str(OUTDIR),
        num_tiles=40,
        zoom=7,
        threshold=0,
    )

    print("Tile build complete")
    print(f"  outdir:      {tile_result.outdir}")
    print(f"  num_files:   {tile_result.num_files}")
    print(f"  total_rows:  {tile_result.total_rows}")
    print(f"  bbox:        {tile_result.bbox}")

    print("\nMVT generation complete")
    print(f"  outdir:      {mvt_result.outdir}")
    print(f"  zoom_levels: {mvt_result.zoom_levels}")
    print(f"  tile_count:  {mvt_result.tile_count}")

    here = Path(__file__).resolve().parent
    map_file = here / "map.html"

    print("\nLooking for map file at:")
    print(map_file)
    print("Exists:", map_file.exists())

    if not map_file.exists():
        raise FileNotFoundError(f"map.html not found at {map_file}")

    app = Flask(__name__)

    @app.route("/")
    def demo() -> Response:
        html = map_file.read_text(encoding="utf-8")
        return Response(html, mimetype="text/html")

    @app.route("/tiles/<dataset>/mvt/<int:z>/<int:x>/<int:y>.mvt")
    def serve_mvt(dataset: str, z: int, x: int, y: int):
        tile_path = DATASET_ROOT / dataset / "mvt" / str(z) / str(x) / f"{y}.mvt"

        print(f"Requested tile: dataset={dataset}, z={z}, x={x}, y={y}")
        print(f"Resolved tile path: {tile_path}")

        if not tile_path.exists():
            abort(404, description=f"Tile not found: {tile_path}")

        return send_file(
            tile_path,
            mimetype="application/vnd.mapbox-vector-tile",
            conditional=True,
        )

    @app.route("/health")
    def health() -> Response:
        return Response("ok", mimetype="text/plain")

    def run_server() -> None:
        app.run(host=HOST, port=PORT, debug=False, use_reloader=False)

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    time.sleep(2)

    url = f"http://{HOST}:{PORT}/?dataset={DATASET_NAME}"
    print(f"\nOpening {url}")
    webbrowser.open(url)

    print("Server is running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping.")


if __name__ == "__main__":
    main()