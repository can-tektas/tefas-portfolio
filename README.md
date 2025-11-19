# TEFAS Fund Portfolio Tracker

A Flask web application to track your TEFAS mutual fund portfolio using Google Sheets as a database and live data from TEFAS.

## Setup Instructions

### 1. Google Sheets API Setup
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project.
3. Enable **Google Sheets API** and **Google Drive API**.
4. Create a Service Account:
   - Go to **Credentials** > **Create Credentials** > **Service Account**.
   - Download the JSON key file.
   - Rename it to `credentials.json` and place it in this project's root directory.
5. **Important:** Open the JSON file, find the `client_email` address, and **share your Google Sheet** with that email address (give 'Editor' access).
6. Create a Google Sheet named `Portfolio`.
   - Rename the first sheet (tab) to `Sheet1` (default).
   - Add headers in the first row: `Code`, `Date`, `Quantity`, `Price`.

### 2. Local Installation
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python app.py
   ```
3. Open your browser at `http://127.0.0.1:5000`.

### 3. Deployment (Render/Railway)
1. **Repository:** Push this code to GitHub.
2. **Environment Variables:**
   - Instead of uploading `credentials.json`, copy its content.
   - Set an environment variable named `GOOGLE_CREDENTIALS` with the content of the JSON file on your hosting platform.
3. **Build Command:** `pip install -r requirements.txt`
4. **Start Command:** `gunicorn app:app`

## Project Structure
- `app.py`: Main Flask application.
- `templates/`: HTML files (Bootstrap 5).
- `static/`: Custom CSS.
- `requirements.txt`: Python dependencies.
