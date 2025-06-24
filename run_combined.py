#!/usr/bin/env python3
"""
Kombinerat script som kör både webserver och scraping samtidigt
Inkluderar frontend-byggning för lokal utveckling (Render bygger i build-steget)
"""
import os
import sys
import subprocess
import threading
import time
import signal
from pathlib import Path

# Lägg till projektrot i path
sys.path.insert(0, str(Path(__file__).parent))

def build_frontend():
    """Bygger React frontend (bara för lokal utveckling)"""
    frontend_dir = Path(__file__).parent / "frontend"
    
    if not frontend_dir.exists():
        print("⚠️  Frontend directory not found - skipping build")
        return False
        
    print("🎨 Bygger React frontend...")
    
    try:
        # Change to frontend directory and build
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=frontend_dir,
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Frontend byggd framgångsrikt!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Frontend build misslyckades: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        
        # Try installing dependencies first
        print("🔄 Försöker installera npm dependencies...")
        try:
            subprocess.run(
                ["npm", "install"], 
                cwd=frontend_dir,
                check=True,
                capture_output=True,
                text=True
            )
            print("✅ npm install framgångsrik!")
            
            # Try building again
            print("🎨 Försöker bygga igen...")
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=frontend_dir,
                check=True,
                capture_output=True,
                text=True
            )
            print("✅ Frontend byggd framgångsrikt efter npm install!")
            return True
            
        except subprocess.CalledProcessError as install_error:
            print(f"❌ npm install misslyckades också: {install_error}")
            return False
            
    except FileNotFoundError:
        print("❌ npm hittades inte! Kontrollera att Node.js är installerat.")
        return False

def run_web_server():
    """Kör webservern"""
    print("🌐 Startar webserver...")
    subprocess.run([sys.executable, "start_server.py"])

def run_scraping_thread():
    """Kör main.py för kontinuerlig scraping i en separat thread"""
    print("🔄 Startar scraping-thread...")
    
    # Vänta lite så webservern och databaser hinner starta
    time.sleep(10)
    
    is_render = os.environ.get("RENDER") == "true"
    
    # Olika inställningar för Render vs lokal miljö
    if is_render:
        sleep_time = "600"  # 10 minuter mellan körningar på Render
        print("🌐 Render miljö - längre intervall för scraping (10 min)")
    else:
        sleep_time = "300"  # 5 minuter lokalt
        print("💻 Lokal miljö - kortare intervall för scraping (5 min)")
    
    # Kör main.py med optimerade inställningar
    try:
        subprocess.run([
            sys.executable, 
            "main.py", 
            "--no-clean",  # Skippa rensning för bättre prestanda
            "--sleep", sleep_time,
            # Kör alla scripts första gången för att bygga heavy_analysis.db
        ])
    except Exception as e:
        print(f"❌ Scraping-thread krashade: {e}")
        print("🔄 Försöker starta om scraping om 60 sekunder...")
        time.sleep(60)
        # Recursiv restart av scraping
        run_scraping_thread()

# Global variabel för att hålla koll på threads
scraping_thread = None
shutdown_event = threading.Event()

def signal_handler(signum, frame):
    """Hanterar graceful shutdown"""
    print(f"\n🛑 Fick signal {signum} - stänger av gracefully...")
    shutdown_event.set()
    
    if scraping_thread and scraping_thread.is_alive():
        print("⏹️  Väntar på att scraping-thread ska avslutas...")
        scraping_thread.join(timeout=10)
    
    sys.exit(0)

if __name__ == "__main__":
    print("🚀 Startar Prom...")
    
    # Sätt upp signal handlers för graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Kolla om vi kör på Render - skippa alltid frontend build där
    is_render = os.environ.get("RENDER") == "true"
    
    if is_render:
        print("🌐 Render deployment - frontend byggd av buildCommand")
        print("🚫 Skippar frontend build för att undvika dubbel-byggning")
    else:
        # Lokal utveckling - kolla om frontend redan finns
        frontend_dist_exists = (Path(__file__).parent / "frontend" / "dist").exists()
        
        if frontend_dist_exists:
            print("📁 Frontend dist/ finns redan - skippar rebuild")
        else:
            print("💻 Lokal utveckling - bygger frontend")
            frontend_built = build_frontend()
            if not frontend_built:
                print("⚠️  Frontend build misslyckades, men fortsätter ändå...")
                print("💡 API:et kommer fortfarande att fungera på /api/*")
    
    # Starta scraping i en separat thread (nu även på Render!)
    print("🔄 Startar scraping-thread...")
    scraping_thread = threading.Thread(target=run_scraping_thread, daemon=True)
    scraping_thread.start()
    print("✅ Scraping-thread startad - hämtar nya hands kontinuerligt")
    
    # Kör webserver i huvudprocessen (blockerar)
    try:
        print("🌐 Startar webserver...")
        run_web_server()
    except KeyboardInterrupt:
        print("\n⏹️  Avslutar gracefully...")
        signal_handler(signal.SIGINT, None) 