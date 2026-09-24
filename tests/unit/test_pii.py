"""US1: deterministic PII detection and placeholders (no model involved)."""

import pytest

from claim_intake.contracts import PiiType
from claim_intake.pii import find_pii, scrub_patterns

# One fictional value per detectable type, written the way a customer might.
PII_EXAMPLES = [
    (PiiType.PHONE, "Call me at 555-201-3344 tonight.", "555-201-3344"),
    (PiiType.EMAIL, "Email jordan.reyes@example.com please.", "jordan.reyes@example.com"),
    (PiiType.SSN, "My SSN is 123-45-6789.", "123-45-6789"),
    (PiiType.CARD, "Charge card 4111 1111 1111 1111 for the tow.", "4111 1111 1111 1111"),
    (PiiType.DOB, "I was born 03/14/1985 in Ohio.", "03/14/1985"),
    (PiiType.DRIVER_LICENSE, "My license number D1234567 was checked.", "D1234567"),
    (PiiType.VIN, "The VIN is 1HGCM82633A004352.", "1HGCM82633A004352"),
    (PiiType.PLATE, "Their plate 7XYZ123 was visible.", "7XYZ123"),
    (PiiType.POLICY_NUMBER, "My policy number NAI-4471823 is active.", "NAI-4471823"),
    (PiiType.ADDRESS, "It happened outside 412 Oak Street last night.", "412 Oak Street"),
]


@pytest.mark.parametrize(("pii_type", "text", "value"), PII_EXAMPLES, ids=lambda x: str(x))
def test_ac_1_1_each_detectable_type_is_replaced_with_typed_placeholder(pii_type, text, value):
    # Given a narrative containing one personal value
    # When it is scrubbed
    scrubbed, removed = scrub_patterns(text)

    # Then the value is gone, replaced by a placeholder labeled with its type
    assert value not in scrubbed
    assert f"[{pii_type}_1]" in scrubbed
    assert removed == [pii_type]


def test_ac_1_1_all_types_in_one_narrative_are_removed():
    narrative = " ".join(text for _, text, _ in PII_EXAMPLES)

    scrubbed, removed = scrub_patterns(narrative)

    for pii_type, _, value in PII_EXAMPLES:
        assert value not in scrubbed
        assert pii_type in removed


def test_ac_1_1_rejects_luhn_invalid_card_number():
    text = "Reference 4111 1111 1111 1112 from the tow company."

    scrubbed, removed = scrub_patterns(text)

    assert scrubbed == text
    assert removed == []


def test_ac_1_1_rejects_ssn_with_invalid_area_number():
    text = "Form code 666-12-3456 was on the receipt."

    scrubbed, removed = scrub_patterns(text)

    assert PiiType.SSN not in removed


def test_ac_1_2_same_value_same_placeholder_distinct_values_numbered():
    text = "Call 555-201-3344 or 555-201-3344, or my wife at 555-777-8888."

    scrubbed, _ = scrub_patterns(text)

    assert scrubbed == "Call [PHONE_1] or [PHONE_1], or my wife at [PHONE_2]."


def test_ac_1_5_preserves_incident_time_street_name_and_damage():
    text = (
        "Yesterday around 6pm I was stopped at a red light on Main St when a pickup "
        "hit my rear bumper near I-95. My F150 is damaged."
    )

    scrubbed, removed = scrub_patterns(text)

    assert scrubbed == text
    assert removed == []


def test_ac_1_6_dob_removed_only_with_birth_context():
    text = "I was born 03/14/1985. On 09/23/2026 I was hit from behind."

    scrubbed, removed = scrub_patterns(text)

    assert "03/14/1985" not in scrubbed
    assert "On 09/23/2026 I was hit" in scrubbed
    assert removed == [PiiType.DOB]


def test_ac_1_8_find_pii_reports_residual_types():
    assert find_pii("My SSN is 123-45-6789.") == [PiiType.SSN]


def test_ac_1_8_find_pii_ignores_placeholders():
    assert find_pii("Call [PHONE_1] and ask for [PERSON_1].") == []
