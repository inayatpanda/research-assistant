#!/usr/bin/env python3
"""Seed three realistic demo projects into a local Research Assistant backend.

The script is **idempotent**: every entity that supports a stable name (project
title, dataset filename, search query, screening article id, RoB article id,
checklist title, etc.) is looked up before being created. Re-running produces
the same end state — no duplicate rows.

Default mode targets a backend running with ``RMA_DISABLE_AUTH=1`` so the
script authenticates as the ``local-user`` legacy user. If your backend is
running with auth enabled, pass ``--email`` / ``--password`` so we sign in
through ``POST /api/auth/login`` (or fall back to ``signup`` on 401 if you
also pass ``--signup``).

Example:
    # backend is running with RMA_DISABLE_AUTH=1 (default dev mode)
    python scripts/seed_demo.py

    # auth-enabled backend (S1 session cookies)
    python scripts/seed_demo.py \\
        --base-url http://127.0.0.1:8787 \\
        --email demo@example.com --password "correcthorse" --signup

    # wipe seed projects and rebuild from scratch
    python scripts/seed_demo.py --force-reset

Three projects are produced:

  A. **Orthopaedics — systematic review of ACL reconstruction outcomes.**
     Frontmatter + 16 articles + PICO + 3 search records + 16 screening
     records + 10 RoB-2 assessments + 10 extraction records + 1 meta-analysis
     over 6 included studies + 3 GRADE outcomes + 1 PROSPERO draft +
     full manuscript draft + PRISMA-2020 checklist + bibliography.

  B. **General medicine — RCT of lisinopril for resistant hypertension.**
     Frontmatter + 5 background references + 40-patient masterchart dataset
     + 3 statistical analyses (independent-t, chi-square, linear regression)
     + CONSORT diagram + CONSORT-2010 checklist + cover letter + reviewer
     response stub + NEJM journal template.

  C. **Surgery — retrospective cohort of laparoscopic cholecystectomy.**
     Frontmatter + 5 references + 60-patient dataset + 3 analyses + STROBE
     cohort checklist + BJS journal template + 1 health-economics analysis.

This script makes **no** changes to backend code, no new pip deps, and uses
only the API surface that already supports CRUD by HTTP. It is safe to run
repeatedly during development.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

DEFAULT_BASE_URL = "http://127.0.0.1:8787"
DEFAULT_TIMEOUT = 60

# Stable mock identifiers — used in project titles so a lookup-by-title makes
# the seed idempotent. Keep these strings stable across runs.
SEED_TAG = "[SEED-DEMO]"
PROJECTS = {
    "ortho": f"{SEED_TAG} Anterior cruciate ligament reconstruction outcomes: a systematic review and meta-analysis",
    "rct": f"{SEED_TAG} Lisinopril vs placebo for resistant hypertension: a double-blind randomised controlled trial",
    "cohort": f"{SEED_TAG} Complication rates after elective laparoscopic cholecystectomy: a retrospective cohort study",
}


# ─── HTTP client ────────────────────────────────────────────────────────────


class ApiClient:
    """Thin authenticated session wrapper around ``requests``."""

    def __init__(self, base_url: str, *, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.timeout = timeout

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return self.base_url + path

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        params: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        expected: tuple[int, ...] = (200, 201, 204),
        allow_status: tuple[int, ...] = (),
    ) -> requests.Response:
        resp = self.session.request(
            method,
            self._url(path),
            json=json_body if files is None else None,
            params=params,
            files=files,
            timeout=self.timeout,
        )
        if resp.status_code in allow_status:
            return resp
        if resp.status_code not in expected:
            raise RuntimeError(
                f"{method} {path} -> {resp.status_code}: {resp.text[:500]}"
            )
        return resp

    def get(self, path: str, **kw: Any) -> Any:
        return self.request("GET", path, **kw).json()

    def post(self, path: str, body: Any | None = None, **kw: Any) -> Any:
        r = self.request("POST", path, json_body=body, **kw)
        if r.status_code == 204:
            return None
        return r.json()

    def patch(self, path: str, body: Any | None = None, **kw: Any) -> Any:
        return self.request("PATCH", path, json_body=body, **kw).json()

    def put(self, path: str, body: Any | None = None, **kw: Any) -> Any:
        return self.request("PUT", path, json_body=body, **kw).json()

    def delete(self, path: str, **kw: Any) -> None:
        self.request("DELETE", path, expected=(200, 204), **kw)

    # ── auth helpers ────────────────────────────────────────────────────

    def check_health(self) -> dict[str, Any]:
        return self.request("GET", "/api/health").json()

    def login_or_signup(
        self, email: str, password: str, *, allow_signup: bool
    ) -> dict[str, Any]:
        """Try login; if 401 and signup is permitted, signup instead."""
        r = self.session.post(
            self._url("/api/auth/login"),
            json={"email": email, "password": password},
            timeout=self.timeout,
        )
        if r.status_code == 200:
            return r.json()
        if r.status_code == 401 and allow_signup:
            r2 = self.session.post(
                self._url("/api/auth/signup"),
                json={
                    "email": email,
                    "password": password,
                    "display_name": email.split("@")[0],
                },
                timeout=self.timeout,
            )
            if r2.status_code in (200, 201):
                return r2.json()
            raise RuntimeError(f"signup failed: {r2.status_code} {r2.text[:300]}")
        raise RuntimeError(f"login failed: {r.status_code} {r.text[:300]}")


# ─── Generic upsert helpers ─────────────────────────────────────────────────


def find_project_by_title(client: ApiClient, title: str) -> dict | None:
    projects = client.get("/api/projects")
    for p in projects:
        if p.get("title") == title:
            return p
    return None


def get_or_create_project(
    client: ApiClient,
    *,
    title: str,
    study_type: str,
    citation_style: str = "vancouver",
    template_journal: str | None = None,
    target_journal: str | None = None,
    prospero_number: str | None = None,
    clinicaltrials_number: str | None = None,
) -> dict:
    existing = find_project_by_title(client, title)
    if existing:
        # PATCH to keep template / style up-to-date if they drift.
        patch: dict[str, Any] = {}
        if existing.get("citation_style") != citation_style:
            patch["citation_style"] = citation_style
        if existing.get("template_journal") != template_journal:
            patch["template_journal"] = template_journal
        if existing.get("target_journal") != target_journal:
            patch["target_journal"] = target_journal
        if prospero_number and existing.get("prospero_number") != prospero_number:
            patch["prospero_number"] = prospero_number
        if (
            clinicaltrials_number
            and existing.get("clinicaltrials_number") != clinicaltrials_number
        ):
            patch["clinicaltrials_number"] = clinicaltrials_number
        if patch:
            existing = client.patch(f"/api/projects/{existing['id']}", patch)
        return existing
    body: dict[str, Any] = {
        "title": title,
        "study_type": study_type,
        "citation_style": citation_style,
    }
    if template_journal:
        body["template_journal"] = template_journal
    if target_journal:
        body["target_journal"] = target_journal
    if prospero_number:
        body["prospero_number"] = prospero_number
    if clinicaltrials_number:
        body["clinicaltrials_number"] = clinicaltrials_number
    return client.post("/api/projects", body)


def upsert_section(
    client: ApiClient, project_id: str, section_name: str, content: str
) -> None:
    client.put(
        f"/api/projects/{project_id}/sections/{section_name}",
        {"section_name": section_name, "content": content},
    )


def upsert_frontmatter(
    client: ApiClient,
    project_id: str,
    *,
    funding: str,
    funders: list[dict[str, str]],
    ethics_irb: str | None,
    ethics_approval: str | None,
    ethics_consent: str | None,
    conflicts: str,
    abstract: dict[str, str],
) -> None:
    client.patch(
        f"/api/projects/{project_id}/frontmatter",
        {
            "funding_statement": funding,
            "funders": funders,
            "ethics_irb": ethics_irb,
            "ethics_approval_number": ethics_approval,
            "ethics_consent": ethics_consent,
            "conflicts_statement": conflicts,
            "structured_abstract_enabled": True,
            "structured_abstract": abstract,
        },
    )


def upsert_authors_and_affiliations(
    client: ApiClient,
    project_id: str,
    *,
    affiliations: list[dict[str, str]],
    authors: list[dict[str, Any]],
) -> tuple[list[dict], list[dict]]:
    # Idempotency: skip create if an affiliation with the same `name` exists.
    existing_affs = client.get(f"/api/projects/{project_id}/affiliations")
    aff_by_name = {a["name"]: a for a in existing_affs}
    created_affs: list[dict] = []
    for aff in affiliations:
        if aff["name"] in aff_by_name:
            created_affs.append(aff_by_name[aff["name"]])
        else:
            row = client.post(
                f"/api/projects/{project_id}/affiliations", aff
            )
            created_affs.append(row)

    existing_authors = client.get(f"/api/projects/{project_id}/authors")
    auth_by_name = {a["full_name"]: a for a in existing_authors}
    created_authors: list[dict] = []
    for author in authors:
        name = author["full_name"]
        if name in auth_by_name:
            created_authors.append(auth_by_name[name])
            continue
        body = {k: v for k, v in author.items() if k != "affiliations"}
        row = client.post(f"/api/projects/{project_id}/authors", body)
        # link each affiliation index
        aff_names = author.get("affiliations", [])
        for aff_name in aff_names:
            target = next(
                (a for a in created_affs if a["name"] == aff_name), None
            )
            if target is not None:
                client.post(
                    f"/api/authors/{row['id']}/affiliations/{target['id']}"
                )
        created_authors.append(row)
    return created_affs, created_authors


def import_articles(
    client: ApiClient, project_id: str, items: list[dict[str, Any]]
) -> list[dict]:
    """Bulk import via /articles/import-from-metadata. Idempotent thanks to
    the backend's DOI/PMID dedup."""
    if not items:
        return []
    # We MUST set source explicitly — backend Literal demands one of
    # ("upload", "doi", "pubmed", "ris", "bibtex", "manual").
    for item in items:
        item.setdefault("source", "manual")
    resp = client.post(
        f"/api/projects/{project_id}/articles/import-from-metadata",
        {"items": items},
    )
    return resp["created"] + resp["skipped_duplicates"]


def list_articles(client: ApiClient, project_id: str) -> list[dict]:
    return client.get(f"/api/projects/{project_id}/articles")


def upsert_review_pico(
    client: ApiClient,
    project_id: str,
    *,
    population: str,
    intervention: str,
    comparator: str,
    outcome: str,
    inclusion: str,
    exclusion: str,
) -> dict:
    return client.patch(
        f"/api/projects/{project_id}/reviews",
        {
            "pico_population": population,
            "pico_intervention": intervention,
            "pico_comparator": comparator,
            "pico_outcome": outcome,
            "eligibility_inclusion": inclusion,
            "eligibility_exclusion": exclusion,
        },
    )


def upsert_search_records(
    client: ApiClient,
    project_id: str,
    records: list[dict[str, Any]],
) -> list[dict]:
    existing = client.get(f"/api/projects/{project_id}/reviews/search")
    by_key = {(r["database_name"], r["query_string"]): r for r in existing}
    out: list[dict] = []
    for rec in records:
        key = (rec["database_name"], rec["query_string"])
        if key in by_key:
            out.append(by_key[key])
            continue
        out.append(
            client.post(f"/api/projects/{project_id}/reviews/search", rec)
        )
    return out


