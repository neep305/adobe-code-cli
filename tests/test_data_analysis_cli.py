"""Integration tests for analyze CLI commands."""

import json

from typer.testing import CliRunner

from adobe_experience.cli.analyze import analyze_app

runner = CliRunner()


def test_analyze_run_generates_artifacts(tmp_path) -> None:
    data_file = tmp_path / "customers.json"
    data_file.write_text(
        json.dumps(
            [
                {"customer_id": "c1", "email": "a@example.com", "country": "US"},
                {"customer_id": "c2", "email": "b@example.com", "country": "KR"},
            ]
        ),
        encoding="utf-8",
    )

    output_dir = tmp_path / "out"
    result = runner.invoke(
        analyze_app,
        [
            "run",
            "--intent",
            "analyze customer dataset and generate schema mapping",
            "--file",
            str(data_file),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    json_files = list(output_dir.glob("analysis_*.json"))
    md_files = list(output_dir.glob("analysis_*.md"))
    assert json_files, "Expected at least one JSON artifact"
    assert md_files, "Expected at least one markdown artifact"


def test_analyze_run_rejects_conflicting_inputs() -> None:
    result = runner.invoke(
        analyze_app,
        [
            "run",
            "--intent",
            "analyze data",
            "--file",
            "dummy.json",
            "--dataset-id",
            "abc123",
        ],
    )

    assert result.exit_code != 0
    assert "either --file or --dataset-id" in result.output
