#!/usr/bin/env bash
set -e  # Exit on error

echo "Upgrading pip..."
python -m pip install --upgrade pip

echo "Installing core dependencies..."
pip install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn==0.27.0 \
    python-dotenv==1.0.0 \
    firebase-admin==6.6.0

echo "Installing Google Cloud dependencies..."
pip install --no-cache-dir \
    google-cloud-storage>=1.37.1,<3.0.0 \
    google-cloud-firestore==2.20.0

echo "Installing remaining dependencies..."
pip install --no-cache-dir -r requirements.txt

echo "Installation completed successfully!" 