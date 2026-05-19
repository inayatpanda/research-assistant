"""Phase 17 (MP17) — Curated 30-item outcome-instrument catalogue.

Pure declarative module. The catalogue is referenced from the route layer
(`/api/instruments/catalogue`) and from the SAP export to render instrument
descriptions. The dataset variable binding (``dataset_variables.instrument_key``)
stores the abbreviation as a string — NEVER an FK to an instrument row in
the DB; the catalogue is code-resident so users can upgrade-in-place without
a data migration.

Hard rule reminder: instrument bindings are PURE METADATA. They never alter
the statistics, the data, the chart axes, or the runner behaviour.
"""
from __future__ import annotations

from typing import Final

from research_api.schemas.instruments import InstrumentSpec

# Note: when ``mid=None``, the MID for the instrument is not well established
# in the literature; reports should phrase this as "no widely accepted MID".

_CATALOGUE: Final[list[InstrumentSpec]] = [
    # ─── Hip / Knee ────────────────────────────────────────────────────────
    InstrumentSpec(
        name="Harris Hip Score",
        abbreviation="HHS",
        scale_low=0.0,
        scale_high=100.0,
        mid=8.0,
        direction="higher_better",
        category="hip_knee",
        default_citation="Harris WH. J Bone Joint Surg Am. 1969;51(4):737-55.",
    ),
    InstrumentSpec(
        name="Oxford Hip Score",
        abbreviation="OHS",
        scale_low=0.0,
        scale_high=48.0,
        mid=5.0,
        direction="higher_better",
        category="hip_knee",
        default_citation="Dawson J et al. J Bone Joint Surg Br. 1996;78(2):185-90.",
    ),
    InstrumentSpec(
        name="Oxford Knee Score",
        abbreviation="OKS",
        scale_low=0.0,
        scale_high=48.0,
        mid=5.0,
        direction="higher_better",
        category="hip_knee",
        default_citation="Dawson J et al. J Bone Joint Surg Br. 1998;80(1):63-9.",
    ),
    InstrumentSpec(
        name="Knee Society Score",
        abbreviation="KSS",
        scale_low=0.0,
        scale_high=200.0,
        mid=None,
        direction="higher_better",
        category="hip_knee",
        default_citation="Insall JN et al. Clin Orthop Relat Res. 1989;(248):13-4.",
    ),
    InstrumentSpec(
        name="Knee Injury and Osteoarthritis Outcome Score",
        abbreviation="KOOS",
        scale_low=0.0,
        scale_high=100.0,
        mid=None,
        direction="higher_better",
        category="hip_knee",
        default_citation="Roos EM et al. J Orthop Sports Phys Ther. 1998;28(2):88-96.",
    ),
    InstrumentSpec(
        name="Western Ontario and McMaster Universities Arthritis Index",
        abbreviation="WOMAC",
        scale_low=0.0,
        scale_high=96.0,
        mid=12.0,
        direction="lower_better",
        category="hip_knee",
        default_citation="Bellamy N et al. J Rheumatol. 1988;15(12):1833-40.",
    ),
    InstrumentSpec(
        name="Forgotten Joint Score-12",
        abbreviation="FJS-12",
        scale_low=0.0,
        scale_high=100.0,
        mid=None,
        direction="higher_better",
        category="hip_knee",
        default_citation="Behrend H et al. J Arthroplasty. 2012;27(3):430-6.",
    ),
    InstrumentSpec(
        name="UCLA Activity Score",
        abbreviation="UCLA",
        scale_low=1.0,
        scale_high=10.0,
        mid=None,
        direction="higher_better",
        category="hip_knee",
        default_citation="Amstutz HC et al. J Bone Joint Surg Am. 1984;66(2):228-41.",
    ),
    # ─── Spine ─────────────────────────────────────────────────────────────
    InstrumentSpec(
        name="Oswestry Disability Index",
        abbreviation="ODI",
        scale_low=0.0,
        scale_high=100.0,
        mid=10.0,
        direction="lower_better",
        category="spine",
        default_citation="Fairbank JC et al. Physiotherapy. 1980;66(8):271-3.",
    ),
    InstrumentSpec(
        name="Neck Disability Index",
        abbreviation="NDI",
        scale_low=0.0,
        scale_high=50.0,
        mid=None,
        direction="lower_better",
        category="spine",
        default_citation="Vernon H, Mior S. J Manipulative Physiol Ther. 1991;14(7):409-15.",
    ),
    InstrumentSpec(
        name="Roland-Morris Disability Questionnaire",
        abbreviation="RMDQ",
        scale_low=0.0,
        scale_high=24.0,
        mid=None,
        direction="lower_better",
        category="spine",
        default_citation="Roland M, Morris R. Spine. 1983;8(2):141-4.",
    ),
    InstrumentSpec(
        name="Japanese Orthopaedic Association Score (back)",
        abbreviation="JOA-back",
        scale_low=0.0,
        scale_high=29.0,
        mid=None,
        direction="higher_better",
        category="spine",
        default_citation="Japanese Orthopaedic Association. J Jpn Orthop Assoc. 1986.",
    ),
    # ─── Shoulder / Elbow ──────────────────────────────────────────────────
    InstrumentSpec(
        name="Constant-Murley Score",
        abbreviation="Constant-Murley",
        scale_low=0.0,
        scale_high=100.0,
        mid=None,
        direction="higher_better",
        category="shoulder_elbow",
        default_citation="Constant CR, Murley AH. Clin Orthop Relat Res. 1987;(214):160-4.",
    ),
    InstrumentSpec(
        name="Disabilities of the Arm, Shoulder and Hand",
        abbreviation="DASH",
        scale_low=0.0,
        scale_high=100.0,
        mid=10.0,
        direction="lower_better",
        category="shoulder_elbow",
        default_citation="Hudak PL et al. Am J Ind Med. 1996;29(6):602-8.",
    ),
    InstrumentSpec(
        name="Quick-DASH",
        abbreviation="Quick-DASH",
        scale_low=0.0,
        scale_high=100.0,
        mid=None,
        direction="lower_better",
        category="shoulder_elbow",
        default_citation="Beaton DE et al. J Hand Ther. 2001;14(2):128-46.",
    ),
    InstrumentSpec(
        name="Oxford Shoulder Score",
        abbreviation="OSS",
        scale_low=0.0,
        scale_high=48.0,
        mid=None,
        direction="higher_better",
        category="shoulder_elbow",
        default_citation="Dawson J et al. J Bone Joint Surg Br. 1996;78(4):593-600.",
    ),
    InstrumentSpec(
        name="American Shoulder and Elbow Surgeons Score",
        abbreviation="ASES",
        scale_low=0.0,
        scale_high=100.0,
        mid=None,
        direction="higher_better",
        category="shoulder_elbow",
        default_citation="Richards RR et al. J Shoulder Elbow Surg. 1994;3(6):347-52.",
    ),
    InstrumentSpec(
        name="PROMIS Upper Extremity",
        abbreviation="PROMIS UE",
        scale_low=0.0,
        scale_high=100.0,
        mid=None,
        direction="higher_better",
        category="shoulder_elbow",
        default_citation="PROMIS Health Organization. promishealth.org.",
    ),
    # ─── Foot / Ankle ──────────────────────────────────────────────────────
    InstrumentSpec(
        name="American Orthopaedic Foot & Ankle Society Score",
        abbreviation="AOFAS",
        scale_low=0.0,
        scale_high=100.0,
        mid=None,
        direction="higher_better",
        category="foot_ankle",
        default_citation="Kitaoka HB et al. Foot Ankle Int. 1994;15(7):349-53.",
    ),
    InstrumentSpec(
        name="Foot and Ankle Outcome Score",
        abbreviation="FAOS",
        scale_low=0.0,
        scale_high=100.0,
        mid=None,
        direction="higher_better",
        category="foot_ankle",
        default_citation="Roos EM et al. Foot Ankle Int. 2001;22(10):788-94.",
    ),
    InstrumentSpec(
        name="Manchester-Oxford Foot Questionnaire",
        abbreviation="MOXFQ",
        scale_low=0.0,
        scale_high=100.0,
        mid=None,
        direction="lower_better",
        category="foot_ankle",
        default_citation="Dawson J et al. Qual Life Res. 2006;15(7):1211-22.",
    ),
    # ─── Generic ───────────────────────────────────────────────────────────
    InstrumentSpec(
        name="Visual Analogue Scale — Pain",
        abbreviation="VAS Pain",
        scale_low=0.0,
        scale_high=10.0,
        mid=2.0,
        direction="lower_better",
        category="generic",
        default_citation="Huskisson EC. Lancet. 1974;304(7889):1127-31.",
    ),
    InstrumentSpec(
        name="Numerical Rating Scale",
        abbreviation="NRS",
        scale_low=0.0,
        scale_high=10.0,
        mid=None,
        direction="lower_better",
        category="generic",
        default_citation="Hawker GA et al. Arthritis Care Res. 2011;63(S11):S240-52.",
    ),
    InstrumentSpec(
        name="Short Form-36",
        abbreviation="SF-36",
        scale_low=0.0,
        scale_high=100.0,
        mid=None,
        direction="higher_better",
        category="generic",
        default_citation="Ware JE, Sherbourne CD. Med Care. 1992;30(6):473-83.",
    ),
    InstrumentSpec(
        name="Short Form-12",
        abbreviation="SF-12",
        scale_low=0.0,
        scale_high=100.0,
        mid=None,
        direction="higher_better",
        category="generic",
        default_citation="Ware JE et al. Med Care. 1996;34(3):220-33.",
    ),
    InstrumentSpec(
        name="EQ-5D-3L",
        abbreviation="EQ-5D-3L",
        scale_low=-0.594,
        scale_high=1.0,
        mid=None,
        direction="higher_better",
        category="generic",
        default_citation="EuroQol Group. Health Policy. 1990;16(3):199-208.",
    ),
    InstrumentSpec(
        name="EQ-5D-5L",
        abbreviation="EQ-5D-5L",
        scale_low=-0.285,
        scale_high=1.0,
        mid=None,
        direction="higher_better",
        category="generic",
        default_citation="Herdman M et al. Qual Life Res. 2011;20(10):1727-36.",
    ),
    InstrumentSpec(
        name="EQ-5D-Y",
        abbreviation="EQ-5D-Y",
        scale_low=-0.594,
        scale_high=1.0,
        mid=None,
        direction="higher_better",
        category="generic",
        default_citation="Wille N et al. Qual Life Res. 2010;19(6):875-86.",
    ),
    InstrumentSpec(
        name="PROMIS Global Health",
        abbreviation="PROMIS Global Health",
        scale_low=0.0,
        scale_high=100.0,
        mid=None,
        direction="higher_better",
        category="generic",
        default_citation="Hays RD et al. Qual Life Res. 2009;18(7):873-80.",
    ),
    InstrumentSpec(
        name="PROMIS Physical Function CAT",
        abbreviation="PROMIS PF CAT",
        scale_low=0.0,
        scale_high=100.0,
        mid=None,
        direction="higher_better",
        category="generic",
        default_citation="Rose M et al. Qual Life Res. 2008;17(2):285-97.",
    ),
    InstrumentSpec(
        name="Patient Specific Functional Scale",
        abbreviation="PSFS",
        scale_low=0.0,
        scale_high=10.0,
        mid=2.0,
        direction="higher_better",
        category="generic",
        default_citation="Stratford P et al. Physiother Can. 1995;47(4):258-63.",
    ),
    # ─── Cardio ────────────────────────────────────────────────────────────
    InstrumentSpec(
        name="New York Heart Association Class",
        abbreviation="NYHA",
        scale_low=1.0,
        scale_high=4.0,
        mid=None,
        direction="lower_better",
        category="cardio",
        default_citation="The Criteria Committee of the New York Heart Association. 1994.",
    ),
]


def list_instruments() -> list[InstrumentSpec]:
    """Return the full catalogue list (defensive copy)."""

    return list(_CATALOGUE)


def get_instrument(abbreviation: str) -> InstrumentSpec | None:
    """Look up by abbreviation. Returns ``None`` for unknown keys (allow
    the caller to handle the user-facing 404)."""

    for spec in _CATALOGUE:
        if spec.abbreviation == abbreviation:
            return spec
    return None


def is_known_key(abbreviation: str | None) -> bool:
    if not abbreviation:
        return False
    return any(s.abbreviation == abbreviation for s in _CATALOGUE)


__all__ = ["list_instruments", "get_instrument", "is_known_key"]