def upsert_screening(
    client: ApiClient, project_id: str, records: list[dict[str, Any]]
) -> list[dict]:
    """upsert_screening uses the article_id as the natural key — POST is itself
    an upsert per backend semantics, so we can post unconditionally."""
    out: list[dict] = []
    for rec in records:
        out.append(
            client.post(
                f"/api/projects/{project_id}/reviews/screening", rec
            )
        )
    return out


def upsert_rob(
    client: ApiClient, project_id: str, records: list[dict[str, Any]]
) -> list[dict]:
    out: list[dict] = []
    for rec in records:
        out.append(
            client.post(f"/api/projects/{project_id}/reviews/rob", rec)
        )
    return out


def upsert_extraction(
    client: ApiClient, project_id: str, records: list[dict[str, Any]]
) -> list[dict]:
    out: list[dict] = []
    for rec in records:
        out.append(
            client.post(
                f"/api/projects/{project_id}/reviews/extraction", rec
            )
        )
    return out


def upsert_dataset_csv(
    client: ApiClient,
    project_id: str,
    *,
    filename: str,
    csv_text: str,
) -> dict:
    existing = client.get(f"/api/projects/{project_id}/datasets")
    for d in existing:
        if d.get("filename") == filename:
            return d
    files = {"file": (filename, csv_text.encode("utf-8"), "text/csv")}
    r = client.request(
        "POST",
        f"/api/projects/{project_id}/datasets",
        files=files,
        expected=(200, 201),
    )
    return r.json()


def list_analyses(client: ApiClient, project_id: str, dataset_id: str) -> list[dict]:
    return client.get(
        f"/api/projects/{project_id}/datasets/{dataset_id}/analyses"
    )


def create_and_run_analysis(
    client: ApiClient,
    project_id: str,
    dataset_id: str,
    *,
    question_type: str,
    chosen_test: str,
    variables: dict[str, Any],
    label_marker: str,
) -> dict:
    """Idempotent: looks for an analysis with matching (test, variables)."""
    existing = list_analyses(client, project_id, dataset_id)
    for a in existing:
        if (
            a.get("chosen_test") == chosen_test
            and a.get("variables") == variables
        ):
            # Already created. Only run if no result yet.
            if a.get("result") is None:
                try:
                    return client.post(
                        f"/api/projects/{project_id}/analyses/{a['id']}/run"
                    )
                except Exception as exc:
                    print(f"      [warn] run failed for {label_marker}: {exc}")
                    return a
            return a
    created = client.post(
        f"/api/projects/{project_id}/datasets/{dataset_id}/analyses",
        {
            "question_type": question_type,
            "chosen_test": chosen_test,
            "variables": variables,
        },
    )
    try:
        ran = client.post(
            f"/api/projects/{project_id}/analyses/{created['id']}/run"
        )
        return ran
    except Exception as exc:
        print(f"      [warn] run failed for {label_marker}: {exc}")
        return created


def upsert_meta_analysis(
    client: ApiClient,
    project_id: str,
    *,
    title: str,
    effect_metric: str,
    model: str,
    inputs: list[dict[str, Any]],
) -> dict:
    existing = client.get(f"/api/projects/{project_id}/reviews/meta")
    for m in existing:
        if m.get("title") == title:
            return m
    return client.post(
        f"/api/projects/{project_id}/reviews/meta",
        {
            "title": title,
            "effect_metric": effect_metric,
            "model": model,
            "inputs": inputs,
        },
    )


def upsert_grade(
    client: ApiClient, project_id: str, assessments: list[dict[str, Any]]
) -> list[dict]:
    # POST is upsert by outcome_label. The route lives under .../review/grade
    # (see routes/grade.py — MP14).
    out: list[dict] = []
    for a in assessments:
        out.append(client.post(f"/api/projects/{project_id}/review/grade", a))
    return out


def upsert_prospero(client: ApiClient, project_id: str, fields: dict[str, str]) -> dict:
    return client.patch(
        f"/api/projects/{project_id}/review/prospero",
        {"fields": fields},
    )


def upsert_consort(client: ApiClient, project_id: str, data: dict[str, Any]) -> dict:
    return client.patch(f"/api/projects/{project_id}/consort", data)


def upsert_checklist_run(
    client: ApiClient,
    project_id: str,
    *,
    checklist_key: str,
    title: str,
    item_decisions: dict[str, dict[str, str]] | None = None,
) -> dict:
    existing = client.get(f"/api/projects/{project_id}/checklists")
    found = next(
        (
            r
            for r in existing
            if r.get("checklist_key") == checklist_key and r.get("title") == title
        ),
        None,
    )
    if found is None:
        created = client.post(
            f"/api/projects/{project_id}/checklists",
            {"checklist_key": checklist_key, "title": title},
        )
        run_id = created["id"]
    else:
        run_id = found["id"]

    if item_decisions:
        for item_id, patch in item_decisions.items():
            try:
                client.patch(
                    f"/api/projects/{project_id}/checklists/{run_id}/items/{item_id}",
                    patch,
                )
            except Exception as exc:
                # Item id might not exist for this checklist; skip silently.
                pass
    return client.get(f"/api/projects/{project_id}/checklists/{run_id}")


def upsert_cover_letter(
    client: ApiClient,
    project_id: str,
    *,
    target_journal: str,
    novelty_points: list[str],
    body_html: str,
) -> dict:
    return client.patch(
        f"/api/projects/{project_id}/cover-letter",
        {
            "target_journal": target_journal,
            "novelty_points": novelty_points,
            "body_html": body_html,
        },
    )


# ─── Data builders — Project A: Ortho SR ────────────────────────────────────


ORTHO_AFFILIATIONS = [
    {
        "name": "Department of Orthopaedic Surgery, Royal National Orthopaedic Hospital",
        "city": "Stanmore",
        "country": "United Kingdom",
    },
    {
        "name": "Institute of Orthopaedics and Musculoskeletal Science, University College London",
        "city": "London",
        "country": "United Kingdom",
    },
    {
        "name": "Centre for Sports and Exercise Medicine, Queen Mary University of London",
        "city": "London",
        "country": "United Kingdom",
    },
]


ORTHO_AUTHORS = [
    {
        "full_name": "Sarah J. Whitfield",
        "given_name": "Sarah",
        "family_name": "Whitfield",
        "is_corresponding": True,
        "email": "sarah.whitfield@example.ac.uk",
        "affiliations": [ORTHO_AFFILIATIONS[0]["name"], ORTHO_AFFILIATIONS[1]["name"]],
    },
    {
        "full_name": "Daniel A. McKenzie",
        "given_name": "Daniel",
        "family_name": "McKenzie",
        "affiliations": [ORTHO_AFFILIATIONS[0]["name"]],
    },
    {
        "full_name": "Priya R. Shah",
        "given_name": "Priya",
        "family_name": "Shah",
        "affiliations": [ORTHO_AFFILIATIONS[2]["name"]],
    },
    {
        "full_name": "Marcus T. Henderson",
        "given_name": "Marcus",
        "family_name": "Henderson",
        "affiliations": [ORTHO_AFFILIATIONS[1]["name"]],
    },
]


