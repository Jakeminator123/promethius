#!/usr/bin/env python3
"""
Setup och kör Prom Analytics
Installerar dependencies och startar både backend och frontend
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def run_command(cmd, cwd=None):
    """Kör ett kommando och skriv ut output"""
    print(f"Kör: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0

def main():
    root = Path(__file__).parent
    frontend_dir = root / "frontend"
    
    print("🚀 Prom Analytics Setup & Run")
    print("=" * 50)
    
    # Kolla om npm finns
    if not run_command(["npm", "--version"]):
        print("❌ npm är inte installerat. Installera Node.js först!")
        print("   Ladda ner från: https://nodejs.org/")
        sys.exit(1)
    
    # Installera Python-dependencies
    print("\n📦 Installerar Python-dependencies...")
    if not run_command([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "python-multipart"]):
        print("❌ Kunde inte installera Python-dependencies")
        sys.exit(1)
    
    # Installera frontend-dependencies
    print("\n📦 Installerar frontend-dependencies...")
    os.chdir(frontend_dir)
    if not run_command(["npm", "install"]):
        print("❌ Kunde inte installera frontend-dependencies")
        sys.exit(1)
    os.chdir(root)
    
    print("\n✅ Installation klar!")
    print("\n🚀 Startar applikationen...")
    print("=" * 50)
    print("Backend: http://localhost:8000")
    print("Frontend: http://localhost:5173")
    print("API Docs: http://localhost:8000/docs")
    print("\nLogga in med: test/test")
    print("\nTryck Ctrl+C för att avsluta")
    print("=" * 50)
    
    # Starta backend och frontend parallellt
    try:
        # Backend process
        backend_proc = subprocess.Popen(
            [sys.executable, "start_server.py"],
            cwd=root
        )
        
        # Vänta lite så backend hinner starta
        time.sleep(2)
        
        # Frontend process
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir
        )
        
        # Vänta på att processer avslutas
        backend_proc.wait()
        frontend_proc.wait()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Avslutar...")
        backend_proc.terminate()
        frontend_proc.terminate()
        sys.exit(0)

if __name__ == "__main__":
    main() 