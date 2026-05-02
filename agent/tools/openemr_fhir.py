"""
OpenEMR FHIR R4 client for the agent tool layer.

Enabled when *all three* env vars are set:
  OPENEMR_BASE_URL          e.g. https://clinical-copilot-v2.fly.dev
  OPENEMR_FHIR_CLIENT_ID    OAuth2 client_id registered in OpenEMR
  OPENEMR_FHIR_CLIENT_SECRET

When not configured the module raises ``OpenEMRNotConfigured`` so callers can
fall back to the CSV cohort.

Quick setup (run once in OpenEMR admin → API Clients):
  1. Administration → Config → API Clients → "Register New Client"
  2. Name: "AI Copilot", grant_type: client_credentials,
     scopes: patient/Patient.read patient/MedicationRequest.read
             patient/Observation.read patient/AllergyIntolerance.read
  3. Copy client_id + client_secret → fly secrets set on clinical-agent-scaffold
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any

import httpx

_TOKEN_LOCK = threading.Lock()
_token_cache: dict[str, Any] = {}  # {"access_token", "expires_at"}


class OpenEMRNotConfigured(RuntimeError):
    """Raised when required OPENEMR_* env vars are absent."""


def _cfg() -> tuple[str, str, str]:
    """Return (base_url, client_id, client_secret) or raise."""
    base = (os.environ.get("OPENEMR_BASE_URL") or "").rstrip("/")
    cid = (os.environ.get("OPENEMR_FHIR_CLIENT_ID") or "").strip()
    sec = (os.environ.get("OPENEMR_FHIR_CLIENT_SECRET") or "").strip()
    if not (base and cid and sec):
        raise OpenEMRNotConfigured(
            "Set OPENEMR_BASE_URL, OPENEMR_FHIR_CLIENT_ID, "
            "and OPENEMR_FHIR_CLIENT_SECRET to enable OpenEMR FHIR tools."
        )
    return base, cid, sec


def _get_token(base: str, client_id: str, client_secret: str) -> str:
    """Fetch or return cached OAuth2 client-credentials token."""
    with _TOKEN_LOCK:
        now = time.monotonic()
        if _token_cache.get("access_token") and now < _token_cache.get("expires_at", 0):
            return str(_token_cache["access_token"])

        resp = httpx.post(
            f"{base}/oauth2/default/token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": (
                    "patient/Patient.read "
                    "patient/MedicationRequest.read "
                    "patient/Observation.read "
                    "patient/AllergyIntolerance.read"
                ),
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache["access_token"] = data["access_token"]
        _token_cache["expires_at"] = now + int(data.get("expires_in", 300)) - 30
        return str(_token_cache["access_token"])


def _fhir_get(path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    """Authenticated FHIR GET; returns parsed JSON."""
    base, cid, sec = _cfg()
    token = _get_token(base, cid, sec)
    resp = httpx.get(
        f"{base}/apis/default/fhir/{path.lstrip('/')}",
        params=params or {},
        headers={"Authorization": f"Bearer {token}", "Accept": "application/fhir+json"},
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Public helpers used by dispatch.py
# ---------------------------------------------------------------------------

def fhir_patient_by_identifier(patient_uuid: str) -> dict[str, Any]:
    """
    Return the OpenEMR Patient FHIR resource matching the Synthea UUID stored
    in ``patient_data.pubpid``.

    On not-found returns ``{"error": "patient_not_found"}``.
    """
    bundle = _fhir_get("Patient", {"identifier": patient_uuid})
    entries = (bundle or {}).get("entry") or []
    if not entries:
        return {"error": "patient_not_found", "identifier": patient_uuid}
    resource = entries[0].get("resource", {})
    name_block = (resource.get("name") or [{}])[0]
    return {
        "source": "openemr_fhir",
        "fhir_id": resource.get("id"),
        "last": (name_block.get("family") or ""),
        "first": " ".join(name_block.get("given") or []),
        "birthdate": resource.get("birthDate", ""),
        "gender": resource.get("gender", ""),
        "address": _first_address(resource.get("address")),
    }


def fhir_medications(patient_uuid: str) -> dict[str, Any]:
    """Active MedicationRequests for the patient identified by Synthea UUID."""
    patient = fhir_patient_by_identifier(patient_uuid)
    if "error" in patient:
        return patient
    fhir_id = patient["fhir_id"]
    bundle = _fhir_get("MedicationRequest", {"patient": fhir_id, "status": "active"})
    entries = (bundle or {}).get("entry") or []
    meds = []
    for e in entries:
        r = e.get("resource", {})
        concept = (r.get("medicationCodeableConcept") or {})
        meds.append({
            "description": concept.get("text") or _first_coding_display(concept),
            "authored_on": r.get("authoredOn", ""),
            "status": r.get("status", ""),
        })
    return {"source": "openemr_fhir", "count": len(meds), "medications": meds}


def fhir_observations(patient_uuid: str, category: str = "laboratory") -> dict[str, Any]:
    """Observations for one category (laboratory | vital-signs)."""
    patient = fhir_patient_by_identifier(patient_uuid)
    if "error" in patient:
        return patient
    fhir_id = patient["fhir_id"]
    bundle = _fhir_get(
        "Observation",
        {"patient": fhir_id, "category": category, "_sort": "-date", "_count": "50"},
    )
    entries = (bundle or {}).get("entry") or []
    rows = []
    for e in entries:
        r = e.get("resource", {})
        code_block = r.get("code") or {}
        value_qty = r.get("valueQuantity") or {}
        rows.append({
            "description": code_block.get("text") or _first_coding_display(code_block),
            "value": value_qty.get("value"),
            "unit": value_qty.get("unit", ""),
            "date": r.get("effectiveDateTime", ""),
        })
    key = "labs" if category == "laboratory" else "vitals"
    return {"source": "openemr_fhir", "count": len(rows), key: rows}


def fhir_allergies(patient_uuid: str) -> dict[str, Any]:
    """AllergyIntolerances for the patient."""
    patient = fhir_patient_by_identifier(patient_uuid)
    if "error" in patient:
        return patient
    fhir_id = patient["fhir_id"]
    bundle = _fhir_get("AllergyIntolerance", {"patient": fhir_id})
    entries = (bundle or {}).get("entry") or []
    rows = []
    for e in entries:
        r = e.get("resource", {})
        code_block = r.get("code") or {}
        rows.append({
            "description": code_block.get("text") or _first_coding_display(code_block),
            "clinical_status": _status_display(r.get("clinicalStatus")),
            "type": r.get("type", ""),
        })
    return {"source": "openemr_fhir", "count": len(rows), "allergies": rows}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _first_coding_display(block: dict[str, Any]) -> str:
    codings = block.get("coding") or []
    if codings:
        return str(codings[0].get("display") or codings[0].get("code") or "")
    return ""


def _first_address(addresses: list[dict[str, Any]] | None) -> dict[str, Any]:
    if not addresses:
        return {}
    a = addresses[0]
    return {
        "city": a.get("city", ""),
        "state": a.get("state", ""),
        "country": a.get("country", ""),
    }


def _status_display(block: dict[str, Any] | None) -> str:
    if not block:
        return ""
    codings = block.get("coding") or []
    if codings:
        return str(codings[0].get("code") or "")
    return block.get("text", "")
