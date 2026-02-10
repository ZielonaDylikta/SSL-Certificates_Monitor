#!/usr/bin/env python3
"""
Simple SSL Certificate Checker
Reads sites from sites.csv, serves results on port 7921.
Optionally sends Teams alerts when certs expire within 15 days.

Environment variables:
    TEAMS_WEBHOOK - Teams Workflows webhook URL (optional)
    ALERT_DAYS    - Alert threshold in days (default: 15)
    TEST_KEY      - Key to protect test endpoints (optional)
"""

import ssl
import socket
import datetime
import csv
import json
import os
import threading
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 7921
CHECK_INTERVAL = 3600
MAX_WORKERS = 10
ALERT_DAYS = int(os.environ.get('ALERT_DAYS', 15))
TEAMS_WEBHOOK = os.environ.get('TEAMS_WEBHOOK', '')
TEST_KEY = os.environ.get('TEST_KEY', '')

results = []
lock = threading.Lock()
ready = threading.Event()

_template_cache = None
_template_mtime = 0
_alerts_sent = {}
_alerts_sent_lock = threading.Lock()
_last_test = 0
_last_test_lock = threading.Lock()
_start_time = time.time()

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)
ALERTS_FILE = os.path.join(DATA_DIR, 'alerts_sent.json')


def load_alert_history():
    """Load alert history from disk so it survives restarts."""
    global _alerts_sent
    try:
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, 'r') as f:
                _alerts_sent = json.load(f)
            print(f"[INFO] Loaded alert history ({len(_alerts_sent)} entries)")
    except Exception as e:
        print(f"[WARNING] Could not load alert history: {e}")
        _alerts_sent = {}


def save_alert_history():
    """Save alert history to disk."""
    try:
        with _alerts_sent_lock:
            with open(ALERTS_FILE, 'w') as f:
                json.dump(_alerts_sent, f)
    except Exception as e:
        print(f"[WARNING] Could not save alert history: {e}")


def load_sites(filename='sites.csv'):
    sites = []
    try:
        with open(filename, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip() and not row[0].startswith('#'):
                    site = row[0].strip()
                    if '.' in site:
                        sites.append(site)
    except FileNotFoundError:
        print(f"[ERROR] {filename} not found.")
    except Exception as e:
        print(f"[ERROR] Failed to read {filename}: {e}")
    return sites


def check_cert(hostname):
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as s:
                cert = s.getpeercert()
                expiry = datetime.datetime.strptime(
                    cert['notAfter'], '%b %d %H:%M:%S %Y %Z'
                ).replace(tzinfo=datetime.timezone.utc)
                now = datetime.datetime.now(datetime.timezone.utc)
                days = (expiry - now).days
                issuer = dict(x[0] for x in cert['issuer']).get(
                    'organizationName', 'Unknown'
                )
                return {
                    'site': hostname,
                    'expiry': expiry.strftime('%Y-%m-%d'),
                    'days': days,
                    'issuer': issuer,
                    'error': None,
                }
    except Exception as e:
        return {
            'site': hostname,
            'expiry': '-',
            'days': -1,
            'issuer': '-',
            'error': str(e),
        }


def load_template():
    global _template_cache, _template_mtime
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template.html')
    try:
        mtime = os.path.getmtime(path)
        if _template_cache is None or mtime > _template_mtime:
            with open(path, 'r', encoding='utf-8') as f:
                _template_cache = f.read()
            _template_mtime = mtime
            print(f"[INFO] Template loaded from {path}")
        return _template_cache
    except FileNotFoundError:
        if _template_cache:
            return _template_cache
        return "<html><body><h1>template.html not found</h1></body></html>"


def send_to_teams(payload):
    """Send a payload to Teams webhook. Returns (success, message)."""
    if not TEAMS_WEBHOOK:
        return False, "TEAMS_WEBHOOK not set"

    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            TEAMS_WEBHOOK, data,
            {"Content-Type": "application/json"}
        )
        response = urllib.request.urlopen(req, timeout=10)
        code = response.getcode()
        body = response.read().decode()
        return True, f"HTTP {code}: {body}"
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


def test_teams_webhook():
    """Send a test message to Teams. Returns (success, message)."""
    payload = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.5",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "🔒 SSL Certificate Monitor — Test",
                        "weight": "Bolder",
                        "size": "Large",
                        "wrap": True
                    },
                    {
                        "type": "TextBlock",
                        "text": f"✅ Webhook is working! Test sent at "
                                f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        "wrap": True,
                        "color": "Good"
                    },
                    {
                        "type": "FactSet",
                        "facts": [
                            {"title": "Alert threshold", "value": f"{ALERT_DAYS} days"},
                            {"title": "Check interval", "value": f"{CHECK_INTERVAL}s"},
                            {"title": "Sites monitored", "value": str(len(load_sites()))},
                        ]
                    }
                ]
            }
        }]
    }

    return send_to_teams(payload)


