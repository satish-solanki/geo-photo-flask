# GeoPhoto — Flask (Python) web app + tamper-checker

This repository contains a Flask app that captures photos from a browser (camera), accepts GPS from the browser, burns a visible watermark, stores images and metadata, and exposes a gallery and tamper verification endpoint.

## Quick start

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in your browser (use a phone for camera+GPS).

## Files
- app.py — Flask application
- templates/index.html — capture page
- templates/gallery.html — gallery page
- static/uploads — saved images (created at runtime)
- db.json — metadata (created at runtime)
- requirements.txt — Python deps
- tests/ — pytest tests

## How to deploy to GitHub
1. Create a new repository on GitHub.
2. Initialize git locally and push:
   ```bash
   git init
   git add .
   git commit -m "Initial commit — GeoPhoto Flask app"
   git branch -M main
   git remote add origin https://github.com/yourusername/yourrepo.git
   git push -u origin main
   ```

## Notes
- Remove the sample preview image if you don't want it in the repo.
- For production, secure the upload endpoint and use a real database.
