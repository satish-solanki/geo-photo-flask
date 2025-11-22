# app.py
from flask import Flask, request, jsonify, render_template, send_from_directory, url_for
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont
import os, io, hashlib, json, datetime, csv
from dateutil import parser as date_parser

UPLOAD_FOLDER = 'static/uploads'
DB_FILE = 'db.json'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
FONT_PATH = None
MAX_UPLOAD_SIZE = 10 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, 'r') as f:
            DB = json.load(f)
    except Exception:
        DB = {}
else:
    DB = {}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def compute_sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _parse_iso_timestamp(ts: str) -> str:
    if not ts:
        return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    try:
        dt = date_parser.parse(ts)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return ts

def burn_watermark(image_bytes: bytes, text_lines: list) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as im:
        base = im.convert('RGBA')
        width, height = base.size
        overlay = Image.new('RGBA', base.size, (0,0,0,0))
        draw = ImageDraw.Draw(overlay)
        font_size = max(12, width // 40)
        try:
            font = ImageFont.truetype(FONT_PATH, font_size) if FONT_PATH else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        padding = max(6, font_size // 4)
        line_heights = []
        for line in text_lines:
            bbox = draw.textbbox((0,0), line, font=font)
            h = bbox[3] - bbox[1]
            line_heights.append(h)
        total_text_height = sum(line_heights) + padding * (len(text_lines) - 1)
        rectangle_height = total_text_height + padding * 2
        rectangle_y = max(0, height - rectangle_height)
        draw.rectangle([(0, rectangle_y), (width, height)], fill=(0,0,0,140))
        y = rectangle_y + padding
        left_margin = padding
        for i, line in enumerate(text_lines):
            draw.text((left_margin, y), line, font=font, fill=(255,255,255,255))
            y += line_heights[i] + padding
        combined = Image.alpha_composite(base, overlay).convert('RGB')
        out_io = io.BytesIO()
        combined.save(out_io, format='JPEG', quality=85)
        return out_io.getvalue()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'photo' not in request.files:
        return jsonify({'error': 'no photo part'}), 400
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': 'no selected file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'file type not allowed'}), 400
    filename = secure_filename(file.filename)
    data = file.read()
    if not data:
        return jsonify({'error': 'empty file'}), 400
    lat = request.form.get('lat')
    lon = request.form.get('lon')
    timestamp_raw = request.form.get('timestamp')
    notes = request.form.get('notes') or ''
    ts_formatted = _parse_iso_timestamp(timestamp_raw) if timestamp_raw else datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    lines = [ts_formatted, f"Lat: {lat or 'N/A'} Lon: {lon or 'N/A'}"]
    if notes:
        lines.append(f"Notes: {notes}")
    try:
        watermarked = burn_watermark(data, lines)
    except Exception as e:
        return jsonify({'error': f'failed to process image: {e}'}), 500
    sha = compute_sha(watermarked)
    out_name = f"{sha[:12]}_{filename.rsplit('.',1)[0]}.jpg"
    out_path = os.path.join(app.config['UPLOAD_FOLDER'], out_name)
    with open(out_path, 'wb') as out:
        out.write(watermarked)
    DB[sha] = {
        'filename': out_name,
        'timestamp': ts_formatted,
        'lat': lat,
        'lon': lon,
        'notes': notes
    }
    with open(DB_FILE, 'w') as f:
        json.dump(DB, f, indent=2)
    return jsonify({'status': 'ok', 'sha': sha, 'url': url_for('uploaded_file', filename=out_name)})

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/gallery')
def gallery():
    items = []
    for sha, meta in DB.items():
        items.append({'sha': sha, **meta, 'url': url_for('uploaded_file', filename=meta['filename'])})
    return render_template('gallery.html', items=items)

@app.route('/verify', methods=['POST'])
def verify():
    if 'photo' not in request.files:
        return jsonify({'error': 'no photo part'}), 400
    file = request.files['photo']
    data = file.read()
    sha = compute_sha(data)
    found = sha in DB
    return jsonify({'sha': sha, 'found': found, 'record': DB.get(sha)})

@app.route('/export_csv')
def export_csv():
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['sha', 'filename', 'timestamp', 'lat', 'lon', 'notes'])
    for sha, meta in DB.items():
        cw.writerow([sha, meta.get('filename'), meta.get('timestamp'), meta.get('lat'), meta.get('lon'), meta.get('notes')])
    output = si.getvalue()
    return app.response_class(output, mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=geo_photos.csv'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