def notify_teams(expiring):
    """Send Teams notification via Workflows webhook."""
    if not TEAMS_WEBHOOK or not expiring:
        return

    count = len(expiring)
    most_urgent = min(r['days'] for r in expiring)

    if most_urgent <= 7:
        header_color = "attention"
    else:
        header_color = "warning"

    rows = []
    for r in sorted(expiring, key=lambda x: x['days']):
        if r['days'] < 0:
            status = f"🔴 Expired {abs(r['days'])}d ago"
        elif r['days'] <= 7:
            status = f"🔴 {r['days']}d left"
        else:
            status = f"🟡 {r['days']}d left"

        rows.append({
            "type": "TableRow",
            "cells": [
                {"type": "TableCell", "items": [{"type": "TextBlock", "text": r['site'], "weight": "Bolder", "size": "Small", "wrap": True}]},
                {"type": "TableCell", "items": [{"type": "TextBlock", "text": status, "size": "Small", "wrap": True}]},
                {"type": "TableCell", "items": [{"type": "TextBlock", "text": r['expiry'], "size": "Small"}]},
            ]
        })

    card = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.5",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "🔒 SSL Certificate Alert",
                        "weight": "Bolder",
                        "size": "Large",
                        "wrap": True
                    },
                    {
                        "type": "TextBlock",
                        "text": f"{count} certificate{'s' if count > 1 else ''} expiring within {ALERT_DAYS} days",
                        "spacing": "None",
                        "color": header_color,
                        "wrap": True
                    },
                    {
                        "type": "Table",
                        "gridStyle": "accent",
                        "firstRowAsHeader": True,
                        "showGridLines": True,
                        "columns": [
                            {"width": 3},
                            {"width": 2},
                            {"width": 2}
                        ],
                        "rows": [
                            {
                                "type": "TableRow",
                                "style": "accent",
                                "cells": [
                                    {"type": "TableCell", "items": [{"type": "TextBlock", "text": "Site", "weight": "Bolder", "size": "Small", "wrap": True}]},
                                    {"type": "TableCell", "items": [{"type": "TextBlock", "text": "Status", "weight": "Bolder", "size": "Small", "wrap": True}]},
                                    {"type": "TableCell", "items": [{"type": "TextBlock", "text": "Expires", "weight": "Bolder", "size": "Small"}]},
                                ]
                            }
                        ] + rows
                    }
                ]
            }
        }]
    }

    success, msg = send_to_teams(card)
    if success:
        print(f"[TEAMS] ✓ Alert sent for {count} site{'s' if count > 1 else ''}")
    else:
        print(f"[TEAMS] ✗ Failed: {msg}")


def check_alerts(data):
    """Check results and send Teams alert once per day per site."""
    today = datetime.date.today().isoformat()

    expiring = []
    with _alerts_sent_lock:
        for r in data:
            if r['error']:
                continue
            if r['days'] <= ALERT_DAYS:
                last = _alerts_sent.get(r['site'])
                if last != today:
                    expiring.append(r)
                    _alerts_sent[r['site']] = today

    if expiring:
        notify_teams(expiring)
        save_alert_history()


def checker_loop(sites):
    while True:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Checking {len(sites)} sites...")
        start = time.time()
        data = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(check_cert, site): site for site in sites}
            for future in as_completed(futures):
                r = future.result()
                status = f"{r['days']}d" if not r['error'] else 'ERROR'
                print(f"  {r['site']:30s} {status}")
                data.append(r)

        elapsed = time.time() - start
        with lock:
            results.clear()
            results.extend(data)
        ready.set()

        check_alerts(data)

        new_sites = load_sites()
        if new_sites:
            sites = new_sites

        print(f"Done in {elapsed:.1f}s. Next check in {CHECK_INTERVAL}s\n")
        time.sleep(CHECK_INTERVAL)


def check_test_auth(handler):
    """Check if test endpoint access is authorized."""
    if not TEST_KEY:
        return True
    if handler.headers.get('X-Test-Key', '') == TEST_KEY:
        return True
    if f'key={TEST_KEY}' in handler.path:
        return True
    return False


