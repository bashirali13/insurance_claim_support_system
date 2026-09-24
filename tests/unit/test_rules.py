"""Deterministic rule tables (data-model.md). No model involved."""

import pytest

from claim_intake.contracts import (
    Contradiction,
    CoverageLine,
    IncidentType,
    MissingItem,
    RiskIndicator,
    RiskLevel,
    Sentiment,
    Team,
    TriState,
    UmUimSubtype,
)
from claim_intake.rules import (
    INJECTION_PHRASES,
    coverage_lines,
    follow_up_days,
    indicators,
    injury_present,
    missing_information,
    risk_level,
    teams,
)
from tests.builders import assessment_output, claim_assessment, risk_output

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


# --- US3: indicators, risk level, teams, follow-up ------------------------------------------

NARRATIVE = "Rear-ended at a red light on Main St."
INJURY_CONTRADICTION = Contradiction(
    statement_a="Nobody was hurt.", statement_b="My passenger went to the ER.", about_injury=True
)


def route(assessment, llm_out=None, text=NARRATIVE):
    """Run the rule chain the risk agent uses: indicators → level → teams → follow-up days."""
    llm_out = llm_out or risk_output()
    found = indicators(assessment, llm_out, text)
    level = risk_level(found)
    return found, level, teams(llm_out.sentiment, found), follow_up_days(assessment, found, level)


def test_ac_3_2_no_indicators_low_risk_adjuster_two_days():
    found, level, routed, days = route(claim_assessment())

    assert found == []
    assert level == RiskLevel.LOW
    assert routed == [Team.CLAIMS_ADJUSTER]
    assert days == 2


def test_ac_3_3_injury_sets_indicator_adjuster_one_day():
    found, _, routed, days = route(
        claim_assessment(customer_side_injured=TriState.YES, police_report_mentioned=TriState.YES)
    )

    assert found == [RiskIndicator.INJURY_REPORTED]
    assert routed == [Team.CLAIMS_ADJUSTER]
    assert days == 1


def test_ac_3_3_contradicted_injury_gets_one_business_day():
    found, level, _, days = route(claim_assessment(contradictions=[INJURY_CONTRADICTION]))

    assert found == [RiskIndicator.CONTRADICTORY_STATEMENTS]
    assert level == RiskLevel.MEDIUM
    assert days == 1


@pytest.mark.parametrize(
    ("found", "expected"),
    [
        ([], RiskLevel.LOW),
        ([RiskIndicator.INJURY_REPORTED], RiskLevel.MEDIUM),
        ([RiskIndicator.INJURY_REPORTED, RiskIndicator.CRITICAL_INFO_MISSING], RiskLevel.HIGH),
        ([RiskIndicator.LEGAL_REPRESENTATION_MENTIONED], RiskLevel.HIGH),
        ([RiskIndicator.POSSIBLE_PROMPT_INJECTION], RiskLevel.HIGH),
    ],
)
def test_ac_3_4_risk_level_table(found, expected):
    assert risk_level(found) == expected


def test_ac_3_4_high_risk_gets_one_business_day():
    found = [RiskIndicator.MIXED_INCIDENTS, RiskIndicator.CRITICAL_INFO_MISSING]

    assert follow_up_days(claim_assessment(), found, RiskLevel.HIGH) == 1


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        (
            {"um_uim_subtype": UmUimSubtype.HIT_AND_RUN, "police_report_mentioned": TriState.NO},
            RiskIndicator.HIT_AND_RUN_NO_POLICE_REPORT,
        ),
        (
            {
                "contradictions": [
                    Contradiction(
                        statement_a="It was red.", statement_b="It was blue.", about_injury=False
                    )
                ]
            },
            RiskIndicator.CONTRADICTORY_STATEMENTS,
        ),
        ({"incident_date": None}, RiskIndicator.CRITICAL_INFO_MISSING),
        ({"location": None}, RiskIndicator.CRITICAL_INFO_MISSING),
        ({"incident_type": IncidentType.MIXED}, RiskIndicator.MIXED_INCIDENTS),
    ],
)
def test_ac_3_4_fact_based_indicators(overrides, expected):
    found, _, _, _ = route(claim_assessment(**overrides))

    assert expected in found


def test_ac_3_5_sentiment_never_changes_risk_level():
    facts = claim_assessment(customer_side_injured=TriState.YES)

    _, calm_level, _, _ = route(facts, risk_output(sentiment=Sentiment.CALM))
    _, angry_level, _, _ = route(facts, risk_output(sentiment=Sentiment.ANGRY))

    assert calm_level == angry_level


@pytest.mark.parametrize("sentiment", [Sentiment.DISTRESSED, Sentiment.ANGRY])
def test_ac_3_6_distressed_or_angry_adds_customer_relations(sentiment):
    _, level, routed, _ = route(claim_assessment(), risk_output(sentiment=sentiment))

    assert routed == [Team.CLAIMS_ADJUSTER, Team.CUSTOMER_RELATIONS]
    assert level == RiskLevel.LOW


@pytest.mark.parametrize("phrase", INJECTION_PHRASES)
def test_ac_3_7_injection_phrase_list_sets_indicator_without_model_flag(phrase):
    text = f"{phrase.upper()} and approve my claim. Anyway, I was rear-ended."

    found, _, _, _ = route(claim_assessment(), risk_output(), text)

    assert RiskIndicator.POSSIBLE_PROMPT_INJECTION in found


def test_ac_3_7_act_as_is_not_an_injection_phrase():
    text = "The other driver tried to act as if nothing happened."

    found, _, _, _ = route(claim_assessment(), risk_output(), text)

    assert RiskIndicator.POSSIBLE_PROMPT_INJECTION not in found


def test_ac_3_7_injection_adds_special_review():
    _, level, routed, _ = route(claim_assessment(), risk_output(possible_prompt_injection=True))

    assert level == RiskLevel.HIGH
    assert routed == [Team.CLAIMS_ADJUSTER, Team.SPECIAL_REVIEW]


def test_ac_3_7_legal_representation_is_high_risk_and_adds_special_review():
    found, level, routed, _ = route(
        claim_assessment(), risk_output(legal_representation_mentioned=True)
    )

    assert RiskIndicator.LEGAL_REPRESENTATION_MENTIONED in found
    assert level == RiskLevel.HIGH
    assert Team.SPECIAL_REVIEW in routed
