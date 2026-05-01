# Frame-Level Early Deepfake Video Detection

Deepfake Defender is a Final Year Project (FYP) web application for detecting manipulated or AI-generated video content at frame level. It combines a Flask backend, a ConvNeXt-based deepfake classification model, MTCNN face detection, frame-level analysis, CSV reporting, suspicious-frame thumbnails, and manipulated segment extraction.

The project is designed as a practical AI web app rather than a simple demo. It includes authentication, admin controls, analysis history, password recovery, structured backend modules, and a professional frontend for early and full video analysis.

## Project Summary

Deepfake videos can be difficult to identify manually because manipulated regions may appear only in some frames or short time segments. This system analyzes video frames, detects faces, runs a deep learning model on extracted face crops, and produces an explainable result with frame-level evidence.

The final decision policy is conservative:

- A video is considered fake only when at least one 1-second window contains fake frames greater than or equal to 50% of that second's FPS.
- Example: for a 30 FPS video, at least 15 fake frames in a single second are required.
- Scattered fake frames across the video do not automatically make the full video fake.
- Suspicious frames are shown for evidence but are not counted as fake frames in the final per-second rule.

## Key Features

- Early deepfake detection for faster results.
- Full video processing for complete analysis.
- MTCNN-based face detection.
- ConvNeXt deep learning model inference.
- Frame-level fake/real confidence scores.
- Per-frame CSV export.
- Suspicious frame thumbnail generation.
- Manipulated segment extraction using FFmpeg.
- Merged manipulated-only video output when fake segments are detected.
- Live processing stages in the UI.
- User signup, login, logout, and profile page.
- Password reset token flow with development fallback when SMTP is not configured.
- Admin dashboard for users, usage history, sessions, IP usage, and logs.
- Analysis history storage in SQLite.
- Clean modular Flask backend structure.

## Screens and Pages

- `index.html` - Main AI analysis dashboard.
- `login.html` - User login.
- `signup.html` - User registration.
- `forgot-password.html` - Password recovery request.
- `reset-password.html` - Password reset form.
- `profile.html` - User profile and analysis history.
- `admin.html` - Admin dashboard.
- `subscription.html` - Future-ready pricing/subscription page.

## Backend Architecture

```text
backend/
  app.py
  __init__.py
  config.py
  extensions.py
  models.py
  routes/
    admin.py
    analyze.py
    auth.py
    pages.py
  services/
    analysis_service.py
    auth_service.py
    email_service.py
    job_service.py
    user_service.py
  utils/
    decorators.py
    helpers.py
    validators.py
  database/
    __init__.py
```

## Detection Pipeline

The analysis flow is:

1. Upload video.
2. Extract frames with OpenCV.
3. Convert frames from BGR to RGB.
4. Detect face regions using MTCNN.
5. Crop face regions.
6. Resize and normalize using Albumentations.
7. Run ConvNeXt model inference.
8. Store per-frame predictions.
9. Apply per-second fake-frame decision rule.
10. Generate CSV report.
11. Generate thumbnails for suspicious/fake frames.
12. Extract manipulated clips for full-video mode.
13. Return JSON response to the frontend.

## Final Decision Rule

The final result is based on a per-second threshold:

```text
required_fake_frames = ceil(video_fps * 0.50)
```

Examples:

- 30 FPS video: fake if any second has 15 or more fake frames.
- 24 FPS video: fake if any second has 12 or more fake frames.
- 60 FPS video: fake if any second has 30 or more fake frames.

This rule reduces false positives where a real video may contain a small number of incorrectly classified frames.

## Tech Stack

- Python
- Flask
- Flask-SQLAlchemy
- SQLite
- PyTorch
- TorchVision
- ConvNeXt via `timm`
- MTCNN via `facenet-pytorch`
- OpenCV
- Albumentations
- FFmpeg
- HTML, CSS, JavaScript
- Chart.js

## Database Tables

The application creates the following tables:

- `users`
- `sessions`
- `analysis_history`
- `password_reset_tokens`
- `admin_logs`
- `ip_usage`
- `subscription_plans`
- `user_subscriptions`

SQLite database is created locally under:

```text
instance/deepfake_defender.db
```

## Authentication

The app supports:

- Signup
- Login
- Logout
- Profile page
- Password reset token flow
- Admin account

Passwords are stored using secure Werkzeug password hashing.

Default admin account:

```text
Email: admin@deepfakedefender.local
Password: Admin@12345
```

For production, change this using environment variables before first run:

```powershell
$env:DDEFENDER_ADMIN_EMAIL="your-admin-email@example.com"
$env:DDEFENDER_ADMIN_PASSWORD="YourStrongPassword123"
```

## Google Login