ORTHO_ARTICLES: list[dict[str, Any]] = [
    {
        "title": "Patellar tendon versus hamstring tendon autograft for anterior cruciate ligament reconstruction: a systematic review and meta-analysis",
        "authors": ["Mohtadi NG", "Chan DS", "Dainty KN", "Whelan DB"],
        "journal": "Cochrane Database of Systematic Reviews",
        "year": 2011,
        "doi": "10.1002/14651858.CD005960.pub2",
        "abstract": (
            "Background: Anterior cruciate ligament (ACL) rupture is a common knee injury that "
            "often requires surgical reconstruction. The two most common autograft choices are "
            "patellar tendon (BPTB) and hamstring tendon (HT). Methods: We searched the Cochrane "
            "Bone, Joint and Muscle Trauma Group Specialised Register, CENTRAL, MEDLINE, EMBASE and "
            "trials registers. Results: 19 trials with 1597 participants were included. There was "
            "no statistically significant difference between BPTB and HT in functional outcome, but "
            "BPTB grafts produced more anterior knee pain and kneeling discomfort."
        ),
    },
    {
        "title": "Outcomes of anterior cruciate ligament reconstruction at 20 years' follow-up: a prospective cohort study",
        "authors": ["Pinczewski LA", "Lyman J", "Salmon LJ", "Russell VJ", "Roe J", "Linklater J"],
        "journal": "American Journal of Sports Medicine",
        "year": 2018,
        "doi": "10.1177/0363546518758027",
        "abstract": (
            "Background: Long-term outcomes after ACL reconstruction are essential to counsel "
            "patients. We report 20-year outcomes in a prospective cohort of 200 patients treated "
            "with either BPTB or HT autograft. Methods: Patients were assessed clinically, "
            "radiographically, and with patient-reported outcomes. Results: 78% of patients "
            "returned to their pre-injury level of sport. Radiographic OA was present in 51% of "
            "operated knees vs 16% of contralateral knees (p<0.001)."
        ),
    },
    {
        "title": "Return to sport after anterior cruciate ligament reconstruction: a systematic review and meta-analysis of the state of play",
        "authors": ["Ardern CL", "Webster KE", "Taylor NF", "Feller JA"],
        "journal": "British Journal of Sports Medicine",
        "year": 2014,
        "doi": "10.1136/bjsports-2013-093398",
        "abstract": (
            "We systematically reviewed return-to-sport rates after ACL reconstruction across 48 "
            "studies including 5770 participants. 81% returned to any sport, 65% to pre-injury "
            "level, but only 55% to competitive sport. Younger age, male sex and elite-level "
            "preinjury sport were associated with higher return rates."
        ),
    },
    {
        "title": "Anterior cruciate ligament reconstruction with bone-patellar tendon-bone autograft compared with allograft: a meta-analysis of randomised trials",
        "authors": ["Tibor LM", "Long JL", "Schilling PL", "Lilly RJ", "Carpenter JE", "Miller BS"],
        "journal": "Journal of Bone and Joint Surgery (American Volume)",
        "year": 2010,
        "doi": "10.2106/JBJS.I.01506",
        "abstract": (
            "We pooled five randomised trials (n=448). Allograft reconstruction was associated "
            "with slightly higher graft rupture rates (relative risk 1.96, 95% CI 1.07 to 3.60) "
            "than BPTB autograft, with no significant difference in Lysholm or IKDC scores."
        ),
    },
    {
        "title": "Early versus delayed reconstruction of the anterior cruciate ligament: a meta-analysis of randomised controlled trials",
        "authors": ["Smith TO", "Davies L", "Hing CB"],
        "journal": "Knee Surgery, Sports Traumatology, Arthroscopy",
        "year": 2010,
        "doi": "10.1007/s00167-010-1116-2",
        "abstract": (
            "We pooled four randomised trials comparing early (<6 weeks) versus delayed (>10 "
            "weeks) ACL reconstruction. No statistically significant difference was detected in "
            "IKDC or Tegner scores at 24 months."
        ),
    },
    {
        "title": "Single-bundle versus double-bundle ACL reconstruction: a systematic review and meta-analysis of randomised controlled trials",
        "authors": ["Tiamklang T", "Sumanont S", "Foocharoen T", "Laopaiboon M"],
        "journal": "Cochrane Database of Systematic Reviews",
        "year": 2012,
        "doi": "10.1002/14651858.CD008413.pub2",
        "abstract": (
            "Seventeen RCTs (1433 participants) were pooled. Double-bundle reconstruction produced "
            "modest improvements in rotational stability (pivot-shift) but no statistically "
            "significant difference in IKDC, Lysholm, or graft failure rate."
        ),
    },
    {
        "title": "Quadriceps tendon autograft for anterior cruciate ligament reconstruction: a systematic review",
        "authors": ["Slone HS", "Romine SE", "Premkumar A", "Xerogeanes JW"],
        "journal": "Arthroscopy",
        "year": 2015,
        "doi": "10.1016/j.arthro.2014.11.010",
        "abstract": (
            "Twenty-seven studies (1845 participants) reported good knee stability after quadriceps "
            "tendon autograft (mean side-to-side difference 1.4 mm). Donor-site morbidity was "
            "lower than BPTB; failure rate was comparable to hamstring autograft."
        ),
    },
    {
        "title": "Rehabilitation after anterior cruciate ligament injury and reconstruction: a randomised comparison of accelerated and non-accelerated protocols",
        "authors": ["Beynnon BD", "Uh BS", "Johnson RJ", "Abate JA"],
        "journal": "American Journal of Sports Medicine",
        "year": 2011,
        "doi": "10.1177/0363546511402544",
        "abstract": (
            "RCT of 25 patients randomised to accelerated vs non-accelerated rehab. No "
            "between-group difference in KT-1000 laxity or single-legged hop performance at "
            "two-year follow-up."
        ),
    },
    {
        "title": "Graft rupture after anterior cruciate ligament reconstruction: a population-based cohort study",
        "authors": ["Magnussen RA", "Lawrence JT", "West RL", "Toth AP", "Taylor DC", "Garrett WE"],
        "journal": "American Journal of Sports Medicine",
        "year": 2012,
        "doi": "10.1177/0363546511431564",
        "abstract": (
            "We reviewed 7556 ACL reconstructions across the Norwegian National Knee Ligament "
            "Registry. Two-year graft revision rate was 1.4%. Hamstring autograft and younger age "
            "were independent predictors of revision."
        ),
    },
    {
        "title": "Comparison of patient-reported outcomes after ACL reconstruction with hamstring vs patellar tendon autograft: a randomised controlled trial",
        "authors": ["Aglietti P", "Giron F", "Buzzi R", "Biddau F", "Sasso F"],
        "journal": "American Journal of Sports Medicine",
        "year": 2009,
        "doi": "10.1177/0363546509336135",
        "abstract": (
            "120 patients were randomised to BPTB or HT autograft. At 5 years, IKDC scores were "
            "comparable (84.1 vs 82.9). BPTB patients reported more anterior knee pain at "
            "kneeling."
        ),
    },
    {
        "title": "Tibial fixation in anterior cruciate ligament reconstruction with bioabsorbable interference screws: a prospective trial",
        "authors": ["Kurosaka M", "Yoshiya S", "Andrish JT"],
        "journal": "Journal of Bone and Joint Surgery (British Volume)",
        "year": 2009,
        "doi": "10.1302/0301-620X.91B5.21345",
        "abstract": (
            "108 participants underwent ACL reconstruction with bioabsorbable interference screws. "
            "At minimum 2-year follow-up, mean side-to-side laxity difference was 1.8 mm; no "
            "screw-related complications were noted."
        ),
    },
    {
        "title": "Quadriceps strength deficit after anterior cruciate ligament reconstruction: a systematic review",
        "authors": ["Palmieri-Smith RM", "Lepley LK"],
        "journal": "Sports Health",
        "year": 2015,
        "doi": "10.1177/1941738114554406",
        "abstract": (
            "30 studies measuring isokinetic quadriceps strength after ACL reconstruction. Mean "
            "between-limb deficit was 12% at six months and 6% at 12 months, irrespective of "
            "graft type."
        ),
    },
    {
        "title": "Risk factors for re-injury after primary anterior cruciate ligament reconstruction: a systematic review",
        "authors": ["Wiggins AJ", "Grandhi RK", "Schneider DK", "Stanfield D", "Webster KE", "Myer GD"],
        "journal": "American Journal of Sports Medicine",
        "year": 2016,
        "doi": "10.1177/0363546515621554",
        "abstract": (
            "We synthesized 19 studies (n=15,304). Age under 25 was associated with a 22% "
            "second-injury rate vs 11% for older patients. Return-to-sport criteria were poorly "
            "standardised across included studies."
        ),
    },
    {
        "title": "Posterior cruciate ligament-preserving versus substituting total knee arthroplasty: a meta-analysis",
        "authors": ["Verra WC", "van den Boom LGH", "Jacobs W", "Clement DJ", "Wymenga AAB", "Nelissen RG"],
        "journal": "Cochrane Database of Systematic Reviews",
        "year": 2013,
        "doi": "10.1002/14651858.CD004803.pub3",
        "abstract": (
            "Pooled 17 trials of CR vs PS TKA; no clinically meaningful difference in range of "
            "motion or knee scores. (Included here as off-topic exclusion exemplar.)"
        ),
    },
    {
        "title": "Posterior tibial slope and graft failure after primary ACL reconstruction: a prospective cohort study",
        "authors": ["Webb JM", "Salmon LJ", "Leclerc E", "Pinczewski LA"],
        "journal": "American Journal of Sports Medicine",
        "year": 2013,
        "doi": "10.1177/0363546513504286",
        "abstract": (
            "200 patients followed for 15 years. Posterior tibial slope >12° was associated with "
            "a four-fold higher risk of graft re-rupture (HR 4.1, 95% CI 1.6 to 10.7)."
        ),
    },
    {
        "title": "Computer-navigated versus conventional anterior cruciate ligament reconstruction: a randomised trial",
        "authors": ["Plaweski S", "Cazal J", "Rosell P", "Merloz P"],
        "journal": "Arthroscopy",
        "year": 2006,
        "doi": "10.1016/j.arthro.2006.05.024",
        "abstract": (
            "60 patients randomised. Computer navigation reduced KT-1000 side-to-side laxity by "
            "an average of 1.1 mm but with no measurable improvement in IKDC at one year."
        ),
    },
]


ORTHO_SEARCH_RECORDS = [
    {
        "database_name": "PubMed",
        "query_string": (
            "((\"Anterior Cruciate Ligament\"[MeSH] OR \"ACL reconstruction\"[tw]) "
            "AND (autograft[tw] OR \"patellar tendon\"[tw] OR \"hamstring tendon\"[tw])) "
            "AND (\"meta-analysis\"[pt] OR \"randomized controlled trial\"[pt] OR \"cohort studies\"[MeSH])"
        ),
        "date_searched": "2026-03-12T10:00:00+00:00",
        "n_results": 412,
        "notes": "Last 15 years; humans; English language",
    },
    {
        "database_name": "Embase",
        "query_string": (
            "('anterior cruciate ligament reconstruction'/exp OR 'acl reconstruction':ti,ab) "
            "AND ('autograft'/exp OR 'patellar tendon':ti,ab OR 'hamstring graft':ti,ab) "
            "AND ([cochrane review]/lim OR [randomized controlled trial]/lim OR [cohort analysis]/lim)"
        ),
        "date_searched": "2026-03-12T10:30:00+00:00",
        "n_results": 287,
        "notes": "Embase syntax via Ovid; 2011–2026",
    },
    {
        "database_name": "Cochrane",
        "query_string": (
            "MeSH descriptor: [Anterior Cruciate Ligament] explode all trees AND "
            "(reconstruct* OR autograft OR allograft)"
        ),
        "date_searched": "2026-03-12T11:00:00+00:00",
        "n_results": 76,
        "notes": "CENTRAL — Cochrane Bone, Joint and Muscle Trauma Group register",
    },
]


# Mapping from article index → screening decision config. Articles index 13
# is included as the off-topic (PCL TKA) study so the screening exemplifies
# a sensible exclusion-with-reason.
ORTHO_SCREENING_PLAN: list[dict[str, Any]] = [
    {"idx": 0, "stage": "full_text", "decision": "include"},
    {"idx": 1, "stage": "full_text", "decision": "include"},
    {"idx": 2, "stage": "full_text", "decision": "include"},
    {"idx": 3, "stage": "full_text", "decision": "include"},
    {"idx": 4, "stage": "full_text", "decision": "include"},
    {"idx": 5, "stage": "full_text", "decision": "include"},
    {"idx": 6, "stage": "full_text", "decision": "include"},
    {"idx": 7, "stage": "full_text", "decision": "include"},
    {"idx": 8, "stage": "full_text", "decision": "include"},
    {"idx": 9, "stage": "full_text", "decision": "include"},
    {
        "idx": 10, "stage": "title_abstract", "decision": "maybe",
        "reason": "Single-arm prospective trial — eligibility ambiguous on outcome",
    },
    {"idx": 11, "stage": "full_text", "decision": "include"},
    {"idx": 12, "stage": "full_text", "decision": "include"},
    {
        "idx": 13, "stage": "title_abstract", "decision": "exclude",
        "exclusion_category": "intervention",
        "reason": "Total knee arthroplasty population — not ACL reconstruction",
    },
    {"idx": 14, "stage": "full_text", "decision": "include"},
    {
        "idx": 15, "stage": "title_abstract", "decision": "exclude",
        "exclusion_category": "study_design",
        "reason": "Single-centre, < 60 participants; underpowered for primary outcome",
    },
]


# Six studies enter the meta-analysis (continuous outcome: IKDC at 24 months,
# graft type comparison). Numbers are illustrative but plausible.
ORTHO_META_INPUTS_BLUEPRINT = [
    {"label": "Mohtadi 2011", "idx": 0, "mean_a": 84.1, "sd_a": 12.3, "n_a": 158, "mean_b": 82.6, "sd_b": 13.8, "n_b": 162},
    {"label": "Pinczewski 2018", "idx": 1, "mean_a": 86.4, "sd_a": 10.9, "n_a": 100, "mean_b": 81.2, "sd_b": 11.5, "n_b": 100},
    {"label": "Tibor 2010", "idx": 3, "mean_a": 87.0, "sd_a": 9.6, "n_a": 71, "mean_b": 82.8, "sd_b": 10.4, "n_b": 76},
    {"label": "Aglietti 2009", "idx": 9, "mean_a": 84.1, "sd_a": 11.7, "n_a": 60, "mean_b": 82.9, "sd_b": 12.0, "n_b": 60},
    {"label": "Kurosaka 2009", "idx": 10, "mean_a": 80.5, "sd_a": 14.1, "n_a": 54, "mean_b": 79.8, "sd_b": 13.4, "n_b": 54},
    {"label": "Beynnon 2011", "idx": 7, "mean_a": 81.7, "sd_a": 12.2, "n_a": 26, "mean_b": 80.9, "sd_b": 12.5, "n_b": 27},
]


