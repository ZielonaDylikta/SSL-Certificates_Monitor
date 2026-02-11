# 🔒 SSL Certificate Monitor with MS Teams Alerts

Simple, zero-dependency SSL certificate expiration checker with a premium dashboard and Microsoft Teams alerts.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![Dependencies](https://img.shields.io/badge/Dependencies-None-green)
![License](https://img.shields.io/badge/License-MIT-green)

<img width="1178" height="913" alt="ssl_cer_monitor" src="https://github.com/user-attachments/assets/19c9f330-4c16-4952-9a1f-058f4617d5b6" />

## ✨ Features

- ✅ Monitor unlimited websites simultaneously
- ✅ Parallel certificate checking with 10 threads (fast)
- ✅ Premium dark dashboard with smooth animations
- ✅ Microsoft Teams alerts via Workflows webhook
- ✅ Smart alert cooldown (once per day per site)
- ✅ Alert history persists across container restarts
- ✅ Health check endpoint for Docker monitoring
- ✅ Test endpoints with authentication & rate limiting
- ✅ Hot-reload sites and template without restart
- ✅ Zero external dependencies (Python stdlib only)
- ✅ Docker ready with docker-compose

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Deployment](#-deployment)
- [Configuration](#-configuration)
- [API Endpoints](#-api-endpoints)
- [Microsoft Teams Setup](#-microsoft-teams-setup)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [How It Works](#-how-it-works)
- [Troubleshooting](#-troubleshooting)

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose (recommended)
- OR Python 3.8+ (for standalone)
- Network access to monitored sites (port 443)
- Microsoft Teams (optional, for alerts)

### 1. Clone Repository

```bash
git clone https://github.com/ZielonaDylikta/SSL-Certificates_Monitor.git
cd SSL-Certificates_Monitor
```

### 2. Configure Sites to Monitor

Edit `sites.csv` and add your domains (one per line):

```csv
# My websites to monitor
google.com
github.com
mycompany.com
internal.mysite.com
```

### 3. Configure Environment Variables

Edit `docker-compose.yml` and set your configuration:

```yaml
environment:
  - TEAMS_WEBHOOK=https://your-teams-webhook-url
  - ALERT_DAYS=15
  - TEST_KEY=your-secret-key
```

### 4. Start the Application

```bash
docker compose up -d --build
```

### 5. Access Dashboard

Open your browser and navigate to:
```
http://localhost:7921
```

## 🐳 Deployment

### Docker Compose (Recommended)

```bash
# Build and start
docker compose up -d --build

# View logs
docker compose logs -f

# Stop
docker compose down

# Restart
docker compose restart

# Check status
docker compose ps
```

### Standalone Python

```bash
# Run directly
python certcheck.py

# With environment variables
TEAMS_WEBHOOK=https://your-webhook ALERT_DAYS=15 python certcheck.py
```

### Docker Only

```bash
# Build image
docker build -t certcheck .

# Run container
docker run -d \
  -p 7921:7921 \
  -v $(pwd)/sites.csv:/app/sites.csv \
  -v $(pwd)/template.html:/app/template.html \
  -v $(pwd)/data:/app/data \
  -e TEAMS_WEBHOOK=https://your-webhook \
  -e ALERT_DAYS=15 \
  -e TEST_KEY=mysecretkey \
  --name certcheck \
  certcheck
```

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TEAMS_WEBHOOK` | No | - | Microsoft Teams Workflows webhook URL for alerts |
| `ALERT_DAYS` | No | 15 | Alert threshold in days (certificates expiring within this period) |
| `TEST_KEY` | No | - | Secret key to protect test endpoints |

### Files

| File | Description | Hot-Reload |
|------|-------------|------------|
| `sites.csv` | List of domains to monitor (one per line) | ✅ Yes |
| `template.html` | Dashboard HTML template | ✅ Yes |
| `data/alerts_sent.json` | Alert history (auto-created) | - |

### Port Configuration

Default port: `7921`

To change the port, modify:
1. `certcheck.py` - Change `PORT = 7921`
2. `docker-compose.yml` - Change port mapping `"7921:7921"`
3. `Dockerfile` - Change `EXPOSE 7921`

## 📡 API Endpoints

### Dashboard
```bash
GET /
```
Web interface with certificate status visualization

### API Data
```bash
curl http://localhost:7921/api
```

Response:
```json
[
  {
    "site": "google.com",
    "expiry": "2025-04-15",
    "days": 89,
    "issuer": "Google Trust Services",
    "error": null
  }
]
```

### Health Check
```bash
curl http://localhost:7921/health
```

Response:
```json
{
  "status": "ok",
  "sites_total": 21,
  "sites_ok": 19,
  "sites_warning": 1,
  "sites_error": 1,
  "teams_configured": true,
  "alert_threshold": 15,
  "check_interval": 3600,
  "uptime_seconds": 86400,
  "timestamp": "2025-02-11T10:30:00+00:00"
}
```

### Test Webhook (Protected)
```bash
# With header
curl -H "X-Test-Key: mysecretkey123" http://localhost:7921/test-webhook

# With query parameter
curl http://localhost:7921/test-webhook?key=mysecretkey123
```

### Test Alert (Protected)
```bash
# With header
curl -H "X-Test-Key: mysecretkey123" http://localhost:7921/test-alert

# With query parameter
curl http://localhost:7921/test-alert?key=mysecretkey123
```

## 📢 Microsoft Teams Setup

### 1. Create Workflow Webhook

1. Open Microsoft Teams
2. Go to the channel where you want alerts
3. Click "..." → "Workflows"
4. Create a new workflow with "Post to a channel when a webhook request is received"
5. Copy the webhook URL

### 2. Configure Webhook

Add the webhook URL to `docker-compose.yml`:

```yaml
environment:
  - TEAMS_WEBHOOK=https://prod-xx.eastus.logic.azure.com:443/workflows/...
```

### 3. Test Connection

```bash
# Test webhook connectivity
curl -H "X-Test-Key: mysecretkey123" http://localhost:7921/test-webhook

# Send test alert
curl -H "X-Test-Key: mysecretkey123" http://localhost:7921/test-alert
```

### Teams Alert Example

```
┌──────────────────────────────────────────────────┐
│  🔒 SSL Certificate Alert                        │
│  2 certificates expiring within 15 days          │
│                                                  │
│  Site              │ Status        │ Expires     │
│  ──────────────────┼───────────────┼──────────   │
│  critical.com      │ 🔴 5d left    │ 2025-01-20  │
│  warning.com       │ 🟡 13d left   │ 2025-01-28  │
└──────────────────────────────────────────────────┘
```

## 📖 Usage

### Adding Sites

Edit `sites.csv` (changes are detected automatically):

```csv
# Production sites
example.com
api.example.com

# Development sites
dev.example.com
staging.example.com
```

### Monitoring Status

Access the dashboard at `http://localhost:7921` to see:
- Real-time certificate status
- Days until expiration
- Certificate issuer
- Visual status indicators
- Expiration timeline bars

### Status Levels

| Status | Days Left | Color | Teams Alert |
|--------|-----------|-------|-------------|
| 🟢 Healthy | > 30 | Green | No |
| 🟡 Soon | 16-30 | Yellow | Yes |
| 🟠 Warning | 8-15 | Orange | Yes |
| 🔴 Critical | 0-7 | Red (pulsing) | Yes |
| 🔴 Expired | < 0 | Dark red (pulsing) | Yes |
| ❌ Error | - | Gray | No |

### Alert Logic

| Condition | Action |
|-----------|--------|
| Cert > 15 days remaining | No alert |
| Cert ≤ 15 days, not alerted today | Send Teams alert |
| Cert ≤ 15 days, already alerted today | Skip (cooldown) |
| Next day, still expiring | Alert again |
| Container restart | Loads alert history, no duplicates |

## 📁 Project Structure

```
certcheck/
├── certcheck.py          # Main application (HTTP server + cert checker)
├── template.html         # Dashboard UI (dark theme with animations)
├── sites.csv             # Sites to monitor (editable, hot-reload)
├── data/                 # Persistent data (auto-created)
│   └── alerts_sent.json  # Alert history (auto-created)
├── Dockerfile            # Container image definition
├── docker-compose.yml    # Docker Compose configuration
└── README.md             # This file
```

## 🔧 How It Works

### Architecture

```
                    ┌──────────────┐
                    │  sites.csv   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  Check certs │ ← Every hour, parallel
                    │  (10 threads)│
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼───┐ ┌──────▼──────┐
       │  Dashboard  │ │ API  │ │ Teams Alert │
       │  :7921/     │ │ /api │ │ (if < 15d)  │
       └─────────────┘ └──────┘ └─────────────┘
```

### Certificate Check Cycle

1. Load sites from `sites.csv`
2. Check all certificates in parallel (10 threads)
3. Update dashboard data
4. Check if any cert expires within threshold (default: 15 days)
5. Send Teams alert (once per day per site)
6. Save alert history to disk
7. Wait 1 hour (3600 seconds)
8. Repeat

### Key Features

- **Parallel Processing**: Uses ThreadPoolExecutor with 10 workers for fast checking
- **Hot Reload**: Automatically detects changes to `sites.csv` and `template.html`
- **Alert Cooldown**: Prevents spam by alerting once per day per site
- **Persistent History**: Alert history survives container restarts
- **Health Monitoring**: Built-in health check endpoint for Docker
- **Zero Dependencies**: Uses only Python standard library

## 🔍 Troubleshooting

### Teams Alerts Not Working

```bash
# 1. Check webhook is configured
curl http://localhost:7921/health

# 2. Test webhook connection
curl http://localhost:7921/test-webhook?key=YOUR_TEST_KEY

# 3. Test full alert
curl http://localhost:7921/test-alert?key=YOUR_TEST_KEY

# 4. Check logs
docker compose logs -f | grep TEAMS
```

### Common Teams Errors

| Error | Solution |
|-------|----------|
| `TEAMS_WEBHOOK not set` | Add `TEAMS_WEBHOOK` to `docker-compose.yml` |
| `HTTP 404` | Webhook URL is wrong, recreate in Teams |
| `HTTP 400` | Bad payload, check logs for details |
| Test passes but no message | Check workflow is enabled in Teams |

### Certificate Check Failures

```bash
# View detailed logs
docker compose logs -f certcheck

# Check specific site manually
docker exec certcheck python -c "from certcheck import check_cert; print(check_cert('example.com'))"
```

### Port Already in Use

```bash
# Find process using port 7921
sudo lsof -i :7921

# Change port in docker-compose.yml
ports:
  - "8080:7921"  # Use port 8080 instead
```

### Dashboard Not Loading

```bash
# Check container status
docker compose ps

# Restart container
docker compose restart

# Rebuild if needed
docker compose up -d --build
```

## 📝 License

MIT License - Feel free to use and modify

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

For issues and questions, please open an issue on GitHub.
