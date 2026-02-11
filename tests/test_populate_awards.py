"""Tests for scripts/populate_awards.py CLI argument parsing."""

from src.config import FISCAL_YEAR_INT
from src.paths import OUTPUTS_DIR


class TestParseArgsDefaults:
    """Test default argument values."""

    def test_parse_args_defaults(self):
        """Default values: no dry-run, no tribe filter, default report path and FY range."""
        from scripts.populate_awards import parse_args

        args = parse_args([])
        assert args.dry_run is False
        assert args.tribe is None
        assert args.report == str(OUTPUTS_DIR / "award_population_report.json")
        assert args.fy_start == FISCAL_YEAR_INT - 4
        assert args.fy_end == FISCAL_YEAR_INT


class TestParseArgsDryRun:
    """Test --dry-run flag."""

    def test_parse_args_dry_run(self):
        """--dry-run sets dry_run to True."""
        from scripts.populate_awards import parse_args

        args = parse_args(["--dry-run"])
        assert args.dry_run is True


class TestParseArgsTribe:
    """Test --tribe filter."""

    def test_parse_args_tribe(self):
        """--tribe sets the tribe ID for single-Tribe processing."""
        from scripts.populate_awards import parse_args

        args = parse_args(["--tribe", "epa_100000001"])
        assert args.tribe == "epa_100000001"


class TestParseArgsFYRange:
    """Test --fy-start and --fy-end."""

    def test_parse_args_fy_range(self):
        """Custom fiscal year range overrides defaults."""
        from scripts.populate_awards import parse_args

        args = parse_args(["--fy-start", "2023", "--fy-end", "2025"])
        assert args.fy_start == 2023
        assert args.fy_end == 2025


class TestParseArgsReport:
    """Test --report path."""

    def test_parse_args_custom_report(self):
        """Custom report path overrides default."""
        from scripts.populate_awards import parse_args

        args = parse_args(["--report", "custom/report.json"])
        assert args.report == "custom/report.json"


class TestParseArgsCombined:
    """Test combined arguments."""

    def test_parse_args_all_flags(self):
        """All flags can be combined."""
        from scripts.populate_awards import parse_args

        args = parse_args([
            "--dry-run",
            "--tribe", "epa_100000316",
            "--report", "outputs/test_report.json",
            "--fy-start", "2022",
            "--fy-end", "2024",
        ])
        assert args.dry_run is True
        assert args.tribe == "epa_100000316"
        assert args.report == "outputs/test_report.json"
        assert args.fy_start == 2022
        assert args.fy_end == 2024