def check_rate_limit():
    """Rate limit test endpoints. Returns (allowed, wait_seconds)."""
    global _last_test
    with _last_test_lock:
        now = time.time()
        elapsed = now - _last_test
        if elapsed < 30:
            return False, int(30 - elapsed)
        _last_test = now
        return True, 0


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            path = self.path.split('?')[0].rstrip('/')

            if path == '/api':
                with lock:
                    data = list(results)
                payload = json.dumps(data, default=str).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.send_header('Cache-Control', 'no-cache, no-store')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(payload)

            elif path == '/health':
                with lock:
                    site_count = len(results)
                    ok_count = sum(1 for r in results if not r.get('error') and r.get('days', -1) > ALERT_DAYS)
                    warn_count = sum(1 for r in results if not r.get('error') and 0 <= r.get('days', -1) <= ALERT_DAYS)
                    err_count = sum(1 for r in results if r.get('error'))

                health = {
                    "status": "ok" if ready.is_set() else "starting",
                    "sites_total": site_count,
                    "sites_ok": ok_count,
                    "sites_warning": warn_count,
                    "sites_error": err_count,
                    "teams_configured": bool(TEAMS_WEBHOOK),
                    "alert_threshold": ALERT_DAYS,
                    "check_interval": CHECK_INTERVAL,
                    "uptime_seconds": int(time.time() - _start_time),
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }
                payload = json.dumps(health, indent=2).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            elif path == '/test-webhook':
                if not check_test_auth(self):
                    payload = json.dumps({"error": "Unauthorized. Provide X-Test-Key header or ?key= parameter"}).encode()
                    self.send_response(403)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                allowed, wait = check_rate_limit()
                if not allowed:
                    payload = json.dumps({"error": f"Rate limited. Try again in {wait} seconds"}).encode()
                    self.send_response(429)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(payload)))
                    self.send_header('Retry-After', str(wait))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                print("[TEST] Testing Teams webhook...")
                success, msg = test_teams_webhook()
                result = {
                    "webhook_configured": bool(TEAMS_WEBHOOK),
                    "webhook_url": TEAMS_WEBHOOK[:50] + "..." if TEAMS_WEBHOOK else "",
                    "success": success,
                    "message": msg,
                    "timestamp": datetime.datetime.now().isoformat(),
                }
                if not TEAMS_WEBHOOK:
                    result["message"] = "TEAMS_WEBHOOK environment variable not set"

                payload = json.dumps(result, indent=2).encode()
                self.send_response(200 if success else 502 if TEAMS_WEBHOOK else 400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

                if success:
                    print(f"[TEST] ✓ Webhook test passed: {msg}")
                else:
                    print(f"[TEST] ✗ Webhook test failed: {msg}")

            elif path == '/test-alert':
                if not check_test_auth(self):
                    payload = json.dumps({"error": "Unauthorized. Provide X-Test-Key header or ?key= parameter"}).encode()
                    self.send_response(403)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                allowed, wait = check_rate_limit()
                if not allowed:
                    payload = json.dumps({"error": f"Rate limited. Try again in {wait} seconds"}).encode()
                    self.send_response(429)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(payload)))
                    self.send_header('Retry-After', str(wait))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                print("[TEST] Sending fake alert...")
                fake_data = [
                    {"site": "test-expired.example.com", "expiry": "2024-01-01", "days": -30, "issuer": "Test CA", "error": None},
                    {"site": "test-critical.example.com", "expiry": "2025-01-20", "days": 5, "issuer": "Test CA", "error": None},
                    {"site": "test-warning.example.com", "expiry": "2025-01-28", "days": 13, "issuer": "Test CA", "error": None},
                ]
                notify_teams(fake_data)

                result = {
                    "webhook_configured": bool(TEAMS_WEBHOOK),
                    "test_sites": len(fake_data),
                    "message": "Fake alert sent — check your Teams channel" if TEAMS_WEBHOOK else "TEAMS_WEBHOOK not set",
                    "timestamp": datetime.datetime.now().isoformat(),
                }
                payload = json.dumps(result, indent=2).encode()
                self.send_response(200 if TEAMS_WEBHOOK else 400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            elif path in ('', '/', '/index.html'):
                page = load_template().encode()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(page)))
                self.end_headers()
                self.wfile.write(page)

            else:
                self.send_response(404)
                self.send_header('Content-Length', '0')
                self.end_headers()

        except BrokenPipeError:
            pass
        except Exception:
            try:
                self.send_response(500)
                self.send_header('Content-Length', '0')
                self.end_headers()
            except Exception:
                pass

    def log_message(self, *args):
        pass


def main():
    sites = load_sites()
    print(f"\nSSL Certificate Checker")
    print(f"  Sites:  {len(sites)}")
    print(f"  Port:   {PORT}")
    print(f"  Check:  every {CHECK_INTERVAL}s")
    print(f"  Alert:  when < {ALERT_DAYS} days")
    if TEAMS_WEBHOOK:
        print(f"  Teams:  ON")
    else:
        print(f"  Teams:  OFF (set TEAMS_WEBHOOK to enable)")
    if TEST_KEY:
        print(f"  Auth:   ON (test endpoints protected)")
    else:
        print(f"  Auth:   OFF (set TEST_KEY to protect test endpoints)")
    print(f"  Data:   {DATA_DIR}")
    print()

    if not sites:
        print("No sites found. Create sites.csv with one domain per line.")
        return

    load_template()
    load_alert_history()

    t = threading.Thread(target=checker_loop, args=(sites,), daemon=True)
    t.start()

    print("Waiting for first check...")
    ready.wait(timeout=120)

    try:
        server = HTTPServer(('0.0.0.0', PORT), Handler)
    except OSError as e:
        print(f"[ERROR] Cannot start on port {PORT}: {e}")
        return

    print(f"  Dashboard:      http://localhost:{PORT}")
    print(f"  API:            http://localhost:{PORT}/api")
    print(f"  Health:         http://localhost:{PORT}/health")
    print(f"  Test webhook:   http://localhost:{PORT}/test-webhook")
    print(f"  Test alert:     http://localhost:{PORT}/test-alert")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
        save_alert_history()
        server.server_close()
        print("[INFO] Stopped.")


if __name__ == '__main__':
    main()
