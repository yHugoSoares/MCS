#!/usr/bin/env python3
"""Benign traffic generator for the TP4 lab (role 1 deliverable).

Continuously exercises the protected service the way a normal user would:
an HTTP GET on a real page plus an optional ICMP echo, one cycle per
interval. Every cycle is written as one JSON line so the monitoring stack can
plot availability/latency next to the firewall events.

This is the instrument behind the mandatory "legitimate service" requirement:
it must keep succeeding before, during and after each attack.

Examples
--------
    python3 legit_client.py                       # 1 req/s forever, HTTP+ping
    python3 legit_client.py --duration 120 --label t-001-baseline
    python3 legit_client.py --url http://10.9.1.2/product.php?id=1
    python3 legit_client.py --no-ping --interval 0.2

Output: JSON Lines on stdout and in --out (default /var/log/client/legit.jsonl).
Exit code 0 on a clean stop; summary is written next to the log.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_STOP = False


def utc_now() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def handle_stop(signum, _frame):
    global _STOP
    _STOP = True
    print(f"# signal {signum} received, stopping after current cycle", file=sys.stderr)


def http_once(url: str, timeout: float) -> dict:
    started = time.perf_counter()
    status = None
    error = None
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "tp4-legit-client/1.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            response.read(4096)
        ok = 200 <= status < 400
    except urllib.error.HTTPError as exc:  # reached the server, bad status
        status = exc.code
        ok = False
        error = f"http_{exc.code}"
    except Exception as exc:  # timeout, refused, reset...
        ok = False
        error = f"{type(exc).__name__}: {exc}"
    return {
        "kind": "http",
        "ok": ok,
        "status": status,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "error": error,
    }


_PING_RE = re.compile(r"time=([0-9.]+)\s*ms")


def ping_once(target: str, timeout: float) -> dict:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            ["ping", "-n", "-c", "1", "-W", str(max(1, int(timeout))), target],
            capture_output=True,
            text=True,
            timeout=timeout + 1,
        )
        match = _PING_RE.search(proc.stdout)
        ok = proc.returncode == 0 and match is not None
        return {
            "kind": "ping",
            "ok": ok,
            "status": None,
            "rtt_ms": round(float(match.group(1)), 2) if match else None,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "error": None if ok else f"rc={proc.returncode}",
        }
    except Exception as exc:
        return {
            "kind": "ping",
            "ok": False,
            "status": None,
            "rtt_ms": None,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "error": f"{type(exc).__name__}: {exc}",
        }


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((pct / 100) * (len(ordered) - 1))))
    return round(ordered[index], 2)


def summarise(records: list[dict], label: str) -> dict:
    http = [r for r in records if r["kind"] == "http"]
    ping = [r for r in records if r["kind"] == "ping"]
    http_lat = [r["latency_ms"] for r in http]
    return {
        "label": label,
        "generated_at": utc_now(),
        "cycles": len(records),
        "http": {
            "total": len(http),
            "ok": sum(1 for r in http if r["ok"]),
            "availability_pct": round(100 * sum(1 for r in http if r["ok"]) / len(http), 2) if http else None,
            "latency_ms_p50": percentile(http_lat, 50),
            "latency_ms_p95": percentile(http_lat, 95),
            "latency_ms_max": round(max(http_lat), 2) if http_lat else None,
        },
        "ping": {
            "total": len(ping),
            "ok": sum(1 for r in ping if r["ok"]),
            "loss_pct": round(100 * sum(1 for r in ping if not r["ok"]) / len(ping), 2) if ping else None,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="TP4 benign traffic generator")
    parser.add_argument("--url", default="http://10.9.1.2/healthz.php")
    parser.add_argument("--ping-target", default="10.9.1.2")
    parser.add_argument("--interval", type=float, default=1.0, help="seconds between cycles")
    parser.add_argument("--duration", type=float, default=0, help="0 = run until stopped")
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--label", default=os.getenv("LAB_TRIAL", "baseline"))
    parser.add_argument("--out", default="/var/log/client/legit.jsonl")
    parser.add_argument("--summary-out", default="")
    parser.add_argument("--summary-every", type=float, default=30, help="0 disables periodic summary")
    parser.add_argument("--no-ping", action="store_true")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path = Path(args.summary_out) if args.summary_out else out_path.with_name(f"legit-summary-{args.label}.json")

    records: list[dict] = []
    started = time.monotonic()
    last_summary = started
    host = os.getenv("HOSTNAME", "client")

    with out_path.open("a", encoding="utf-8") as sink:
        while not _STOP:
            cycle_start = time.monotonic()
            results = [http_once(args.url, args.timeout)]
            if not args.no_ping:
                results.append(ping_once(args.ping_target, args.timeout))

            for result in results:
                record = {
                    "ts": utc_now(),
                    "trial": args.label,
                    "phase": "benign",
                    "attack": None,
                    "client": host,
                    "target": args.url if result["kind"] == "http" else args.ping_target,
                    **result,
                }
                records.append(record)
                line = json.dumps(record, separators=(",", ":"))
                sink.write(line + "\n")
                sink.flush()
                print(line, flush=True)

            if args.summary_every and time.monotonic() - last_summary >= args.summary_every:
                last_summary = time.monotonic()
                print(json.dumps({"periodic_summary": summarise(records, args.label)}), file=sys.stderr, flush=True)

            if args.duration and time.monotonic() - started >= args.duration:
                break

            sleep_for = args.interval - (time.monotonic() - cycle_start)
            if sleep_for > 0:
                time.sleep(sleep_for)

    summary = summarise(records, args.label)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary}), file=sys.stderr, flush=True)
    print(f"# summary written to {summary_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