def build_ortho_manuscript_sections() -> dict[str, str]:
    return {
        "Abstract": (
            "<p><strong>Background.</strong> Anterior cruciate ligament (ACL) injury is one of the "
            "most common ligamentous knee injuries; the optimal reconstruction strategy remains "
            "debated despite four decades of research.</p>"
            "<p><strong>Objectives.</strong> To systematically review randomised and observational "
            "evidence comparing autograft choices, fixation, and rehabilitation pathways after "
            "primary ACL reconstruction.</p>"
            "<p><strong>Methods.</strong> We searched PubMed, Embase, and the Cochrane CENTRAL "
            "Register on 12 March 2026. Two reviewers independently screened titles/abstracts and "
            "full texts, extracted data, and assessed risk of bias using RoB 2 for trials and "
            "ROBINS-I for cohorts. We pooled continuous outcomes using a random-effects model "
            "(DerSimonian–Laird) and explored heterogeneity with I² and tau².</p>"
            "<p><strong>Results.</strong> Of 775 records, 12 studies (n=1,623) met inclusion. "
            "Pooled IKDC score at 24 months favoured bone-patellar tendon-bone over hamstring "
            "autograft by a mean difference of 2.4 points (95% CI 0.6 to 4.2; I²=38%).</p>"
            "<p><strong>Conclusions.</strong> Both BPTB and hamstring autografts produce comparable "
            "patient-reported outcomes; subtle differences exist in side-to-side laxity and "
            "anterior knee pain that should be discussed during shared decision-making.</p>"
        ),
        "Introduction": (
            "<p>The anterior cruciate ligament (ACL) is the principal restraint to anterior tibial "
            "translation and a critical contributor to rotational knee stability. ACL injury "
            "incidence has been estimated between 30 and 78 per 100,000 person-years, with the "
            "highest rates in young athletes participating in pivoting sports. Surgical "
            "reconstruction remains the standard of care for active patients, with the goal of "
            "restoring stability and enabling return to sport.</p>"
            "<p>Despite consistent peri-operative protocols, debate persists over autograft choice, "
            "single- versus double-bundle technique, fixation, and rehabilitation tempo. Bone-"
            "patellar tendon-bone (BPTB) autograft, hamstring tendon (HT) autograft, and "
            "quadriceps tendon (QT) autograft each have distinct mechanical and donor-site "
            "profiles. While prior systematic reviews have addressed individual comparisons, "
            "few have integrated the full spectrum of evidence across graft choice and "
            "post-operative rehabilitation pathways.</p>"
            "<p>This systematic review and meta-analysis was therefore commissioned to (1) "
            "compare patient-reported outcomes after BPTB and HT autograft reconstruction; (2) "
            "characterise risk of graft re-rupture and revision; and (3) appraise the methodological "
            "quality of the contemporary evidence base.</p>"
        ),
        "Methodology": (
            "<p>The review was registered prospectively on PROSPERO (CRD42026512098) and follows "
            "the PRISMA 2020 statement. We searched PubMed, Embase, and the Cochrane CENTRAL "
            "Register from inception to 12 March 2026 using a strategy combining MeSH and free "
            "text terms for anterior cruciate ligament, reconstruction, and graft choice. The "
            "full search strategy is reproduced in Supplementary Table S1.</p>"
            "<p><strong>Eligibility criteria.</strong> We included randomised controlled trials and "
            "prospective cohort studies in which adults underwent primary ACL reconstruction with "
            "either BPTB, HT or QT autograft. Outcomes of interest were the IKDC subjective knee "
            "score at 24 months, KT-1000 side-to-side laxity, anterior knee pain on kneeling, "
            "and graft re-rupture. We excluded conference abstracts, single-centre series with "
            "fewer than 30 participants, and studies of revision or paediatric reconstruction.</p>"
            "<p><strong>Screening and data extraction.</strong> Two reviewers (SJW, DAM) "
            "independently screened titles and abstracts, then full texts, using Covidence. "
            "Disagreements were resolved by discussion or by a third reviewer (PRS). Data were "
            "extracted into a pre-piloted form covering study design, population, graft, follow-up "
            "duration, outcomes and adverse events.</p>"
            "<p><strong>Risk of bias.</strong> We used the Cochrane Risk of Bias 2 tool for "
            "randomised trials and ROBINS-I for non-randomised studies. Two assessors completed "
            "independent ratings; disagreements were resolved by consensus.</p>"
            "<p><strong>Synthesis.</strong> Continuous outcomes were pooled using a random-effects "
            "DerSimonian–Laird model with restricted maximum likelihood estimation of tau². "
            "Heterogeneity was quantified with I². Sensitivity analyses included leave-one-out "
            "and restricted analysis to studies at low risk of bias. Funnel-plot asymmetry was "
            "explored with Egger's regression. All analyses were performed in Research Assistant.</p>"
        ),
        "Results": (
            "<p>The PRISMA flow is summarised in Figure 1. The search identified 775 records "
            "after de-duplication, of which 96 were screened at full text and 12 were included in "
            "the synthesis (n=1,623 participants). Included studies comprised 8 randomised trials "
            "and 4 prospective cohorts, with median follow-up of 36 months (IQR 24–60).</p>"
            "<p><strong>Patient-reported outcomes.</strong> The pooled mean difference in IKDC "
            "subjective knee score at 24 months favoured BPTB over HT by 2.4 points "
            "(95% CI 0.6 to 4.2; six studies; I²=38%). The effect was attenuated when restricted "
            "to studies at low risk of bias (MD 1.9 points, 95% CI -0.1 to 3.9).</p>"
            "<p><strong>Laxity.</strong> Eight studies (n=987) reported KT-1000 side-to-side "
            "difference. Pooled mean side-to-side laxity was 1.6 mm (95% CI 1.3 to 1.9) and "
            "did not differ significantly between graft types.</p>"
            "<p><strong>Graft re-rupture.</strong> Five studies (n=8,432) reported graft re-rupture. "
            "The pooled risk ratio for HT vs BPTB was 1.31 (95% CI 0.92 to 1.86). Younger age "
            "(&lt;25 years) and high posterior tibial slope were consistent independent predictors.</p>"
            "<p><strong>Risk of bias.</strong> Of the eight RCTs, five were judged at low risk "
            "of bias overall, two raised some concerns (most often around deviations from "
            "intended interventions), and one was at high risk due to unblinded outcome assessment.</p>"
        ),
        "Discussion": (
            "<p>This systematic review summarises contemporary evidence comparing autograft choice "
            "after primary ACL reconstruction. The principal finding is that BPTB autograft "
            "confers a small but statistically detectable advantage in IKDC at 24 months, while "
            "incurring more donor-site anterior knee pain at kneeling. The clinical relevance of "
            "a 2-point IKDC difference is debatable, sitting just below the published minimal "
            "clinically important difference of 6.3.</p>"
            "<p>Our findings broadly align with the 2011 Cochrane review by Mohtadi and "
            "colleagues but extend the evidence base with longer-term cohort data, including the "
            "20-year Sydney series. Differences in graft re-rupture were not statistically "
            "significant in this synthesis, although registry data suggest a small but consistent "
            "increase in revision risk with hamstring autograft in young athletes.</p>"
            "<p><strong>Strengths.</strong> We followed the PRISMA 2020 statement, prospectively "
            "registered the protocol, used dual independent screening and extraction, and "
            "appraised risk of bias with current tools. <strong>Limitations.</strong> Most "
            "included studies were single-centre, heterogeneity in rehabilitation protocols was "
            "considerable, and we did not formally evaluate cost-effectiveness.</p>"
            "<p><strong>Implications for practice.</strong> Surgeons should counsel patients about "
            "the modest IKDC advantage of BPTB grafts against the higher prevalence of anterior "
            "knee pain. <strong>Implications for research.</strong> Future trials should employ "
            "standardised outcomes (IKDC, Marx activity, KOOS-Sport/Rec), report longer follow-up, "
            "and prespecify return-to-sport criteria before the index procedure.</p>"
        ),
        "Conclusion": (
            "<p>In adults undergoing primary ACL reconstruction, bone-patellar tendon-bone "
            "autograft produces marginally superior IKDC subjective knee scores compared with "
            "hamstring tendon autograft at 24 months, with comparable laxity and graft re-rupture "
            "rates. The clinical relevance of the IKDC difference is small and should be balanced "
            "against the higher prevalence of anterior knee pain after BPTB graft harvest.</p>"
        ),
    }


# ─── Project B: RCT (lisinopril) ─────────────────────────────────────────────


RCT_AFFILIATIONS = [
    {
        "name": "Division of Cardiovascular Medicine, John Radcliffe Hospital",
        "city": "Oxford",
        "country": "United Kingdom",
    },
    {
        "name": "Nuffield Department of Population Health, University of Oxford",
        "city": "Oxford",
        "country": "United Kingdom",
    },
]


RCT_AUTHORS = [
    {
        "full_name": "Elena R. Marshall",
        "given_name": "Elena",
        "family_name": "Marshall",
        "is_corresponding": True,
        "email": "elena.marshall@example.ac.uk",
        "affiliations": [RCT_AFFILIATIONS[0]["name"]],
    },
    {
        "full_name": "James K. Adebayo",
        "given_name": "James",
        "family_name": "Adebayo",
        "affiliations": [RCT_AFFILIATIONS[1]["name"]],
    },
    {
        "full_name": "Hannah F. O'Brien",
        "given_name": "Hannah",
        "family_name": "O'Brien",
        "affiliations": [RCT_AFFILIATIONS[0]["name"]],
    },
]


RCT_REFERENCES: list[dict[str, Any]] = [
    {
        "title": "2018 ESC/ESH Guidelines for the management of arterial hypertension",
        "authors": ["Williams B", "Mancia G", "Spiering W", "Agabiti Rosei E"],
        "journal": "European Heart Journal",
        "year": 2018,
        "doi": "10.1093/eurheartj/ehy339",
    },
    {
        "title": "Resistant hypertension: detection, evaluation, and management: a scientific statement from the American Heart Association",
        "authors": ["Carey RM", "Calhoun DA", "Bakris GL", "Brook RD"],
        "journal": "Hypertension",
        "year": 2018,
        "doi": "10.1161/HYP.0000000000000084",
    },
    {
        "title": "Effects of intensive blood pressure lowering on cardiovascular and renal outcomes",
        "authors": ["SPRINT Research Group"],
        "journal": "New England Journal of Medicine",
        "year": 2015,
        "doi": "10.1056/NEJMoa1511939",
    },
    {
        "title": "Spironolactone versus placebo, bisoprolol, and doxazosin to determine the optimal treatment for drug-resistant hypertension (PATHWAY-2)",
        "authors": ["Williams B", "MacDonald TM", "Morant S", "Webb DJ", "Sever P"],
        "journal": "The Lancet",
        "year": 2015,
        "doi": "10.1016/S0140-6736(15)00257-3",
    },
    {
        "title": "Heart disease and stroke statistics-2024 update: a report from the American Heart Association",
        "authors": ["Tsao CW", "Aday AW", "Almarzooq ZI"],
        "journal": "Circulation",
        "year": 2024,
        "doi": "10.1161/CIR.0000000000001209",
    },
]


def build_rct_csv() -> str:
    """Realistic 40-patient masterchart. Seed RNG for repeatability."""
    random.seed(20250521)
    lines = ["id,age,sex,baseline_sbp,week_12_sbp,group,adverse_event"]
    for i in range(1, 41):
        age = random.randint(45, 78)
        sex = random.choice(["M", "F"])
        baseline = random.randint(150, 178)
        if i % 2 == 0:  # lisinopril
            group = "lisinopril"
            # average ~-14 mmHg with sd 7
            change = -int(random.gauss(14, 7))
            ae = "yes" if random.random() < 0.20 else "no"
        else:
            group = "placebo"
            change = -int(random.gauss(2, 6))
            ae = "yes" if random.random() < 0.10 else "no"
        week12 = max(110, baseline + change)
        lines.append(f"{i},{age},{sex},{baseline},{week12},{group},{ae}")
    return "\n".join(lines) + "\n"


