"""US12: the release documentation stays true to the code (research R6, R7).

These check structure and safety, never exact wording: samples come from real-model runs.
"""

import json
import re
from pathlib import Path

import pytest

from claim_intake import cli
from claim_intake.pii import find_pii
from claim_intake.reporting import DECISION_NOTICE

ROOT = Path(__file__).parents[2]
README = ROOT / "README.md"
ARCHITECTURE = ROOT / "docs" / "architecture.md"
SAMPLES = sorted((ROOT / "docs" / "samples").glob("*.md"))
NARRATIVES = ROOT / "tests" / "fixtures" / "narratives"

MODULES = [
    "cli",
    "orchestration",
    "existing_claims",
    "intake",
    "assessment",
    "risk",
    "summary",
    "rules",
    "pii",
    "reporting",
    "storage",
]


def mermaid_blocks(text: str) -> list[str]:
    return re.findall(r"```mermaid\n(.*?)```", text, flags=re.DOTALL)


def known_personal_values() -> set[str]:
    """Every fictional personal value the fixtures use; none may reach a sample."""
    values = set()
    for case in json.loads((NARRATIVES / "pii_cases.json").read_text(encoding="utf-8")):
        values.update(case["must_not_contain"])
    for case in json.loads((NARRATIVES / "adversarial_cases.json").read_text(encoding="utf-8")):
        values.update(case["secrets"])
    return values


def section(text: str, heading: str) -> str:
    """The text under a `## heading`, up to the next `## ` heading."""
    after = text.split(f"## {heading}\n", 1)[1]
    return after.split("\n## ", 1)[0]


def test_ac_12_2_readme_relative_links_resolve():
    links = re.findall(r"\]\(([^)#\s]+)", README.read_text(encoding="utf-8"))
    relative = [link for link in links if not link.startswith(("http://", "https://"))]

    assert relative, "the README links to nothing"
    assert [link for link in relative if not (ROOT / link).exists()] == []


def test_ac_12_2_readme_cli_flags_are_real_options(capsys):
    commands = re.findall(r"claim-support((?:[ \t]+--[\w-]+)+)", README.read_text(encoding="utf-8"))
    flags = {flag for command in commands for flag in command.split()}
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    help_text = capsys.readouterr().out

    assert {"--load-samples", "--trace"} <= flags
    assert [flag for flag in flags if flag not in help_text] == []


def test_ac_12_3_architecture_mermaid_names_every_module():
    diagrams = "\n".join(mermaid_blocks(ARCHITECTURE.read_text(encoding="utf-8")))

    assert [m for m in MODULES if not re.search(rf"\b{m}\b", diagrams)] == []


def test_ac_12_3_readme_embeds_a_diagram_and_links_the_architecture():
    readme = README.read_text(encoding="utf-8")

    assert mermaid_blocks(readme)
    assert "](docs/architecture.md)" in readme


def test_ac_12_4_samples_cover_filing_update_help_privacy_and_escalation():
    names = [sample.stem for sample in SAMPLES]

    for kind in ("filing-", "update-", "help-"):
        assert any(name.startswith(kind) for name in names), f"no {kind} sample"
    assert any("privacy-review" in name for name in names)
    assert any("escalation" in name for name in names)


def test_ac_12_4_samples_have_reply_and_report_sections_and_notice():
    assert SAMPLES
    for sample in SAMPLES:
        text = sample.read_text(encoding="utf-8")
        assert "## Customer reply\n" in text, sample.name
        assert "## Staff report\n" in text, sample.name
        assert DECISION_NOTICE in section(text, "Staff report"), sample.name


def test_ac_12_4_samples_contain_no_personal_values():
    personal = known_personal_values()
    for sample in SAMPLES:
        text = sample.read_text(encoding="utf-8")
        assert find_pii(text) == [], sample.name
        assert [value for value in personal if value in text] == [], sample.name


def test_ac_12_4_scripted_privacy_sample_is_labeled():
    privacy = [sample for sample in SAMPLES if "privacy-review" in sample.stem]

    assert privacy
    for sample in privacy:
        assert "**Scripted run.**" in sample.read_text(encoding="utf-8")
