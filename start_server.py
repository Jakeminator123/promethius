#!/usr/bin/env python3
"""
Start-skript för Prom webserver
Kör med: python start_server.py
"""

import uvicorn
import sys
import os
from pathlib import Path

# Lägg till prom i path så vi kan importera app
sys.path.insert(0, str(Path(__file__).parent))

# Create empty databases if they don't exist (on Render)
if os.environ.get("RENDER") == "true":
    from utils.paths import POKER_DB, HEAVY_DB
    import sqlite3
    
    # Create minimal databases if they don't exist
    for db_path in [POKER_DB, HEAVY_DB]:
        if not db_path.exists():
            print(f"📦 Creating empty database: {db_path}")
            # Ensure parent directory exists
            db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(db_path))
            conn.close()

if __name__ == "__main__":
    # Get port from environment variable (Render sets this) or default to 8000
    port = int(os.environ.get("PORT", 8000))
    
    # Check if running on Render
    is_render = os.environ.get("RENDER") == "true"
    
    print("🚀 Startar Prom webserver...")
    if is_render:
        print(f"🌐 Running on Render.com on port {port}")
    else:
        print(f"📍 API dokumentation: http://localhost:{port}/docs")
        print(f"🌐 Frontend (när byggd): http://localhost:{port}")
        print("⏹️  Tryck Ctrl+C för att avsluta\n")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=not is_render,  # Only reload in development
        log_level="info"
    ) 