def build_rct_manuscript_sections() -> dict[str, str]:
    return {
        "Abstract": (
            "<p><strong>Background.</strong> Resistant hypertension affects approximately 10% of "
            "treated hypertensive adults and confers substantial cardiovascular risk despite "
            "multi-agent therapy.</p>"
            "<p><strong>Methods.</strong> We conducted a single-centre, double-blind, "
            "placebo-controlled randomised trial of add-on lisinopril 20 mg daily versus matched "
            "placebo in 40 adults with confirmed resistant hypertension. The primary outcome was "
            "change in 24-hour ambulatory systolic blood pressure at 12 weeks.</p>"
            "<p><strong>Results.</strong> Lisinopril reduced systolic blood pressure by a mean of "
            "13.6 mmHg compared with 2.1 mmHg in the placebo arm (mean difference 11.5 mmHg, 95% "
            "CI 7.4 to 15.6; p&lt;0.001). Adverse events were uncommon and similar between arms.</p>"
            "<p><strong>Conclusions.</strong> In adults with resistant hypertension, add-on "
            "lisinopril produces a clinically meaningful reduction in systolic blood pressure at "
            "12 weeks.</p>"
        ),
        "Introduction": (
            "<p>Resistant hypertension — blood pressure that remains above goal despite the "
            "concurrent use of three antihypertensive agents from different classes, one of which "
            "is a diuretic — is associated with a substantially elevated risk of stroke, heart "
            "failure and cardiovascular death. Despite the introduction of mineralocorticoid "
            "receptor antagonists as a fourth-line agent following the PATHWAY-2 trial, a "
            "subset of patients remains hypertensive on quadruple therapy, and additional add-on "
            "agents are needed.</p>"
            "<p>The angiotensin-converting enzyme inhibitor lisinopril is an inexpensive, widely "
            "available agent with established cardiovascular benefits. However, its incremental "
            "value when added on top of a maximally tolerated multi-drug regimen has not been "
            "rigorously evaluated. We therefore conducted a randomised, double-blind, "
            "placebo-controlled trial to test the hypothesis that add-on lisinopril reduces 24-hour "
            "ambulatory systolic blood pressure at 12 weeks compared with placebo.</p>"
        ),
        "Methodology": (
            "<p>This was a single-centre, double-blind, placebo-controlled, parallel-group "
            "randomised trial registered prospectively on ClinicalTrials.gov (NCT04451234). The "
            "trial protocol was approved by the local research ethics committee and all "
            "participants provided written informed consent.</p>"
            "<p><strong>Participants.</strong> Adults aged 18–80 years with seated office systolic "
            "blood pressure ≥150 mmHg despite receiving three antihypertensive agents at maximally "
            "tolerated doses, including a thiazide-type diuretic. Adherence was confirmed by "
            "witnessed dosing and pill counts.</p>"
            "<p><strong>Randomisation and blinding.</strong> Eligible participants were randomised "
            "1:1 to add-on lisinopril 20 mg daily or matched placebo using a permuted-block "
            "schedule (block size 4) stratified by age. Investigators, participants and outcome "
            "assessors were blinded.</p>"
            "<p><strong>Outcomes.</strong> The primary outcome was change in 24-hour ambulatory "
            "systolic blood pressure at 12 weeks. Secondary outcomes included change in seated "
            "office BP, treatment-emergent adverse events, and quality of life (EQ-5D-5L).</p>"
            "<p><strong>Statistical analysis.</strong> We compared the mean change in systolic "
            "blood pressure between arms using an independent-samples t-test, with results "
            "additionally adjusted for baseline SBP and age in a linear regression. A chi-square "
            "test compared the proportion experiencing adverse events. Analyses were performed in "
            "Research Assistant on an intention-to-treat basis.</p>"
        ),
        "Results": (
            "<p>The CONSORT flow is shown in Figure 1. Forty participants were enrolled and "
            "randomised; baseline characteristics were well balanced between arms (Table 1). "
            "The primary outcome, mean change in 24-hour systolic BP, was -13.6 mmHg (SD 7.1) in "
            "the lisinopril arm and -2.1 mmHg (SD 6.4) in the placebo arm (mean difference "
            "11.5 mmHg, 95% CI 7.4 to 15.6; p&lt;0.001).</p>"
            "<p>In a pre-specified linear-regression model adjusting for baseline SBP and age, "
            "the treatment effect was 11.3 mmHg (95% CI 7.0 to 15.5). Adverse events occurred in "
            "20% of lisinopril and 10% of placebo participants (chi-square p=0.41).</p>"
        ),
        "Discussion": (
            "<p>In this small placebo-controlled trial, add-on lisinopril produced a robust and "
            "clinically meaningful reduction in 24-hour systolic blood pressure at 12 weeks in "
            "patients with confirmed resistant hypertension. The effect size — approximately 11 "
            "mmHg — is comparable to that observed in the seminal PATHWAY-2 trial of "
            "spironolactone, suggesting that ACE inhibition remains a useful add-on strategy.</p>"
            "<p>Strengths of this trial include the double-blind placebo-controlled design, the "
            "use of ambulatory blood pressure monitoring, and rigorous adherence verification. "
            "Important limitations include the modest sample size and the single-centre setting; "
            "a larger multi-centre trial would clarify whether the effect generalises to broader "
            "populations. We did not collect long-term cardiovascular outcomes.</p>"
        ),
        "Conclusion": (
            "<p>In a placebo-controlled randomised trial, add-on lisinopril reduced 24-hour systolic "
            "blood pressure by an additional 11.5 mmHg at 12 weeks in adults with resistant "
            "hypertension. Larger multi-centre trials are warranted to confirm the effect on "
            "long-term cardiovascular outcomes.</p>"
        ),
    }


# ─── Project C: Surgery cohort (laparoscopic cholecystectomy) ───────────────


SURG_AFFILIATIONS = [
    {
        "name": "Department of Hepatobiliary Surgery, Addenbrooke's Hospital",
        "city": "Cambridge",
        "country": "United Kingdom",
    },
    {
        "name": "Cambridge University Hospitals NHS Foundation Trust",
        "city": "Cambridge",
        "country": "United Kingdom",
    },
]


SURG_AUTHORS = [
    {
        "full_name": "Oliver J. Birkett",
        "given_name": "Oliver",
        "family_name": "Birkett",
        "is_corresponding": True,
        "email": "oliver.birkett@example.ac.uk",
        "affiliations": [SURG_AFFILIATIONS[0]["name"]],
    },
    {
        "full_name": "Aanya R. Chowdhury",
        "given_name": "Aanya",
        "family_name": "Chowdhury",
        "affiliations": [SURG_AFFILIATIONS[1]["name"]],
    },
]


SURG_REFERENCES: list[dict[str, Any]] = [
    {
        "title": "Laparoscopic cholecystectomy: outcomes from a national audit",
        "authors": ["Sutcliffe RP", "Hollyman M", "Hodson J", "Bonney G"],
        "journal": "British Journal of Surgery",
        "year": 2019,
        "doi": "10.1002/bjs.11215",
    },
    {
        "title": "Surgeon volume and outcomes after laparoscopic cholecystectomy: a population-based cohort study",
        "authors": ["Harrison EM", "O'Neill S", "Meurs TS"],
        "journal": "Annals of Surgery",
        "year": 2017,
        "doi": "10.1097/SLA.0000000000002041",
    },
    {
        "title": "Tokyo Guidelines 2018: diagnostic criteria and severity grading of acute cholecystitis",
        "authors": ["Yokoe M", "Hata J", "Takada T"],
        "journal": "Journal of Hepato-Biliary-Pancreatic Sciences",
        "year": 2018,
        "doi": "10.1002/jhbp.515",
    },
    {
        "title": "Acute cholecystitis: early versus delayed laparoscopic cholecystectomy — meta-analysis",
        "authors": ["Gurusamy KS", "Davidson C", "Gluud C", "Davidson BR"],
        "journal": "Cochrane Database of Systematic Reviews",
        "year": 2013,
        "doi": "10.1002/14651858.CD005440.pub3",
    },
    {
        "title": "ASA Physical Status Classification System: 2020 updates",
        "authors": ["American Society of Anesthesiologists"],
        "journal": "ASA Newsletter",
        "year": 2020,
        "doi": "10.1097/ALN.0000000000003411",
    },
]


def build_surg_csv() -> str:
    # Use 0/1 for binary outcomes so the regression runner can handle them
    # without explicit dtype coercion. Surgeon volume stays categorical as a
    # 0/1 indicator (1=high) — the manuscript narrative still reads naturally.
    random.seed(20260101)
    lines = ["id,age,bmi,asa_grade,surgeon_volume_high,los_days,complication,mortality"]
    for i in range(1, 61):
        age = random.randint(28, 84)
        bmi = round(random.uniform(20.0, 38.0), 1)
        asa = random.choices([1, 2, 3, 4], weights=[0.15, 0.55, 0.25, 0.05])[0]
        is_high = random.random() < 0.5
        if is_high:
            los = max(1, int(random.gauss(2.1, 1.0)))
            complication = 1 if random.random() < 0.05 + (asa - 1) * 0.03 else 0
        else:
            los = max(1, int(random.gauss(3.4, 1.6)))
            complication = 1 if random.random() < 0.10 + (asa - 1) * 0.04 else 0
        mortality = 1 if (asa >= 3 and random.random() < 0.04) else 0
        surgeon_volume_high = 1 if is_high else 0
        lines.append(f"{i},{age},{bmi},{asa},{surgeon_volume_high},{los},{complication},{mortality}")
    return "\n".join(lines) + "\n"


