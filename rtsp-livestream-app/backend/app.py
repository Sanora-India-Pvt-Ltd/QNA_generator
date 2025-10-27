"""
Flask backend for RTSP -> HLS streaming + overlays CRUD.

Requirements (backend/requirements.txt)
--------------------------------------
Flask
pymongo
flask-cors
python-dotenv   # optional, for local env loading

Assumptions
-----------
- ffmpeg_manager.py exists in same folder and exposes FFmpegManager
- A 'streams' directory will be used to store HLS output (created automatically)
- MongoDB connection URI in env var MONGO_URI (default: mongodb://localhost:27017/rtsp_app)
"""

import os
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from ffmpeg_manager import FFmpegManager

# ------------- Configuration -------------
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/rtsp_app")
STREAMS_DIR = os.environ.get("STREAMS_DIR", os.path.join(os.getcwd(), "streams"))
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 5000))
DEBUG = os.environ.get("DEBUG", "True").lower() in ("1", "true", "yes")

# ------------- Flask App -------------
app = Flask(__name__, static_folder=STREAMS_DIR)
CORS(app)  # For frontend dev; lock down in production

# ------------- MongoDB -------------
client = MongoClient(MONGO_URI)
db = client.get_default_database()

# ------------- FFmpeg Manager -------------
ffm = FFmpegManager(base_dir=STREAMS_DIR)

# ------------- Helpers -------------
def objid(id_str):
    try:
        return ObjectId(id_str)
    except Exception:
        return None

def overlay_with_id(doc):
    if not doc:
        return None
    doc['_id'] = str(doc['_id'])
    return doc

def stream_with_id(doc):
    if not doc:
        return None
    doc['_id'] = str(doc['_id'])
    return doc

# ------------- Health Check -------------
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "db": True, "streams_dir": STREAMS_DIR})

# ------------- Streams Endpoints -------------
@app.route('/api/streams', methods=['POST'])
def create_stream():
    """Start converting an RTSP URL to HLS and create a stream record."""
    try:
        data = request.get_json(force=True)
        rtsp_url = data.get('rtsp_url')
        name = data.get('name', 'stream')

        if not rtsp_url:
            return jsonify({"error": "rtsp_url is required"}), 400

        stream_doc = {
            "rtsp_url": rtsp_url,
            "name": name,
            "status": "starting",
            "created_at": datetime.utcnow()
        }
        res = db.streams.insert_one(stream_doc)
        stream_id = str(res.inserted_id)

        # Start ffmpeg
        try:
            ffm.start_stream(stream_id, rtsp_url)
            db.streams.update_one({"_id": ObjectId(stream_id)}, {"$set": {"status": "running"}})
        except Exception as e:
            db.streams.update_one(
                {"_id": ObjectId(stream_id)},
                {"$set": {"status": "error", "error": str(e)}}
            )
            return jsonify({"error": "failed to start ffmpeg", "details": str(e)}), 500

        hls_path = f"/streams/{stream_id}/index.m3u8"
        return jsonify({"stream_id": stream_id, "hls_path": hls_path}), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "internal_server_error", "details": str(e)}), 500

@app.route('/api/streams', methods=['GET'])
def list_streams():
    docs = [stream_with_id(d) for d in db.streams.find({})]
    return jsonify(docs)

@app.route('/api/streams/<stream_id>', methods=['GET'])
def get_stream(stream_id):
    _id = objid(stream_id)
    if not _id:
        return jsonify({"error": "invalid id"}), 400
    doc = db.streams.find_one({"_id": _id})
    if not doc:
        return jsonify({"error": "not_found"}), 404
    return jsonify(stream_with_id(doc))

@app.route('/api/streams/<stream_id>', methods=['DELETE'])
def stop_stream(stream_id):
    _id = objid(stream_id)
    if not _id:
        return jsonify({"error": "invalid id"}), 400
    found = db.streams.find_one({"_id": _id})
    if not found:
        return jsonify({"error": "not_found"}), 404

    ok = ffm.stop_stream(stream_id)
    db.streams.update_one({"_id": _id}, {"$set": {"status": "stopped"}})
    return jsonify({"stopped": ok})