Google login has a safe placeholder endpoint:

```text
/api/auth/google/start
```

Normal email/password login works fully. Google OAuth can be connected later using free Google OAuth credentials.

## Important Model File Note

The trained checkpoint is required at project root:

```text
model_convnext.pth
```

This file is not included in the GitHub repository because it is large and GitHub LFS quota was exceeded during upload. To run inference, place your trained `model_convnext.pth` file in the same folder as `app.py`.

Expected location:

```text
Frame-Level-Early-Deepfake-Video-Detection/
  app.py
  model_convnext.pth
```

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/myousaf179/Frame-Level-Early-Deepfake-Video-Detection.git
cd Frame-Level-Early-Deepfake-Video-Detection
```

### 2. Create Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Upgrade Build Tools

```bash
python -m pip install --upgrade pip setuptools wheel
```

### 4. Install PyTorch

CPU-only install:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

If you have a CUDA GPU, install the matching PyTorch build from the official PyTorch website.

### 5. Install Project Dependencies

```bash
pip install -r requirements.txt
```

### 6. Install FFmpeg

Windows:

```powershell
winget install ffmpeg
```

Linux:

```bash
sudo apt install ffmpeg
```

macOS:

```bash
brew install ffmpeg
```

Check installation:

```bash
ffmpeg -version
```

### 7. Add Model Checkpoint

Copy `model_convnext.pth` into the project root.

## Running the App

```bash
python app.py
```

Open in browser:

```text
http://127.0.0.1:5000/
```

## Main API Endpoints

### Analysis

```text
POST /analyze
POST /analyze_full
POST /analyze_frame
```

### Live Analysis Jobs

```text
POST /api/analyze/jobs
GET  /api/analyze/jobs/<job_id>
GET  /api/analyze/jobs/<job_id>/events
```

### Auth

```text
GET  /api/auth/me
POST /api/auth/signup
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/profile
PATCH /api/auth/profile
POST /api/auth/forgot-password
POST /api/auth/reset-password
```

### Admin

```text
GET /api/admin/summary
GET /api/admin/users
GET /api/admin/history
GET /api/admin/sessions
GET /api/admin/ip-usage
GET /api/admin/logs
```

## Analysis Output

The app can generate:

- Final fake/real decision.
- Summary text.
- Frame counts.
- Fake frame count.
- Real frame count.
- Suspicious frame count.
- Confidence arrays.
- CSV report.
- Suspicious thumbnails.
- Manipulated video segments.
- Merged manipulated-only clip.

Generated runtime files are stored under:

```text
uploads/
outputs/
```

These folders are ignored by Git.

## Environment Variables

Optional variables:

```text
DDEFENDER_SECRET_KEY
DDEFENDER_DEBUG
DDEFENDER_DATABASE_URI
DDEFENDER_MAX_UPLOAD_MB
DDEFENDER_ADMIN_EMAIL
DDEFENDER_ADMIN_PASSWORD
DDEFENDER_ADMIN_NAME
DDEFENDER_SMTP_HOST
DDEFENDER_SMTP_PORT
DDEFENDER_SMTP_USER
DDEFENDER_SMTP_PASSWORD
DDEFENDER_SMTP_FROM
DDEFENDER_SMTP_TLS
DDEFENDER_PUBLIC_URL
DDEFENDER_GOOGLE_CLIENT_ID
DDEFENDER_GOOGLE_CLIENT_SECRET
```

## Password Recovery

If SMTP is configured, password reset links are sent by email.

If SMTP is not configured, the API returns a development reset link for testing. This makes FYP testing easier without needing a paid email service.

## Testing Checklist

Recommended manual checks:

- Signup flow.
- Login flow.
- Logout flow.
- Password recovery.
- Profile page.
- Admin login.
- Admin users list.
- Video upload.
- Early detection.
- Full video processing.
- CSV download.
- Thumbnail display.
- Segment extraction.
- Broken links.
- Browser console errors.
- Server errors.

Basic backend syntax check:

```bash
python -m compileall app.py backend
```

## Known Limitations

- The trained model checkpoint is not included in the GitHub repo.
- Google OAuth is prepared as a placeholder and needs credentials to be completed.
- Subscription billing UI is future-ready but payment checkout is not connected.
- Accuracy depends on the quality and training data of the model checkpoint.
- FFmpeg is required for manipulated segment extraction.

## Project Purpose

This project was built as a Final Year Project to demonstrate practical frame-level deepfake detection with a usable web application interface. It focuses on explainability, evidence generation, and a clear user workflow for video authenticity analysis.

## Repository

GitHub:

```text
https://github.com/myousaf179/Frame-Level-Early-Deepfake-Video-Detection
```