def build_surg_manuscript_sections() -> dict[str, str]:
    return {
        "Abstract": (
            "<p><strong>Background.</strong> Laparoscopic cholecystectomy is among the most common "
            "elective abdominal procedures, yet the relative contribution of patient and surgeon "
            "factors to post-operative complications is incompletely understood.</p>"
            "<p><strong>Methods.</strong> We retrospectively analysed 60 consecutive elective "
            "laparoscopic cholecystectomies performed at a tertiary centre between 2024 and 2026. "
            "Complications and length of stay were related to age, BMI, ASA grade and surgeon "
            "volume using logistic regression and Kaplan–Meier analysis.</p>"
            "<p><strong>Results.</strong> Complications occurred in 13% of cases. ASA grade and "
            "surgeon volume were independently associated with complication risk; high-volume "
            "surgeons achieved lower complication rates and shorter median length of stay (2 vs "
            "3 days; log-rank p=0.01).</p>"
            "<p><strong>Conclusions.</strong> Surgeon volume is an important modifiable contributor "
            "to outcomes after elective laparoscopic cholecystectomy and should be reflected in "
            "elective scheduling and quality benchmarking.</p>"
        ),
        "Introduction": (
            "<p>Laparoscopic cholecystectomy (LC) is the standard of care for symptomatic "
            "cholelithiasis and remains one of the most frequently performed general-surgical "
            "procedures. Despite the maturity of the technique, complications including bile-duct "
            "injury, bleeding, and conversion to open surgery continue to affect patient outcomes "
            "and healthcare costs.</p>"
            "<p>Patient-level risk factors (age, body-mass index, ASA physical status, severity of "
            "cholecystitis) have been characterised in earlier reports. The contribution of "
            "surgeon volume — a system-level modifiable factor — is less consistently quantified, "
            "particularly in contemporary UK practice. We therefore performed a retrospective "
            "cohort analysis of consecutive elective LC procedures at our centre to estimate "
            "the independent contribution of surgeon volume after adjustment for patient factors.</p>"
        ),
        "Methodology": (
            "<p>This was a retrospective cohort study following the STROBE reporting statement. "
            "We included all adults undergoing elective laparoscopic cholecystectomy for "
            "symptomatic cholelithiasis at our tertiary hepatobiliary centre between 1 January "
            "2024 and 31 December 2026. Emergency procedures and patients undergoing concomitant "
            "biliary exploration were excluded.</p>"
            "<p>Data were extracted from the hospital electronic health record. Primary outcome "
            "was the occurrence of any in-hospital complication. Secondary outcomes included "
            "length of stay (days), in-hospital mortality, and 30-day readmission. The exposure "
            "of interest was surgeon volume, classified as high (≥75 LCs/year) or low (&lt;75 "
            "LCs/year) using national audit benchmarks.</p>"
            "<p>Categorical variables are summarised as n (%) and continuous variables as mean "
            "(SD) or median (IQR). Adjusted associations with complications were modelled by "
            "multivariable logistic regression with age, BMI, ASA grade, and surgeon volume as "
            "covariates. Length of stay was compared between groups using Kaplan–Meier analysis "
            "with log-rank testing. Analyses were performed in Research Assistant.</p>"
        ),
        "Results": (
            "<p>Sixty consecutive procedures were included (median age 56 years; 38% male; "
            "median BMI 27.4 kg/m²). ASA grade distribution was 1=15%, 2=55%, 3=25%, 4=5%. "
            "Thirty (50%) procedures were performed by a high-volume surgeon.</p>"
            "<p>Eight patients (13%) experienced an in-hospital complication. In multivariable "
            "logistic regression, ASA grade (OR 2.18 per unit, 95% CI 1.10 to 4.33; p=0.026) "
            "and low surgeon volume (OR 3.12, 95% CI 1.04 to 9.40; p=0.043) were independently "
            "associated with complication risk after adjustment for age and BMI.</p>"
            "<p>Median length of stay was 2 days (IQR 1–3) for high-volume surgeons and 3 days "
            "(IQR 2–4) for low-volume surgeons (log-rank p=0.01). In-hospital mortality was 2% "
            "and occurred only in ASA-3/4 patients.</p>"
        ),
        "Discussion": (
            "<p>In this retrospective cohort of elective laparoscopic cholecystectomy, surgeon "
            "volume was an independent contributor to complication risk and length of stay, "
            "after adjustment for patient factors. The magnitude of the effect — a three-fold "
            "increase in adjusted odds of complication for low-volume surgeons — is consistent "
            "with population-based UK data and underlines the value of consolidating elective "
            "hepatobiliary work onto high-volume operators.</p>"
            "<p>Our analysis is limited by its single-centre design and modest sample size; "
            "residual confounding from unmeasured covariates (gallbladder anatomy, intra-operative "
            "findings) cannot be excluded. A prospective multi-centre study with formal definitions "
            "of surgeon-volume thresholds and standardised complication adjudication would "
            "strengthen the evidence base.</p>"
        ),
        "Conclusion": (
            "<p>Surgeon volume is an independent and modifiable contributor to outcomes after "
            "elective laparoscopic cholecystectomy. Service-level policies that consolidate "
            "elective work onto high-volume operators are likely to reduce complications and "
            "shorten length of stay.</p>"
        ),
    }


# ─── Seed Project A — Ortho SR ──────────────────────────────────────────────


def seed_project_a_ortho(client: ApiClient) -> dict:
    print("\n[A] Orthopaedics — systematic review")
    project = get_or_create_project(
        client,
        title=PROJECTS["ortho"],
        study_type="Systematic Review",
        citation_style="vancouver",
        template_journal="bjj",
        target_journal="The Bone & Joint Journal",
        prospero_number="CRD42026512098",
    )
    pid = project["id"]
    print(f"    project id: {pid}")

    upsert_frontmatter(
        client, pid,
        funding="This review received no specific funding. SJW is supported by an NIHR Doctoral Fellowship (DRF-2024-001).",
        funders=[{"name": "NIHR Doctoral Fellowship Programme", "grant_id": "DRF-2024-001"}],
        ethics_irb=None,
        ethics_approval=None,
        ethics_consent="Not required — systematic review of published data.",
        conflicts="The authors declare no competing interests.",
        abstract={
            "background": (
                "Anterior cruciate ligament (ACL) reconstruction is one of the most commonly "
                "performed knee operations worldwide. The optimal choice of graft, fixation, "
                "and rehabilitation pathway is debated. We aimed to systematically review and "
                "meta-analyse modern evidence comparing autograft choices."
            ),
            "methods": (
                "We searched PubMed, Embase, and the Cochrane CENTRAL Register from inception "
                "to 12 March 2026. Two independent reviewers screened records, extracted data, "
                "and assessed risk of bias using RoB 2 (trials) and ROBINS-I (cohorts). "
                "Continuous outcomes were pooled with random-effects (DerSimonian–Laird) models."
            ),
            "results": (
                "Twelve studies (1,623 participants) met inclusion. Pooled IKDC subjective knee "
                "score at 24 months favoured bone-patellar tendon-bone autograft over hamstring "
                "by 2.4 points (95% CI 0.6 to 4.2; I²=38%)."
            ),
            "conclusions": (
                "BPTB and hamstring autografts produce broadly comparable patient-reported "
                "outcomes; small differences in laxity and donor-site pain should inform shared "
                "decision-making."
            ),
        },
    )
    print("    frontmatter upserted")

    upsert_authors_and_affiliations(
        client, pid,
        affiliations=ORTHO_AFFILIATIONS,
        authors=ORTHO_AUTHORS,
    )
    print(f"    authors: {len(ORTHO_AUTHORS)}, affiliations: {len(ORTHO_AFFILIATIONS)}")

    # ── Articles ───────────────────────────────────────────────────────
    # We don't store study_design on each article via import-from-metadata
    # (the schema doesn't accept it); the design is captured separately in
    # the extraction records.
    import_articles(client, pid, [dict(a) for a in ORTHO_ARTICLES])
    articles = list_articles(client, pid)
    # Map article title → article record (for screening / RoB / extraction)
    by_title: dict[str, dict] = {a["title"]: a for a in articles}
    art_by_idx: dict[int, dict] = {}
    for i, src in enumerate(ORTHO_ARTICLES):
        found = by_title.get(src["title"])
        if found is not None:
            art_by_idx[i] = found
    print(f"    articles in library: {len(articles)}")

    # ── PICO + eligibility ─────────────────────────────────────────────
    upsert_review_pico(
        client, pid,
        population="Adults aged ≥18 years undergoing primary anterior cruciate ligament reconstruction",
        intervention="Bone-patellar tendon-bone, hamstring tendon, or quadriceps tendon autograft reconstruction",
        comparator="Alternative autograft, allograft, or non-operative management",
        outcome=(
            "IKDC subjective knee score at 24 months (primary); KT-1000 side-to-side laxity, "
            "graft re-rupture, return-to-sport rate, and donor-site complications (secondary)"
        ),
        inclusion=(
            "Randomised controlled trials or prospective cohort studies of adults (≥18 years) "
            "undergoing primary ACL reconstruction; ≥6 months follow-up; published in English "
            "between 2008 and 2026."
        ),
        exclusion=(
            "Conference abstracts; single-centre series with <30 participants; revision or "
            "paediatric reconstruction; concomitant multi-ligament surgery."
        ),
    )

    # ── Search records ─────────────────────────────────────────────────
    upsert_search_records(client, pid, ORTHO_SEARCH_RECORDS)
    print(f"    search records: {len(ORTHO_SEARCH_RECORDS)}")

    # ── Screening ──────────────────────────────────────────────────────
    screening_records = []
    for plan in ORTHO_SCREENING_PLAN:
        art = art_by_idx.get(plan["idx"])
        if art is None:
            continue
        rec: dict[str, Any] = {
            "article_id": art["id"],
            "stage": plan["stage"],
            "decision": plan["decision"],
        }
        if "reason" in plan:
            rec["reason"] = plan["reason"]
        if "exclusion_category" in plan:
            rec["exclusion_category"] = plan["exclusion_category"]
        screening_records.append(rec)
    upsert_screening(client, pid, screening_records)
    print(f"    screening records: {len(screening_records)}")

    # ── RoB assessments (RoB 2 for first 10 included studies) ──────────
    included_indices = [
        p["idx"] for p in ORTHO_SCREENING_PLAN
        if p["decision"] == "include" and p["idx"] in art_by_idx
    ]
    rob_judgements = [
        ("low", "low", "low", "low", "low"),
        ("low", "low", "low", "low", "some_concerns"),
        ("some_concerns", "low", "low", "low", "low"),
        ("low", "some_concerns", "low", "low", "low"),
        ("low", "low", "some_concerns", "low", "low"),
        ("low", "low", "low", "some_concerns", "some_concerns"),
        ("high", "some_concerns", "low", "low", "low"),
        ("low", "low", "low", "low", "some_concerns"),
        ("low", "low", "some_concerns", "low", "low"),
        ("some_concerns", "low", "low", "low", "low"),
    ]
    domains = ("randomisation", "deviations", "missing_outcome", "measurement", "reporting")
    rob_records = []
    for idx, judgements in zip(included_indices[:10], rob_judgements):
        art = art_by_idx[idx]
        rob_records.append({
            "article_id": art["id"],
            "tool": "rob2",
            "domain_answers": dict(zip(domains, judgements)),
            "notes": "Dual-rated by SJW and DAM; consensus reached without arbitration.",
        })
    upsert_rob(client, pid, rob_records)
    print(f"    RoB assessments: {len(rob_records)}")

    # ── Extraction (first 10 included) ─────────────────────────────────
    extraction_records = []
    # Canonical study-design tokens accepted by the extraction-schema validator:
    # ('RCT', 'cohort', 'case_control', 'case_series', 'cross_sectional',
    #  'qualitative', 'other'). Only "RCT" is uppercase by design.
    designs = ["RCT", "RCT", "cohort", "RCT", "RCT", "RCT", "cohort", "RCT", "RCT", "RCT"]
    countries = ["Canada", "Australia", "Australia", "USA", "UK", "Thailand", "USA", "USA", "Italy", "Japan"]
    interventions = [
        "Bone-patellar tendon-bone autograft",
        "Hamstring tendon autograft",
        "Bone-patellar tendon-bone autograft",
        "Bone-patellar tendon-bone autograft",
        "Early reconstruction (<6 weeks)",
        "Single-bundle reconstruction",
        "Quadriceps tendon autograft",
        "Accelerated rehabilitation",
        "Bone-patellar tendon-bone autograft",
        "Bioabsorbable interference screw",
    ]
    comparators = [
        "Hamstring tendon autograft",
        "Bone-patellar tendon-bone autograft",
        "Hamstring tendon autograft",
        "Allograft",
        "Delayed reconstruction (>10 weeks)",
        "Double-bundle reconstruction",
        "Hamstring tendon autograft",
        "Non-accelerated rehabilitation",
        "Hamstring tendon autograft",
        "Metal interference screw",
    ]
    outcomes_list = [
        ["IKDC at 24 months", "Anterior knee pain", "Graft re-rupture"],
        ["IKDC at 20 years", "Radiographic OA", "Return to sport"],
        ["Return to sport", "IKDC", "Marx activity"],
        ["IKDC", "Graft rupture", "KT-1000 laxity"],
        ["IKDC at 24 months", "Tegner score"],
        ["Pivot-shift test", "IKDC", "Graft failure"],
        ["KT-1000", "IKDC", "Donor-site morbidity"],
        ["KT-1000", "Single-leg hop"],
        ["IKDC at 5 years", "Anterior knee pain"],
        ["KT-1000 laxity", "Complications"],
    ]
    n_totals = [320, 200, 5770, 147, 234, 1433, 120, 25, 120, 108]
    for idx, design, country, n_total, iname, cname, outcomes in zip(
        included_indices[:10],
        designs,
        countries,
        n_totals,
        interventions,
        comparators,
        outcomes_list,
    ):
        art = art_by_idx[idx]
        extraction_records.append({
            "article_id": art["id"],
            "fields": {
                "basic": {
                    "first_author": art["authors"][0] if art.get("authors") else "Unknown",
                    "year": art["year"],
                    "country": country,
                    "design": design,
                },
                "population": {
                    "n_total": n_total,
                    "mean_age": 28,
                    "sex_male_pct": 64,
                    "inclusion": "Adults ≥18 years with primary ACL injury",
                    "exclusion": "Revision, multi-ligament injury, paediatric",
                },
                "intervention": {
                    "name": iname,
                    "dose_or_protocol": "Standard surgical protocol",
                    "duration_weeks": 104,
                },
                "comparator": {"name": cname, "dose_or_protocol": "Standard"},
                "outcomes": {"outcomes": [{"name": n} for n in outcomes]},
                "funding": {"source": "Institutional", "coi_disclosed": "yes"},
                "notes": {"free_text": "Extracted independently by SJW and DAM; consensus reached."},
            },
        })
    upsert_extraction(client, pid, extraction_records)
    print(f"    extraction records: {len(extraction_records)}")

    # ── Meta-analysis (mean difference, IKDC) ──────────────────────────
    meta_inputs: list[dict[str, Any]] = []
    for blueprint in ORTHO_META_INPUTS_BLUEPRINT:
        art = art_by_idx.get(blueprint["idx"])
        if art is None:
            continue
        meta_inputs.append({
            "article_id": art["id"],
            "study_label": blueprint["label"],
            "mean_a": blueprint["mean_a"],
            "sd_a": blueprint["sd_a"],
            "n_a": blueprint["n_a"],
            "mean_b": blueprint["mean_b"],
            "sd_b": blueprint["sd_b"],
            "n_b": blueprint["n_b"],
        })
    if len(meta_inputs) >= 2:
        upsert_meta_analysis(
            client, pid,
            title="IKDC subjective knee score at 24 months: BPTB vs Hamstring autograft",
            effect_metric="md",
            model="random",
            inputs=meta_inputs,
        )
        print(f"    meta-analysis: 1 (n_studies={len(meta_inputs)})")

    # ── GRADE certainty (3 outcomes) ───────────────────────────────────
    upsert_grade(client, pid, [
        {
            "outcome_label": "IKDC subjective knee score at 24 months",
            "starting_certainty": "high",
            "domain_risk_of_bias": "not_serious",
            "domain_inconsistency": "not_serious",
            "domain_indirectness": "not_serious",
            "domain_imprecision": "serious",
            "domain_publication_bias": "not_serious",
            "notes": "Downgraded one level for imprecision (CI crosses minimal clinically important difference).",
        },
        {
            "outcome_label": "Graft re-rupture at 24 months",
            "starting_certainty": "high",
            "domain_risk_of_bias": "not_serious",
            "domain_inconsistency": "serious",
            "domain_indirectness": "not_serious",
            "domain_imprecision": "serious",
            "domain_publication_bias": "not_serious",
            "notes": "Downgraded for inconsistency (I²=58%) and imprecision (wide 95% CI).",
        },
        {
            "outcome_label": "Anterior knee pain at kneeling",
            "starting_certainty": "high",
            "domain_risk_of_bias": "not_serious",
            "domain_inconsistency": "not_serious",
            "domain_indirectness": "not_serious",
            "domain_imprecision": "not_serious",
            "domain_publication_bias": "not_serious",
            "notes": "Robust to sensitivity analysis; very low risk of publication bias on Egger's test.",
        },
    ])
    print("    GRADE assessments: 3")

    # ── PROSPERO draft ──────────────────────────────────────────────────
    try:
        upsert_prospero(client, pid, {
            "review_title": "ACL reconstruction outcomes: a systematic review and meta-analysis",
            "review_question": "What are the comparative patient-reported and structural outcomes after autograft choice for primary ACL reconstruction?",
            "anticipated_completion_date": "2026-12-31",
            "language": "English",
            "country": "United Kingdom",
        })
        print("    PROSPERO draft: 1")
    except Exception as exc:
        print(f"    [warn] PROSPERO draft skipped: {exc}")

    # ── Manuscript sections ────────────────────────────────────────────
    for section, content in build_ortho_manuscript_sections().items():
        upsert_section(client, pid, section, content)
    print(f"    manuscript sections: {len(build_ortho_manuscript_sections())}")

    # ── Checklist: PRISMA 2020 ─────────────────────────────────────────
    try:
        run = upsert_checklist_run(
            client, pid,
            checklist_key="PRISMA_2020",
            title="PRISMA 2020 — ACL reconstruction SR (final)",
        )
        # Mark a handful of items as 'pass' to give the screenshot some teeth.
        item_decisions: dict[str, dict[str, str]] = {}
        for item in run.get("items", [])[:18]:
            item_decisions[item["item_id"]] = {
                "status": "pass",
                "comment": "Reported per PRISMA 2020 statement.",
            }
        if item_decisions:
            for item_id, patch in item_decisions.items():
                try:
                    client.patch(
                        f"/api/projects/{pid}/checklists/{run['id']}/items/{item_id}",
                        patch,
                    )
                except Exception:
                    pass
        print("    PRISMA 2020 checklist: 1")
    except Exception as exc:
        print(f"    [warn] PRISMA checklist skipped: {exc}")

    return project


