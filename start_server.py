#!/usr/bin/env python3
"""
Start-skript för Prom webserver
Kör med: python start_server.py
"""

import uvicorn
import sys
from pathlib import Path

# Lägg till prom i path så vi kan importera app
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    print("🚀 Startar Prom webserver...")
    print("📍 API dokumentation: http://localhost:8000/docs")
    print("🌐 Frontend (när byggd): http://localhost:8000")
    print("⏹️  Tryck Ctrl+C för att avsluta\n")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 