from flask import Flask, render_template, request, jsonify, Response, send_file, url_for
import os
import base64
from datetime import datetime
import csv
from io import StringIO, BytesIO
import zipfile

from sqlalchemy import Column, DateTime, Integer, String, create_engine, select
from sqlalchemy.orm import declarative_base, Session

app = Flask(__name__)

# Directory to store collected samples
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
METADATA_FILE = os.path.join(DATA_DIR, "labels.csv")
DB_PATH = os.path.join(DATA_DIR, "digits.db")
DB_URL = f"sqlite:///{DB_PATH}"

os.makedirs(DATA_DIR, exist_ok=True)

engine = create_engine(DB_URL, echo=False, future=True)
Base = declarative_base()


class DigitSample(Base):
    __tablename__ = "digit_samples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False)
    label = Column(String(1), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    ip = Column(String, nullable=True)


def ensure_storage():
    os.makedirs(IMAGES_DIR, exist_ok=True)
    if not os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            f.write("filename,label,timestamp,ip\n")

    # Ensure database and tables exist
    Base.metadata.create_all(engine)


@app.route("/")
def index():
    ensure_storage()
    return render_template("index.html")


@app.route("/api/submit", methods=["POST"])
def submit():
    ensure_storage()
    data = request.get_json(force=True, silent=True) or {}
    label = data.get("label")
    image_data = data.get("image")

    if label is None or label not in [str(i) for i in range(10)]:
        return jsonify({"status": "error", "message": "Invalid or missing label"}), 400

    if not image_data or not isinstance(image_data, str) or not image_data.startswith("data:image/png;base64,"):
        return jsonify({"status": "error", "message": "Invalid image data"}), 400

    # Strip the header and decode
    try:
        header, b64data = image_data.split(",", 1)
        image_bytes = base64.b64decode(b64data)
    except Exception:
        return jsonify({"status": "error", "message": "Failed to decode image"}), 400

    now = datetime.utcnow()
    timestamp_str = now.strftime("%Y%m%dT%H%M%S%fZ")
    filename = f"digit_{label}_{timestamp_str}.png"
    file_path = os.path.join(IMAGES_DIR, filename)

    with open(file_path, "wb") as img_file:
        img_file.write(image_bytes)

    # Log metadata to CSV (optional, keeps previous behavior)
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    with open(METADATA_FILE, "a", encoding="utf-8") as f:
        f.write(f"{filename},{label},{timestamp_str},{ip}\n")

    # Store in database for real-time structured storage
    with Session(engine) as session:
        sample = DigitSample(
            filename=filename,
            label=label,
            timestamp=now,
            ip=ip,
        )
        session.add(sample)
        session.commit()

    return jsonify({"status": "ok", "filename": filename})


@app.route("/api/stats", methods=["GET"])
def stats():
    """
    Simple endpoint to check that data is being stored correctly.
    Returns total number of samples and up to 10 most recent.
    """
    base_url = request.url_root.rstrip("/")
    with Session(engine) as session:
        all_ids = [row.id for row in session.scalars(select(DigitSample.id))]
        total = len(all_ids)
        recent = []
        for sample in session.scalars(
            select(DigitSample).order_by(DigitSample.id.desc()).limit(10)
        ):
            recent.append(
                {
                    "id": sample.id,
                    "filename": sample.filename,
                    "label": sample.label,
                    "timestamp": sample.timestamp.isoformat() if sample.timestamp else None,
                    "ip": sample.ip,
                    "image_url": f"{base_url}/api/images/{sample.filename}",
                }
            )

    return jsonify({"total": total, "recent": recent})


@app.route("/view", methods=["GET"])
def view_data():
    """Simple HTML page to view all collected images from your machine."""
    ensure_storage()
    return render_template("view.html")


@app.route("/api/images/<filename>", methods=["GET"])
def serve_image(filename):
    """Serve individual image files so you can view them in browser."""
    file_path = os.path.join(IMAGES_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "Image not found"}), 404
    return send_file(file_path, mimetype="image/png")


@app.route("/api/export/json", methods=["GET"])
def export_json():
    """Return all samples as JSON with image URLs so you can view them."""
    base_url = request.url_root.rstrip("/")
    with Session(engine) as session:
        items = []
        for sample in session.scalars(select(DigitSample).order_by(DigitSample.id)):
            items.append(
                {
                    "id": sample.id,
                    "filename": sample.filename,
                    "label": sample.label,
                    "timestamp": sample.timestamp.isoformat() if sample.timestamp else None,
                    "ip": sample.ip,
                    "image_url": f"{base_url}/api/images/{sample.filename}",
                }
            )
    return jsonify(items)


@app.route("/api/export/csv", methods=["GET"])
def export_csv():
    """Return all samples as a CSV file download."""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "filename", "label", "timestamp", "ip"])

    with Session(engine) as session:
        for sample in session.scalars(select(DigitSample).order_by(DigitSample.id)):
            writer.writerow(
                [
                    sample.id,
                    sample.filename,
                    sample.label,
                    sample.timestamp.isoformat() if sample.timestamp else "",
                    sample.ip or "",
                ]
            )

    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=digit_samples.csv"},
    )


@app.route("/api/export/images", methods=["GET"])
def export_images():
    """Download all images as a ZIP file to your machine."""
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        if os.path.exists(IMAGES_DIR):
            for filename in os.listdir(IMAGES_DIR):
                if filename.endswith(".png"):
                    file_path = os.path.join(IMAGES_DIR, filename)
                    zip_file.write(file_path, filename)
    
    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="digit_images.zip",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

