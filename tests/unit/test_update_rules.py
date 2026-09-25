"""US7: deciding what an update changed, and the claim's status and date afterwards (rules only)."""

from datetime import date

import pytest

from claim_intake.contracts import (
    ClaimStatus,
    IncidentType,
    MissingItem,
    RiskLevel,
    TriState,
    UmUimSubtype,
)
from claim_intake.rules import diff_facts, earliest_follow_up, status_after_update
from tests.builders import assessment_output

SAVED = assessment_output(
    incident_date="yesterday around 6pm",
    location="Main St",
    damage_areas=["rear bumper"],
    customer_side_injured=TriState.YES,
    police_report_mentioned=TriState.UNKNOWN,
)


def updated(**changes):
    return SAVED.model_copy(update=changes)


def test_ac_7_1_police_report_unknown_to_yes_is_added():
    changes = diff_facts(SAVED, updated(police_report_mentioned=TriState.YES))

    assert [(c.field, c.old, c.new) for c in changes.added] == [
        ("police_report_mentioned", None, "YES")
    ]
    assert changes.applied.police_report_mentioned == TriState.YES


def test_ac_7_1_new_damage_items_are_added_and_list_never_shrinks():
    changes = diff_facts(SAVED, updated(damage_areas=["rear door"]))

    assert [(c.field, c.new) for c in changes.added] == [("damage_areas", "rear door")]
    assert changes.applied.damage_areas == ["rear bumper", "rear door"]


def test_ac_7_2_changed_incident_time_is_a_corrected_change_and_applied():
    changes = diff_facts(SAVED, updated(incident_date="around 7pm"))

    assert [(c.field, c.old, c.new) for c in changes.corrected] == [
        ("incident_date", "yesterday around 6pm", "around 7pm")
    ]
    assert changes.applied.incident_date == "around 7pm"


@pytest.mark.parametrize(
    ("change", "kind"),
    [
        ({"location": "Oak Ave"}, "corrected"),
        ({"location": None}, "corrected"),  # value → unknown
        ({"vehicle_drivable": TriState.NO}, "corrected"),
        ({"vehicle_drivable": TriState.UNKNOWN}, "corrected"),
        ({"other_property_damaged": TriState.YES}, "corrected"),
        ({"police_report_mentioned": TriState.NO}, "added"),  # was UNKNOWN
        ({"um_uim_subtype": UmUimSubtype.HIT_AND_RUN}, "added"),  # was None
        ({"others_injured": TriState.UNKNOWN}, "sensitive"),  # known → unknown, sensitive field
        ({"other_party_involved": TriState.NO}, "sensitive"),
    ],
)
def test_ac_7_2_diff_rules_for_every_field_kind(change, kind):
    changes = diff_facts(SAVED, updated(**change))

    (field,) = change
    assert [c.field for c in getattr(changes, kind)] == [field]


def test_ac_7_4_injury_yes_to_no_is_sensitive_and_saved_value_kept():
    changes = diff_facts(SAVED, updated(customer_side_injured=TriState.NO))

    assert [(c.field, c.old, c.new) for c in changes.sensitive] == [
        ("customer_side_injured", "YES", "NO")
    ]
    assert changes.corrected == []
    assert changes.applied.customer_side_injured == TriState.YES


def test_ac_7_4_incident_type_change_is_sensitive():
    changes = diff_facts(SAVED, updated(incident_type=IncidentType.THEFT))

    assert [c.field for c in changes.sensitive] == ["incident_type"]
    assert changes.applied.incident_type == IncidentType.COLLISION


def test_ac_7_4_injury_unknown_to_yes_is_added_and_applied_immediately():
    saved = SAVED.model_copy(update={"others_injured": TriState.UNKNOWN})

    changes = diff_facts(saved, saved.model_copy(update={"others_injured": TriState.YES}))

    assert [c.field for c in changes.added] == ["others_injured"]
    assert changes.sensitive == []
    assert changes.applied.others_injured == TriState.YES


def test_ac_7_6_identical_facts_produce_empty_changes():
    assert diff_facts(SAVED, SAVED).is_empty


@pytest.mark.parametrize(
    ("current", "level", "missing", "expected"),
    [
        (ClaimStatus.ESCALATED, RiskLevel.LOW, [], ClaimStatus.ESCALATED),
        (ClaimStatus.SUBMITTED, RiskLevel.HIGH, [], ClaimStatus.ESCALATED),
        (
            ClaimStatus.UNDER_REVIEW,
            RiskLevel.MEDIUM,
            [MissingItem.LOCATION],
            ClaimStatus.UNDER_REVIEW,
        ),
        (
            ClaimStatus.SUBMITTED,
            RiskLevel.LOW,
            [MissingItem.POLICE_REPORT],
            ClaimStatus.AWAITING_INFORMATION,
        ),
        (ClaimStatus.AWAITING_INFORMATION, RiskLevel.LOW, [], ClaimStatus.SUBMITTED),
    ],
)
def test_ac_7_5_status_after_update_priority(current, level, missing, expected):
    assert status_after_update(current, level, missing) == expected


def test_ac_7_5_claim_follow_up_date_is_earliest_promise():
    thursday = date(2026, 9, 24)

    assert earliest_follow_up(thursday, [2, 1, 3]) == date(2026, 9, 25)
