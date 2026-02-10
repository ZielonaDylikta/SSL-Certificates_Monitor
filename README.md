# 🔒 SSL Certificate Monitor with MS Teams Alerts

Simple, zero-dependency SSL certificate expiration checker with a premium dashboard and Microsoft Teams alerts.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![Dependencies](https://img.shields.io/badge/Dependencies-None-green)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- ✅ Monitor 20+ websites simultaneously
- ✅ Parallel certificate checking (fast)
- ✅ Premium dark dashboard with animations
- ✅ Microsoft Teams alerts via Workflows webhook
- ✅ Alert cooldown (once per day per site)
- ✅ Alert history persists across restarts
- ✅ Health check endpoint for Docker
- ✅ Test endpoints with auth & rate limiting
- ✅ Hot-reload sites and template without restart
- ✅ Zero external dependencies (stdlib only)
- ✅ Docker ready with compose
<img width="1178" height="913" alt="ssl_cer_monitor" src="https://github.com/user-attachments/assets/19c9f330-4c16-4952-9a1f-058f4617d5b6" />

## Quick Start

### 1. Clone / Download

```bash
mkdir certcheck && cd certcheck

update docker-compose.yml with your webhooks
docker compose up -d --build

certcheck/
├── certcheck.py
├── template.html
├── sites.csv
├── Dockerfile
├── docker-compose.yml
└── README.md


# My websites to monitor
google.com
github.com
mycompany.com
internal.mysite.com


┌─────────────────────────────────────────────────────────┐
│                 🔒 Certificate Monitor                  │
│                  21 sites monitored                     │
│                                                         │
│  ● 18 Healthy  ● 2 Warning  ● 1 Critical  ● 0 Error     │
│                                                         │
│  Site              Issuer      Expires   Days   Status  │
│  ───────────────── ─────────── ──────── ────── ──────── │
│  critical.com      Let's Enc   01-20     ██ 5d  🔴 Crit │
│  warning.com       DigiCert    02-01     ███ 17d 🟡 Soon│
│  google.com        Google      04-15     ████ 89d 🟢 OK │
│  github.com        DigiCert    05-20     ████ 124d 🟢 OK│
└─────────────────────────────────────────────────────────┘



┌──────────────────────────────────────────────────┐
│  🔒 SSL Certificate Alert                        │
│  2 certificates expiring within 15 days          │
│                                                  │
│  Site              │ Status        │ Expires     │
│  ──────────────────┼───────────────┼──────────   │
│  critical.com      │ 🔴 5d left    │ 2025-01-20  │
│  warning.com       │ 🟡 13d left   │ 2025-01-28  │
└──────────────────────────────────────────────────┘

COMPOSE

services:
  certcheck:
    build: .
    container_name: certcheck
    ports:
      - "7921:7921"
    volumes:
      - ./sites.csv:/app/sites.csv
      - ./template.html:/app/template.html
      - ./data:/app/data
    restart: unless-stopped
    environment:
      - TEAMS_WEBHOOK=https://your-webhook-url-here
      - ALERT_DAYS=15
      - TEST_KEY=mysecretkey123



Endpoint		Auth	Description
GET /			No	Dashboard
GET /api		No	JSON certificate data
GET /health		No	Health check (used by Docker)
GET /test-webhook	Yes	Test Teams webhook connection
GET /test-alert		Yes	Send fake alert to Teams


API Response
Bash

curl http://localhost:7921/api
JSON

[
  {
    "site": "google.com",
    "expiry": "2025-04-15",
    "days": 89,
    "issuer": "Google Trust Services",
    "error": null
  }
]
Health Check
Bash

curl http://localhost:7921/health

{
  "status": "ok",
  "sites_total": 21,
  "sites_ok": 19,
  "sites_warning": 1,
  "sites_error": 1,
  "teams_configured": true,
  "alert_threshold": 15,
  "check_interval": 3600,
  "uptime_seconds": 86400
}


Test Endpoints 

# With header
curl -H "X-Test-Key: mysecretkey123" http://localhost:7921/test-webhook
curl -H "X-Test-Key: mysecretkey123" http://localhost:7921/test-alert

# With query parameter
curl http://localhost:7921/test-webhook?key=mysecretkey123
curl http://localhost:7921/test-alert?key=mysecretkey123

Docker Commands

Command	Description
docker compose up -d --build	Build and start
docker compose down	Stop
docker compose restart	Restart
docker compose logs -f	Watch logs
docker compose ps	Check status


certcheck/
├── certcheck.py          # Main application
├── template.html         # Dashboard UI
├── sites.csv             # Sites to monitor (editable)
├── data/                 # Persistent data (auto-created)
│   └── alerts_sent.json  # Alert history (auto-created)
├── Dockerfile
├── docker-compose.yml
└── README.md


How it works ?

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

Certificate Check Cycle
Load sites from sites.csv
Check all certificates in parallel (10 threads)
Update dashboard data
Check if any cert expires within 15 days
Send Teams alert (once per day per site)
Save alert history to disk
Wait 1 hour
Repeat
Alert Logic
Condition	Action
Cert > 15 days remaining	Nothing
Cert ≤ 15 days, not alerted today	Send Teams alert
Cert ≤ 15 days, already alerted today	Skip (cooldown)
Next day, still expiring	Alert again
Container restart	Loads alert history, no duplicate


Status Levels
Status	Days Left	Dashboard	Teams
🟢 Healthy	> 30	Green	No alert
🟡 Soon	16 — 30	Yellow	Alert
🟠 Warning	8 — 15	Orange	Alert
🔴 Critical	0 — 7	Red (pulsing)	Alert
🔴 Expired	< 0	Dark red (pulsing)	Alert
❌ Error	—	Gray	No alert


Teams check 

# 1. Check webhook is set
curl http://localhost:7921/health

# 2. Test webhook connection
curl http://localhost:7921/test-webhook?key=YOUR_TEST_KEY

# 3. Test full alert
curl http://localhost:7921/test-alert?key=YOUR_TEST_KEY

# 4. Check logs
docker compose logs -f | grep TEAMS

# Test webhook connection
curl -H "X-Test-Key: mysecretkey123" http://localhost:7921/test-webhook

# Test fake alert
curl -H "X-Test-Key: mysecretkey123" http://localhost:7921/test-alert

Common Teams errors
Error	Fix
TEAMS_WEBHOOK not set	Add TEAMS_WEBHOOK to docker-compose.yml
HTTP 404	Webhook URL is wrong, recreate in Teams
HTTP 400	Bad payload, check logs for details
Test passes but no message	Check flow is enabled in Teams Workflows

Requirements
Python 3.8+ (no external packages)
Docker & Docker Compose (optional, recommended)
Network access to monitored sites (port 443)
Microsoft Teams (optional, for alerts)
