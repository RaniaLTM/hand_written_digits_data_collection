## Handwritten Digit Data Collection

Simple web interface (no authentication) for collecting handwritten digit samples (0–9).  
Users draw a digit on a canvas, choose the corresponding label, and submit; the server stores PNG images plus a CSV file with metadata.

### 1. Project structure

- **`app.py`**: Flask application (serves the page and receives submissions).
- **`templates/index.html`**: Main page with drawing canvas and controls.
- **`static/style.css`**: Basic modern styling.
- **`static/script.js`**: Canvas drawing logic and submission via `fetch`.
- **`data/images/`**: Generated at runtime; contains submitted digit PNGs.
- **`data/labels.csv`**: Generated at runtime; one line per sample: `filename,label,timestamp,ip`.
- **`data/digits.db`**: SQLite database created at runtime; table `digit_samples` stores all submissions.

### 2. Requirements

- Python 3.9+ (3.10/3.11 also fine)
- Pip

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Run the app (development)

From the project root (where `app.py` is located):

```bash
python app.py
```

By default the app runs on `http://127.0.0.1:5000/`.

Open that URL in a browser and you will see:

- A square dark canvas where you can draw a digit with mouse or touch.
- A dropdown to select the correct digit (0–9).
- **Clear** and **Submit sample** buttons.

Each successful submission will:

- Save a PNG file in `data/images/` named like `digit_5_20251204T123456789012Z.png`.
- Append a row to `data/labels.csv` with filename, label, timestamp (UTC), and IP address (for backup / quick viewing).
- Insert a row into the **SQLite database** `data/digits.db` in the table `digit_samples`:
  - `id` (auto-increment)
  - `filename`
  - `label`
  - `timestamp` (UTC, `datetime`)
  - `ip`

To quickly inspect the database (for example using the CLI):

```bash
sqlite3 data/digits.db "SELECT id, filename, label, timestamp, ip FROM digit_samples LIMIT 10;"
```

### 4. Basic production deployment (optional)

You can also run it with Gunicorn behind a reverse proxy (Linux server example):

```bash
pip install -r requirements.txt
gunicorn -w 3 -b 0.0.0.0:8000 "app:app"
```

Then point Nginx/Apache to `http://127.0.0.1:8000`.


