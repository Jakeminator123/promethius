#!/usr/bin/env bash
# Build script for Render
set -e

echo "🐍 Installing Python dependencies..."
pip install -r requirements.txt

echo "📦 Building frontend..."
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build

echo "✅ Build complete!" 