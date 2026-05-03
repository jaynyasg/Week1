"""FHIR Observation category defense-in-depth (AUD-004)."""

from __future__ import annotations

from agent.tools.openemr_fhir import observation_resource_matches_category


def _obs(code: str) -> dict:
    return {
        "resourceType": "Observation",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": code,
                    }
                ]
            }
        ],
    }


def test_matches_laboratory():
    assert observation_resource_matches_category(_obs("laboratory"), "laboratory")
    assert not observation_resource_matches_category(_obs("laboratory"), "vital-signs")


def test_matches_vital_signs():
    assert observation_resource_matches_category(_obs("vital-signs"), "vital-signs")
    assert not observation_resource_matches_category(_obs("vital-signs"), "laboratory")


def test_cross_category_blocks_lab_in_vitals_path():
    """Vitals tool query must not surface lab-coded rows if server returns them anyway."""
    assert not observation_resource_matches_category(_obs("laboratory"), "vital-signs")


def test_empty_category_never_matches():
    assert not observation_resource_matches_category({"resourceType": "Observation"}, "laboratory")
    assert not observation_resource_matches_category({"resourceType": "Observation"}, "vital-signs")
