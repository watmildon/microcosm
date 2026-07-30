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
    explicit = os.environ.get("MICROCOSM_USER_AGENT", "").strip()
    if explicit:
        return explicit
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if repo:
        return f"microcosm (https://github.com/{repo})"
    return "microcosm (unconfigured local run)"


USER_AGENT = build_user_agent()

# Matches fetch.py: a private instance URL here is checked ahead of the public list.
PRIMARY_ENDPOINT_ENV_VAR = "OVERPASS_PRIMARY_URL"

PUBLIC_ENDPOINTS = [
    "https://overpass-api.de/api/",
    "https://overpass.kumi.systems/api/",
    "https://maps.mail.ru/osm/tools/overpass/api/",
    "https://overpass.private.coffee/api/",
    "https://overpass.maprva.org/api/",
]

# Tiny query that returns no elements but does return the osm3s timestamp
TIMESTAMP_QUERY = "[out:json][timeout:5];out count;"

REQUEST_TIMEOUT = 20  # seconds


# Stand-in printed instead of the private endpoint's URL. Nothing about a private
# instance is shown — not even the hostname, since the API key often sits in the
# path (…/k/<key>/api/interpreter) and the host alone narrows down the rest.
PRIMARY_ENDPOINT_LABEL = f"private instance (${PRIMARY_ENDPOINT_ENV_VAR})"


def build_endpoint_list():
    """Return (interpreter_url, status_url, label) triples to check, primary first.

    Public entries are base URLs that both suffixes hang off. The private URL is
    used verbatim as the interpreter endpoint — it is whatever fetch.py posts to,
    and its API key may sit anywhere in the path, so /status can't be derived
    from it reliably. It gets no status URL and is checked by query alone.
    """
    public = [
        (base.rstrip("/") + "/interpreter", base.rstrip("/") + "/status",
         urllib.parse.urlparse(base).hostname or base)
        for base in PUBLIC_ENDPOINTS
    ]

    primary = os.environ.get(PRIMARY_ENDPOINT_ENV_VAR, "").strip()
    if not primary:
        return public

    parsed = urllib.parse.urlparse(primary)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        print(
            f"WARNING: {PRIMARY_ENDPOINT_ENV_VAR} is not a valid http(s) URL, "
            f"checking public endpoints only",
            file=sys.stderr,
        )
        return public

    return [(primary, None, PRIMARY_ENDPOINT_LABEL)] + public


def fetch_data_timestamp(url):
    """Send a minimal query and return the osm3s.timestamp_osm_base value."""
    encoded = urllib.parse.urlencode({"data": TIMESTAMP_QUERY}).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("osm3s", {}).get("timestamp_osm_base", "")


def fetch_status(url):
    """Fetch /status and parse server metadata."""
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

    for interpreter_url, status_url, label in build_endpoint_list():
        entry = {
            "name": label,
            "status": "OK",
            "data_timestamp": "",
            "meta": {},
        }

        # Primary check: can it answer a query and what's the data date?
        try:
            entry["data_timestamp"] = fetch_data_timestamp(interpreter_url)
        except urllib.error.HTTPError as e:
            entry["status"] = f"HTTP {e.code}"
        except urllib.error.URLError as e:
            entry["status"] = f"UNREACHABLE"
        except Exception as e:
            entry["status"] = f"ERROR"

        # Secondary check: server metadata from /status
        if entry["status"] == "OK" and status_url:
            try:
                entry["meta"] = fetch_status(status_url)
            except Exception:
                pass  # /status is optional — query working is what matters

        results.append(entry)

    # Print results
    # Widened to fit the private-instance label without shifting the other columns.
    print(f"{'Endpoint':<40} {'Status':<14} {'Data Timestamp':<24} {'Age':<12} {'Areas'}")
    print("-" * 100)

    for r in results:
        ts = r["data_timestamp"]
        age_str, _ = data_age(ts) if ts else ("", -1)
        areas = "yes" if r["meta"].get("areas") else ""
        print(f"{r['name']:<40} {r['status']:<14} {ts:<24} {age_str:<12} {areas}")

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