# ------------- Overlays Endpoints -------------
@app.route('/api/streams/<stream_id>/overlays', methods=['POST'])
def create_overlay(stream_id):
    _id = objid(stream_id)
    if not _id:
        return jsonify({"error": "invalid stream id"}), 400

    body = request.get_json(force=True)
    overlay = {
        "stream_id": str(stream_id),
        "type": body.get("type", "text"),
        "content": body.get("content", ""),
        "x": int(body.get("x", 10)),
        "y": int(body.get("y", 10)),
        "width": int(body.get("width", 100)),
        "height": int(body.get("height", 40)),
        "z": int(body.get("z", 10)),
        "created_at": datetime.utcnow()
    }
    res = db.overlays.insert_one(overlay)
    overlay['_id'] = str(res.inserted_id)
    return jsonify(overlay), 201

@app.route('/api/streams/<stream_id>/overlays', methods=['GET'])
def list_overlays(stream_id):
    _id = objid(stream_id)
    if not _id:
        return jsonify({"error": "invalid stream id"}), 400
    docs = list(db.overlays.find({"stream_id": str(stream_id)}))
    return jsonify([overlay_with_id(d) for d in docs])

@app.route('/api/overlays/<overlay_id>', methods=['GET'])
def get_overlay(overlay_id):
    _id = objid(overlay_id)
    if not _id:
        return jsonify({"error": "invalid overlay id"}), 400
    doc = db.overlays.find_one({"_id": _id})
    if not doc:
        return jsonify({"error": "not_found"}), 404
    return jsonify(overlay_with_id(doc))

@app.route('/api/overlays/<overlay_id>', methods=['PUT'])
def update_overlay(overlay_id):
    _id = objid(overlay_id)
    if not _id:
        return jsonify({"error": "invalid overlay id"}), 400
    body = request.get_json(force=True)
    allowed = {"content", "x", "y", "width", "height", "z", "type"}
    updates = {k: (int(v) if k in ("x","y","width","height","z") else v)
               for k,v in body.items() if k in allowed}
    if not updates:
        return jsonify({"error": "no_valid_fields_provided"}), 400
    db.overlays.update_one({"_id": _id}, {"$set": updates})
    doc = db.overlays.find_one({"_id": _id})
    return jsonify(overlay_with_id(doc))

@app.route('/api/overlays/<overlay_id>', methods=['DELETE'])
def delete_overlay(overlay_id):
    _id = objid(overlay_id)
    if not _id:
        return jsonify({"error": "invalid overlay id"}), 400
    db.overlays.delete_one({"_id": _id})
    return jsonify({"deleted": overlay_id})

# ------------- Serve HLS files -------------
@app.route('/streams/<stream_id>/<path:filename>')
def serve_stream_file(stream_id, filename):
    dirpath = os.path.join(STREAMS_DIR, stream_id)
    file_path = os.path.join(dirpath, filename)
    if not os.path.exists(file_path):
        return abort(404)
    return send_from_directory(dirpath, filename, conditional=True)

# ------------- Simple Landing -------------
@app.route('/')
def index():
    return jsonify({"name": "rtsp-hls-backend", "version": "1.0", "docs": "/api/health"})

# ------------- Graceful Shutdown -------------
@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    try:
        for sid in list(ffm.procs.keys()):
            ffm.stop_stream(sid)
        return jsonify({"stopped_all": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------- Run -------------
if __name__ == '__main__':
    os.makedirs(STREAMS_DIR, exist_ok=True)
    print(f"Starting app on {HOST}:{PORT} (debug={DEBUG}). Streams dir: {STREAMS_DIR}")
    app.run(host=HOST, port=PORT, debug=DEBUG)
