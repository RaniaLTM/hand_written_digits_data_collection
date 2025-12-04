from flask import Flask, render_template, request, jsonify
import os
import base64
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, create_engine
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

