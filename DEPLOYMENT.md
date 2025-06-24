# Prom Analytics - Render Deployment Guide

## Vad som sker nu:

### ✅ Web Service (run_combined.py)
- **Web Server**: Serverar frontend + API på port som Render tilldelar
- **Kontinuerlig Scraping**: Hämtar nya hands var 10:e minut i bakgrunden
- **Graceful Shutdown**: Hanterar SIGTERM för säker avstängning
- **Auto-restart**: Om scraping kraschar, startar den om automatiskt

### ⚙️ Optimeringar för Render:
- **Threading** istället för multiprocessing (bättre för containers)
- **Längre intervall** (10 min) för att spara CPU/resurser
- **Skippar rensning** (`--no-clean`) för snabbare start
- **Skippar processing scripts** (`--no-scripts`) för lägre CPU-användning
- **Större disk** (10GB) för databastillväxt
- **Unbuffered Python** för bättre logging

## Deployment Steps:

### 1. Commit & Push dina ändringar:
```bash
git add .
git commit -m "Optimized for Render with continuous scraping"
git push origin main
```

### 2. På Render Dashboard:
- Gå till din service
- Klicka "Manual Deploy" > "Deploy latest commit"

### 3. Övervaka deployment:
- **Build logs**: Kontrollera att frontend byggs korrekt
- **Deploy logs**: Se till att både webserver och scraping startar
- **Live logs**: Följ real-time aktivitet

## Förväntade Log-meddelanden:

```
🚀 Startar Prom...
🌐 Render deployment - frontend redan byggd
🔄 Aktiverar kontinuerlig scraping på Render
🔄 Startar scraping-thread...
✅ Scraping-thread startad - hämtar nya hands kontinuerligt
🌐 Startar webserver...
🔄 Startar scraping-thread...
🌐 Render miljö - längre intervall för scraping (10 min)
```

## Monitoring:

### Health Check:
- URL: `https://your-app.onrender.com/health`
- Ska returnera: `{"status": "ok", "timestamp": "..."}`

### Database Growth:
- Databasen växer kontinuerligt med nya hands
- Kontrollera att disk usage inte närmar sig 10GB

### Performance:
- CPU bör vara låg (scraping var 10:e minut)
- Memory usage stabil
- Inga restarter av service

## Troubleshooting:

### Om scraping slutar fungera:
1. Kolla logs för fel meddelanden
2. Scraping-thread försöker auto-restart
3. Om det failar helt, redeploya servicen

### Om databasen blir full:
1. Öka disk size i render.yaml
2. Eller implementera data retention (rensa gamla hands)

### Om CPU blir hög:
1. Öka sleep interval i run_combined.py (rad 71)
2. Från 600 sekunder till 900+ sekunder

## Nästa steg:
1. Deploy och testa
2. Övervaka i 24h för stabilitet  
3. Optimera intervaller baserat på data-behov
4. Lägg till alerts för disk usage

## URL:er efter deployment:
- **Huvudsida**: `https://your-app.onrender.com`
- **API docs**: `https://your-app.onrender.com/docs`
- **Health check**: `https://your-app.onrender.com/health` 