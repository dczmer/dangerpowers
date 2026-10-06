"""Minimal HTTP API client used by the weekly report automation."""

import requests

API_BASE = "https://reports.internal.example.com"


def fetch_report(report_id):
    """Fetch a single report by id."""
    resp = requests.get(f"{API_BASE}/reports/{report_id}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def list_reports(owner):
    """List all reports owned by the given user."""
    resp = requests.get(
        f"{API_BASE}/reports",
        params={"owner": owner},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
