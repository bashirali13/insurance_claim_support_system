"""Deterministic rule tables (data-model.md). No model involved."""

import pytest

from claim_intake.contracts import (
    Contradiction,
    CoverageLine,
    IncidentType,
    MissingItem,
    TriState,
    UmUimSubtype,
)
from claim_intake.rules import coverage_lines, injury_present, missing_information
from tests.builders import assessment_output

# --- US2: injury, missing information, coverage lines ---------------------------------------


def test_ac_2_5_injury_present_is_unknown_when_not_stated():
    facts = assessment_output(customer_side_injured=TriState.UNKNOWN, others_injured=TriState.NO)

    assert injury_present(facts) == TriState.UNKNOWN


@pytest.mark.parametrize("injured_side", ["customer_side_injured", "others_injured"])
def test_ac_2_5_injury_present_yes_when_either_side_injured(injured_side):
    facts = assessment_output(**{injured_side: TriState.YES})

    assert injury_present(facts) == TriState.YES


def test_ac_3_3_injury_contradiction_makes_injury_unknown():
    facts = assessment_output(
        customer_side_injured=TriState.YES,
        contradictions=[
            Contradiction(
                statement_a="Nobody was hurt.",
                statement_b="My passenger went to the ER.",
                about_injury=True,
            )
        ],
    )

    assert injury_present(facts) == TriState.UNKNOWN


def test_ac_2_6_hit_and_run_collision_missing_date_location_police_report():
    facts = assessment_output(
        um_uim_subtype=UmUimSubtype.HIT_AND_RUN,
        incident_date=None,
        location=None,
        police_report_mentioned=TriState.UNKNOWN,
    )

    assert missing_information(facts) == [
        MissingItem.INCIDENT_DATE,
        MissingItem.LOCATION,
        MissingItem.POLICE_REPORT,
    ]


def test_ac_2_6_solo_collision_without_injury_does_not_require_police_report():
    facts = assessment_output(other_party_involved=TriState.NO, other_property_damaged=TriState.YES)

    assert missing_information(facts) == []


def test_ac_2_6_collision_with_injury_requires_police_report():
    facts = assessment_output(customer_side_injured=TriState.YES)

    assert missing_information(facts) == [MissingItem.POLICE_REPORT]


def test_ac_2_6_collision_with_unclear_other_party_asks_about_it():
    facts = assessment_output(other_party_involved=TriState.UNKNOWN)

    assert missing_information(facts) == [MissingItem.OTHER_PARTY_INVOLVEMENT]


@pytest.mark.parametrize("incident", [IncidentType.THEFT, IncidentType.VANDALISM])
def test_ac_2_6_theft_and_vandalism_require_police_report(incident):
    facts = assessment_output(incident_type=incident, police_report_mentioned=TriState.NO)

    assert MissingItem.POLICE_REPORT in missing_information(facts)


def test_ac_2_6_theft_requires_police_report():
    facts = assessment_output(incident_type=IncidentType.THEFT, police_report_mentioned=TriState.NO)

    assert missing_information(facts) == [MissingItem.POLICE_REPORT]


def test_ac_2_6_theft_does_not_require_damage_description():
    facts = assessment_output(
        incident_type=IncidentType.THEFT,
        damage_areas=[],
        police_report_mentioned=TriState.YES,
    )

    assert missing_information(facts) == []


def test_ac_2_6_other_incidents_require_damage_description():
    facts = assessment_output(incident_type=IncidentType.WEATHER, damage_areas=[])

    assert missing_information(facts) == [MissingItem.DAMAGE_DESCRIPTION]


def test_ac_2_6_unknown_requires_what_happened():
    facts = assessment_output(incident_type=IncidentType.UNKNOWN, incident_date=None, location=None)

    assert missing_information(facts) == [
        MissingItem.WHAT_HAPPENED,
        MissingItem.INCIDENT_DATE,
        MissingItem.LOCATION,
    ]


def test_ac_2_6_mixed_has_no_missing_items():
    facts = assessment_output(incident_type=IncidentType.MIXED, incident_date=None, location=None)

    assert missing_information(facts) == []


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"incident_type": IncidentType.COLLISION}, [CoverageLine.COLLISION]),
        ({"incident_type": IncidentType.THEFT}, [CoverageLine.COMPREHENSIVE]),
        ({"incident_type": IncidentType.VANDALISM}, [CoverageLine.COMPREHENSIVE]),
        ({"incident_type": IncidentType.WEATHER}, [CoverageLine.COMPREHENSIVE]),
        ({"incident_type": IncidentType.FIRE}, [CoverageLine.COMPREHENSIVE]),
        ({"incident_type": IncidentType.GLASS}, [CoverageLine.COMPREHENSIVE]),
        ({"incident_type": IncidentType.ANIMAL_STRIKE}, [CoverageLine.COMPREHENSIVE]),
        ({"incident_type": IncidentType.UNKNOWN}, []),
        ({"incident_type": IncidentType.MIXED}, []),
        (
            {"others_injured": TriState.YES},
            [CoverageLine.COLLISION, CoverageLine.LIABILITY_BODILY_INJURY],
        ),
        (
            {"other_property_damaged": TriState.YES},
            [CoverageLine.COLLISION, CoverageLine.LIABILITY_PROPERTY_DAMAGE],
        ),
        (
            {"um_uim_subtype": UmUimSubtype.UNINSURED},
            [CoverageLine.COLLISION, CoverageLine.UM_UIM],
        ),
        (
            {"customer_side_injured": TriState.YES},
            [CoverageLine.COLLISION, CoverageLine.PIP_MEDPAY],
        ),
    ],
)
def test_ac_2_8_coverage_lines_follow_rule_table(overrides, expected):
    assert coverage_lines(assessment_output(**overrides)) == expected


def test_ac_2_8_hit_and_run_with_injured_customer_gets_three_lines():
    facts = assessment_output(
        um_uim_subtype=UmUimSubtype.HIT_AND_RUN, customer_side_injured=TriState.YES
    )

    assert coverage_lines(facts) == [
        CoverageLine.COLLISION,
        CoverageLine.UM_UIM,
        CoverageLine.PIP_MEDPAY,
    ]
