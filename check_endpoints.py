#!/usr/bin/env python3
"""Check health and data freshness of Overpass API endpoints.

Sends a minimal query to each endpoint to verify it can serve data,
then reports the osm3s data timestamp. Also checks /status for server
metadata (rate limits, slots, areas). Zero external dependencies.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


def build_user_agent():
    explicit = os.environ.get("TAP_IN_OSM_USER_AGENT", "").strip()
    if explicit:
        return explicit
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if repo:
        return f"tap-in-osm (https://github.com/{repo})"
    return "tap-in-osm (unconfigured local run)"


USER_AGENT = build_user_agent()

ENDPOINTS = [
    "https://overpass-api.de/api/",
    "https://overpass.kumi.systems/api/",
    "https://maps.mail.ru/osm/tools/overpass/api/",
    "https://overpass.private.coffee/api/",
    "https://overpass.maprva.org/api/",
]

# Tiny query that returns no elements but does return the osm3s timestamp
TIMESTAMP_QUERY = "[out:json][timeout:5];out count;"

REQUEST_TIMEOUT = 20  # seconds


def fetch_data_timestamp(base_url):
    """Send a minimal query and return the osm3s.timestamp_osm_base value."""
    url = base_url.rstrip("/") + "/interpreter"
    encoded = urllib.parse.urlencode({"data": TIMESTAMP_QUERY}).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("osm3s", {}).get("timestamp_osm_base", "")


def fetch_status(base_url):
    """Fetch /status and parse server metadata."""
    url = base_url.rstrip("/") + "/status"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        text = resp.read().decode("utf-8")

    info = {}
    for line in text.splitlines():
        line = line.strip()
        if "Area timestamp:" in line:
            info["areas"] = True
        if "Rate limit:" in line:
            info["rate_limit"] = line.split(":", 1)[1].strip()
        if "slots available" in line.lower():
            info["slots"] = line.strip()
    return info


def data_age(ts_str):
    """Return (human-readable age string, hours as float) from an ISO timestamp."""
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        if hours < 1:
            return f"{hours * 60:.0f}m ago", hours
        if hours < 48:
            return f"{hours:.1f}h ago", hours
        return f"{hours / 24:.1f}d ago", hours
    except (ValueError, TypeError):
        return "?", -1


def check_all():
    """Check all endpoints and print a summary."""
    results = []

    for base_url in ENDPOINTS:
        name = base_url.split("//")[1].split("/")[0]
        entry = {"name": name, "status": "OK", "data_timestamp": "", "meta": {}}

        # Primary check: can it answer a query and what's the data date?
        try:
            entry["data_timestamp"] = fetch_data_timestamp(base_url)
        except urllib.error.HTTPError as e:
            entry["status"] = f"HTTP {e.code}"
        except urllib.error.URLError as e:
            reason = str(e.reason) if hasattr(e, "reason") else str(e)
            entry["status"] = f"UNREACHABLE"
        except Exception as e:
            entry["status"] = f"ERROR"

        # Secondary check: server metadata from /status
        if entry["status"] == "OK":
            try:
                entry["meta"] = fetch_status(base_url)
            except Exception:
                pass  # /status is optional — query working is what matters

        results.append(entry)

    # Print results
    print(f"{'Endpoint':<35} {'Status':<14} {'Data Timestamp':<24} {'Age':<12} {'Areas'}")
    print("-" * 95)

    for r in results:
        ts = r["data_timestamp"]
        age_str, _ = data_age(ts) if ts else ("", -1)
        areas = "yes" if r["meta"].get("areas") else ""
        print(f"{r['name']:<35} {r['status']:<14} {ts:<24} {age_str:<12} {areas}")

    # Summary
    print()
    ok = [r for r in results if r["status"] == "OK"]
    print(f"{len(ok)}/{len(results)} endpoints healthy")

    for r in ok:
        ts = r["data_timestamp"]
        if not ts:
            continue
        _, hours = data_age(ts)
        if hours > 48:
            print(f"WARNING: {r['name']} data is {hours:.1f}h old")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(check_all())