# ─── Seed Project B — RCT ───────────────────────────────────────────────────


def seed_project_b_rct(client: ApiClient) -> dict:
    print("\n[B] General medicine — RCT")
    project = get_or_create_project(
        client,
        title=PROJECTS["rct"],
        study_type="Randomised Controlled Trial",
        citation_style="nejm",
        template_journal="nejm",
        target_journal="New England Journal of Medicine",
        clinicaltrials_number="NCT04451234",
    )
    pid = project["id"]
    print(f"    project id: {pid}")

    upsert_frontmatter(
        client, pid,
        funding="This trial was funded by an Oxford-NHS Cardiovascular Research Award (Ref 2024-CV-019).",
        funders=[{"name": "Oxford-NHS Cardiovascular Research Award", "grant_id": "2024-CV-019"}],
        ethics_irb="Oxford Research Ethics Committee (REC reference 24/SC/0142)",
        ethics_approval="24/SC/0142",
        ethics_consent="All participants provided written informed consent.",
        conflicts="The authors declare no relevant conflicts of interest.",
        abstract={
            "background": (
                "Resistant hypertension affects up to 10% of treated hypertensive adults and "
                "confers substantial cardiovascular risk. The incremental benefit of add-on "
                "lisinopril on multi-drug regimens is uncertain."
            ),
            "methods": (
                "We performed a single-centre, double-blind, placebo-controlled trial of "
                "lisinopril 20 mg daily vs placebo in 40 adults with confirmed resistant "
                "hypertension. The primary outcome was change in 24-hour ambulatory systolic "
                "blood pressure at 12 weeks."
            ),
            "results": (
                "Lisinopril reduced systolic blood pressure by 13.6 mmHg vs 2.1 mmHg in placebo "
                "(difference 11.5 mmHg, 95% CI 7.4 to 15.6; p<0.001). Adverse events were "
                "uncommon and similar between arms."
            ),
            "conclusions": (
                "Add-on lisinopril produces a clinically meaningful reduction in systolic blood "
                "pressure in resistant hypertension. (Funded by the Oxford-NHS Cardiovascular "
                "Research Award; ClinicalTrials.gov NCT04451234.)"
            ),
        },
    )
    print("    frontmatter upserted")

    upsert_authors_and_affiliations(
        client, pid, affiliations=RCT_AFFILIATIONS, authors=RCT_AUTHORS
    )
    print(f"    authors: {len(RCT_AUTHORS)}, affiliations: {len(RCT_AFFILIATIONS)}")

    import_articles(client, pid, [dict(a) for a in RCT_REFERENCES])
    print(f"    references in library: {len(RCT_REFERENCES)}")

    # ── Dataset ─────────────────────────────────────────────────────────
    dataset = upsert_dataset_csv(
        client, pid, filename="lisinopril-rct-masterchart.csv", csv_text=build_rct_csv()
    )
    did = dataset["id"]
    print(f"    dataset rows: {dataset['n_rows']} cols: {dataset['n_columns']}")

    # ── Analyses ───────────────────────────────────────────────────────
    # 1) Independent t-test of week_12_sbp by group.
    create_and_run_analysis(
        client, pid, did,
        question_type="group_comparison",
        chosen_test="independent_t",
        variables={"groups": "group", "outcome": "week_12_sbp"},
        label_marker="independent_t (week12 by group)",
    )
    # 2) Chi-square for adverse_event by group.
    create_and_run_analysis(
        client, pid, did,
        question_type="group_comparison",
        chosen_test="chi_squared",
        variables={"groups": "group", "outcome": "adverse_event"},
        label_marker="chi_squared (AE by group)",
    )
    # 3) Multiple linear regression: week_12_sbp ~ baseline_sbp + age + group.
    create_and_run_analysis(
        client, pid, did,
        question_type="association",
        chosen_test="multiple_linear",
        variables={
            "outcome": "week_12_sbp",
            "predictors": ["baseline_sbp", "age", "group"],
        },
        label_marker="multiple_linear (week12 ~ baseline + age + group)",
    )
    print("    analyses: 3 (independent t, chi-square, multiple linear regression)")

    # ── Manuscript sections ────────────────────────────────────────────
    for section, content in build_rct_manuscript_sections().items():
        upsert_section(client, pid, section, content)
    print(f"    manuscript sections: {len(build_rct_manuscript_sections())}")

    # ── CONSORT diagram ────────────────────────────────────────────────
    upsert_consort(client, pid, {
        "enrollment_assessed": 68,
        "enrollment_excluded": 28,
        "enrollment_excluded_reasons": {
            "did_not_meet_inclusion": 19,
            "declined_to_participate": 6,
            "other": 3,
        },
        "randomised": 40,
        "allocated_intervention": 20,
        "allocated_control": 20,
        "intervention_received": 20,
        "control_received": 20,
        "intervention_lost_followup": 0,
        "control_lost_followup": 1,
        "intervention_discontinued": 1,
        "control_discontinued": 0,
        "intervention_analysed": 20,
        "control_analysed": 19,
    })
    print("    CONSORT diagram populated")

    # ── Checklist: CONSORT 2010 ────────────────────────────────────────
    try:
        run = upsert_checklist_run(
            client, pid,
            checklist_key="CONSORT_2010",
            title="CONSORT 2010 — Lisinopril RCT (final)",
        )
        for item in run.get("items", [])[:20]:
            try:
                client.patch(
                    f"/api/projects/{pid}/checklists/{run['id']}/items/{item['item_id']}",
                    {"status": "pass", "comment": "Reported per CONSORT 2010."},
                )
            except Exception:
                pass
        print("    CONSORT 2010 checklist: 1")
    except Exception as exc:
        print(f"    [warn] CONSORT checklist skipped: {exc}")

    # ── Cover letter ───────────────────────────────────────────────────
    # NB: the cover-letter ``target_journal`` field is constrained to the
    # journal-template catalogue keys (ortho-only at this revision). We
    # therefore leave it unset for the RCT — the body still mentions NEJM.
    try:
        upsert_cover_letter(
            client, pid,
            target_journal=None,
            novelty_points=[
                "First placebo-controlled trial of add-on lisinopril in confirmed resistant hypertension.",
                "11.5 mmHg reduction in 24-hour SBP at 12 weeks — comparable to spironolactone in PATHWAY-2.",
                "Adherence was verified by witnessed dosing and pill counts.",
            ],
            body_html=(
                "<p>Dear Editor,</p>"
                "<p>We are pleased to submit our manuscript, <em>Lisinopril vs placebo for "
                "resistant hypertension: a double-blind randomised controlled trial</em>, for "
                "consideration by the New England Journal of Medicine.</p>"
                "<p>Resistant hypertension is a stubborn clinical problem and the incremental "
                "value of add-on ACE inhibition on quadruple therapy has not previously been "
                "tested in a placebo-controlled trial. We believe our results — an additional "
                "11.5 mmHg reduction in 24-hour systolic blood pressure at 12 weeks — will be "
                "of broad interest to the Journal's readership.</p>"
                "<p>The manuscript has not been submitted or published elsewhere. All authors "
                "have approved the submission and declare no relevant conflicts of interest.</p>"
                "<p>Yours faithfully,<br/>Elena R. Marshall, on behalf of the authors</p>"
            ),
        )
        print("    cover letter drafted")
    except Exception as exc:
        print(f"    [warn] cover letter skipped: {exc}")

    return project


# ─── Seed Project C — Surgery cohort ────────────────────────────────────────


def seed_project_c_cohort(client: ApiClient) -> dict:
    print("\n[C] Surgery — retrospective cohort")
    project = get_or_create_project(
        client,
        title=PROJECTS["cohort"],
        study_type="Retrospective Case Series",
        citation_style="bjj",
        template_journal="bjj",
        target_journal="British Journal of Surgery",
    )
    pid = project["id"]
    print(f"    project id: {pid}")

    upsert_frontmatter(
        client, pid,
        funding="No external funding was received for this study.",
        funders=[],
        ethics_irb="Cambridge Local Research Ethics Committee",
        ethics_approval="CLREC 25/HBP/041",
        ethics_consent="Informed consent waived for retrospective analysis of routinely collected data.",
        conflicts="The authors declare no competing interests.",
        abstract={
            "background": (
                "Laparoscopic cholecystectomy is a high-volume elective procedure. The relative "
                "contribution of patient and surgeon factors to post-operative complications "
                "remains incompletely understood."
            ),
            "methods": (
                "Retrospective cohort of 60 consecutive elective laparoscopic cholecystectomies "
                "performed between 2024 and 2026 at a UK tertiary hepatobiliary centre. "
                "Multivariable logistic regression and Kaplan–Meier analysis examined surgeon "
                "volume as an independent contributor to complications and length of stay."
            ),
            "results": (
                "Complications occurred in 13% of cases. ASA grade (OR 2.18) and low surgeon "
                "volume (OR 3.12) were independently associated with complication risk. Median "
                "length of stay was 2 days for high-volume vs 3 days for low-volume surgeons."
            ),
            "conclusions": (
                "Surgeon volume is an important modifiable contributor to outcomes after "
                "elective laparoscopic cholecystectomy."
            ),
        },
    )
    print("    frontmatter upserted")

    upsert_authors_and_affiliations(
        client, pid, affiliations=SURG_AFFILIATIONS, authors=SURG_AUTHORS
    )
    print(f"    authors: {len(SURG_AUTHORS)}, affiliations: {len(SURG_AFFILIATIONS)}")

    import_articles(client, pid, [dict(a) for a in SURG_REFERENCES])
    print(f"    references in library: {len(SURG_REFERENCES)}")

    # ── Dataset ────────────────────────────────────────────────────────
    dataset = upsert_dataset_csv(
        client, pid, filename="lap-chole-cohort.csv", csv_text=build_surg_csv()
    )
    did = dataset["id"]
    print(f"    dataset rows: {dataset['n_rows']} cols: {dataset['n_columns']}")

    # ── Analyses ───────────────────────────────────────────────────────
    # 1) Logistic regression: complication ~ asa_grade + surgeon_volume_high + age + bmi
    create_and_run_analysis(
        client, pid, did,
        question_type="association",
        chosen_test="logistic",
        variables={
            "outcome": "complication",
            "predictors": ["asa_grade", "surgeon_volume_high", "age", "bmi"],
        },
        label_marker="logistic (complication ~ ASA + surgeon + age + bmi)",
    )
    # 2) Independent t-test: BMI by complication
    create_and_run_analysis(
        client, pid, did,
        question_type="group_comparison",
        chosen_test="independent_t",
        variables={"groups": "complication", "outcome": "bmi"},
        label_marker="independent_t (bmi by complication)",
    )
    # 3) Chi-square: complication by surgeon_volume_high
    create_and_run_analysis(
        client, pid, did,
        question_type="group_comparison",
        chosen_test="chi_squared",
        variables={"groups": "surgeon_volume_high", "outcome": "complication"},
        label_marker="chi_squared (complication by surgeon_volume_high)",
    )
    print("    analyses: 3 (logistic, independent t, chi-square)")

    # ── Manuscript sections ────────────────────────────────────────────
    for section, content in build_surg_manuscript_sections().items():
        upsert_section(client, pid, section, content)
    print(f"    manuscript sections: {len(build_surg_manuscript_sections())}")

    # ── STROBE checklist ───────────────────────────────────────────────
    try:
        run = upsert_checklist_run(
            client, pid,
            checklist_key="STROBE_COHORT",
            title="STROBE (Cohort) — Lap-chole cohort (final)",
        )
        for item in run.get("items", [])[:18]:
            try:
                client.patch(
                    f"/api/projects/{pid}/checklists/{run['id']}/items/{item['item_id']}",
                    {"status": "pass", "comment": "Reported per STROBE."},
                )
            except Exception:
                pass
        print("    STROBE checklist: 1")
    except Exception as exc:
        print(f"    [warn] STROBE checklist skipped: {exc}")

    # ── Health-economics analysis ──────────────────────────────────────
    # Skipped if the dataset is missing the required cost / utility columns;
    # this dataset is a complication/LoS chart so we attach a minimal demo
    # health-economics entry pointing at the dataset for show.
    try:
        existing_econ = client.get(f"/api/projects/{pid}/economic-analyses")
        already = next(
            (e for e in existing_econ if e.get("name") == "ICER: high vs low volume surgeons"),
            None,
        )
        if already is None:
            # los_days proxy for cost (£250/day) and 1-complication = -0.05 QALY
            # The economics module expects bound cost-columns mapped via roles.
            client.post(
                f"/api/projects/{pid}/economic-analyses",
                {
                    "name": "ICER: high vs low volume surgeons",
                    "dataset_id": did,
                    "currency": "GBP",
                    "time_horizon_months": 12,
                    "perspective": "healthcare_system",
                    "treatment_col": "surgeon_volume_high",
                    "comparator_label": "0",
                    "intervention_label": "1",
                    "cost_columns": [
                        {"col": "los_days", "role": "quantity"},
                    ],
                },
            )
            print("    health-economics analysis: 1")
        else:
            print("    health-economics analysis: 1 (existing)")
    except Exception as exc:
        print(f"    [warn] health-economics skipped: {exc}")

    return project


# ─── Driver ─────────────────────────────────────────────────────────────────


def wipe_seed_projects(client: ApiClient) -> None:
    print("Wiping existing seed projects …")
    for p in client.get("/api/projects"):
        title = p.get("title") or ""
        if title.startswith(SEED_TAG):
            try:
                client.delete(f"/api/projects/{p['id']}")
                print(f"  deleted {p['id']}: {title}")
            except Exception as exc:
                print(f"  [warn] could not delete {p['id']}: {exc}")


def print_summary(client: ApiClient) -> None:
    print("\n─── Summary ─────────────────────────────────────────────────")
    projects = client.get("/api/projects")
    seeded = [p for p in projects if (p.get("title") or "").startswith(SEED_TAG)]
    for p in seeded:
        pid = p["id"]
        try:
            arts = client.get(f"/api/projects/{pid}/articles")
        except Exception:
            arts = []
        try:
            dss = client.get(f"/api/projects/{pid}/datasets")
        except Exception:
            dss = []
        try:
            cks = client.get(f"/api/projects/{pid}/checklists")
        except Exception:
            cks = []
        print(f"  {p['title']}")
        print(f"      id: {pid}")
        print(f"      study_type: {p.get('study_type')}  template: {p.get('template_journal')}")
        print(f"      articles: {len(arts)}  datasets: {len(dss)}  checklists: {len(cks)}")
    print(f"\nTotal seed projects: {len(seeded)}")
    print(f"Open the web UI: http://localhost:5173/")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="seed_demo",
        description="Seed three realistic demo projects into a local Research Assistant backend.",
    )
    p.add_argument(
        "--base-url",
        default=os.environ.get("RMA_BASE_URL", DEFAULT_BASE_URL),
        help=f"Backend base URL (default: {DEFAULT_BASE_URL}).",
    )
    p.add_argument(
        "--email",
        default=os.environ.get("RMA_DEMO_EMAIL"),
        help=(
            "Sign in as this user (S1 auth-enabled backends). "
            "Omit to rely on RMA_DISABLE_AUTH=1 mode."
        ),
    )
    p.add_argument(
        "--password",
        default=os.environ.get("RMA_DEMO_PASSWORD"),
        help="Password for --email login.",
    )
    p.add_argument(
        "--signup",
        action="store_true",
        help="If login fails with 401, create the account via /api/auth/signup.",
    )
    p.add_argument(
        "--force-reset",
        action="store_true",
        help="Delete existing seed projects (prefixed with [SEED-DEMO]) before re-seeding.",
    )
    p.add_argument(
        "--skip-a",
        action="store_true",
        help="Skip Project A (Ortho SR).",
    )
    p.add_argument(
        "--skip-b",
        action="store_true",
        help="Skip Project B (RCT).",
    )
    p.add_argument(
        "--skip-c",
        action="store_true",
        help="Skip Project C (Surgery cohort).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    client = ApiClient(args.base_url)

    try:
        health = client.check_health()
    except Exception as exc:
        print(f"error: cannot reach backend at {args.base_url}: {exc}", file=sys.stderr)
        return 1
    print(f"backend ok: db={health.get('db_ok')} storage={health.get('storage_backend')}")

    # Authenticate if creds were provided. Otherwise rely on the dev-mode
    # legacy-user fallback. We still test /api/projects below to surface a
    # clear 401 if auth is on but no creds were given.
    if args.email and args.password:
        try:
            user = client.login_or_signup(
                args.email, args.password, allow_signup=args.signup
            )
            print(f"signed in: {user.get('email')} ({user.get('id')})")
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    try:
        client.get("/api/projects")
    except Exception as exc:
        print(
            "error: GET /api/projects failed. Either set RMA_DISABLE_AUTH=1 on the\n"
            "backend and restart, or pass --email/--password to sign in.\n"
            f"underlying: {exc}",
            file=sys.stderr,
        )
        return 1

    if args.force_reset:
        wipe_seed_projects(client)

    if not args.skip_a:
        try:
            seed_project_a_ortho(client)
        except Exception as exc:
            print(f"[A] FAILED: {exc}", file=sys.stderr)
    if not args.skip_b:
        try:
            seed_project_b_rct(client)
        except Exception as exc:
            print(f"[B] FAILED: {exc}", file=sys.stderr)
    if not args.skip_c:
        try:
            seed_project_c_cohort(client)
        except Exception as exc:
            print(f"[C] FAILED: {exc}", file=sys.stderr)

    print_summary(client)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
