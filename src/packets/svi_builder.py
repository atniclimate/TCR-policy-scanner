"""CDC/ATSDR SVI 2022 integration pipeline: Tribal Social Vulnerability Index builder.

Builds per-Tribe SVI profiles by:
  1. Parsing CDC SVI 2022 county-level CSV data
  2. Excluding Theme 3 (Racial & Ethnic Minority Status) per sovereignty decision (DEC-02)
  3. Computing custom 3-theme Tribal SVI composite = mean(Theme1, Theme2, Theme4)
  4. Aggregating to Tribal areas via existing area-weighted AIANNH crosswalk
  5. Validating against SVIProfile Pydantic schema
  6. Writing per-Tribe SVI profile JSON files (atomic writes)

Theme 3 exclusion rationale: The CDC SVI Theme 3 (Racial & Ethnic Minority Status)
applies colonial classification frameworks to Indigenous peoples. All federally
recognized Tribal Nations are by definition minority populations. Including Theme 3
would paradoxically penalize Tribal Nations for their identity rather than measuring
actual social vulnerability. This is a sovereignty-informed design decision.

Usage:
    builder = SVIProfileBuilder(config)
    count = builder.build_all_profiles()
    print(f"Built {count} SVI profiles")
"""

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.packets._geo_common import (
    atomic_write_json,
    atomic_write_text,
    load_aiannh_crosswalk,
    load_area_weights,
)
from src.packets.hazards import _safe_float
from src.paths import (
    AIANNH_CROSSWALK_PATH,
    OUTPUTS_DIR,
    SVI_COUNTY_PATH,
    SVI_DIR,
    TRIBAL_COUNTY_WEIGHTS_PATH,
    VULNERABILITY_PROFILES_DIR,
    resolve_path,
)
from src.schemas.vulnerability import DataGapType, SVIProfile, SVITheme

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# -- Module constants --
# ---------------------------------------------------------------------------

SVI_INCLUDED_THEMES: frozenset[str] = frozenset({"theme1", "theme2", "theme4"})
"""SVI themes included in the Tribal composite score.

Theme 1: Socioeconomic Status
Theme 2: Household Characteristics & Disability
Theme 4: Housing Type & Transportation
"""

SVI_EXCLUDED_THEMES: frozenset[str] = frozenset({"theme3"})
"""SVI themes excluded from the Tribal composite score.

Theme 3: Racial & Ethnic Minority Status -- excluded per DEC-02.
"""

SVI_SOURCE_YEAR: int = 2022
"""CDC SVI data release year for this pipeline."""

SVI_THEME_NAMES: dict[str, str] = {
    "theme1": "Socioeconomic Status",
    "theme2": "Household Characteristics & Disability",
    "theme4": "Housing Type & Transportation",
}
"""Human-readable names for included SVI themes."""


# ---------------------------------------------------------------------------
# -- Helper functions --
# ---------------------------------------------------------------------------


def _safe_svi_float(value, default: float = 0.0) -> float:
    """Convert a value to float, handling CDC -999 sentinel as missing data.

    The CDC SVI dataset uses -999 as a sentinel value for suppressed or
    unavailable data. This function converts -999 to the default value
    rather than treating it as a real numeric value.

    Args:
        value: The value to convert. May be str, None, int, float, or empty.
        default: Fallback value if conversion fails or sentinel detected.

    Returns:
        Float value or default. Returns default for -999, -999.0, and "-999".
    """
    result = _safe_float(value, default=default)
    if result == -999 or result == -999.0:
        return default
    return result


# ---------------------------------------------------------------------------
# -- SVIProfileBuilder --
# ---------------------------------------------------------------------------


class SVIProfileBuilder:
    """Builds per-Tribe SVI profiles from CDC SVI 2022 county-level data.

    Loads SVI county-level CSV data, bridges to Tribal areas via the
    AIANNH area-weighted crosswalk, computes custom 3-theme composite
    (excluding Theme 3), and writes per-Tribe JSON cache files.

    The builder follows the same 9-step pattern as HazardProfileBuilder:
      1. __init__ with config
      2. _load_crosswalk
      3. _load_area_weights
      4. _load_svi_csv (data ingest)
      5. _aggregate_tribe_svi (per-Tribe aggregation)
      6. (no USFS equivalent -- single data source)
      7. build_all_profiles (orchestration)
      8. _atomic_write
      9. generate_coverage_report

    Attributes:
        svi_csv_path: Path to SVI 2022 county CSV.
        output_dir: Path to output directory for per-Tribe SVI profile files.
        crosswalk_path: Path to aiannh_tribe_crosswalk.json.
    """

    def __init__(self, config: dict) -> None:
        """Initialize the SVI builder.

        Args:
            config: Application configuration dict. Reads paths from
                config["packets"]["svi"][*], falling back to defaults.
        """
        from src.packets.registry import TribalRegistry

        packets_cfg = config.get("packets", {})
        svi_cfg = packets_cfg.get("svi", {})

        raw = svi_cfg.get("svi_csv_path")
        self.svi_csv_path = resolve_path(raw) if raw else SVI_COUNTY_PATH

        raw = svi_cfg.get("output_dir")
        self.output_dir = resolve_path(raw) if raw else SVI_DIR / "profiles"

        raw = svi_cfg.get("crosswalk_path")
        self.crosswalk_path = resolve_path(raw) if raw else AIANNH_CROSSWALK_PATH

        # Load registry for tribe enumeration
        self._registry = TribalRegistry(config)

        # Load crosswalk: AIANNH GEOID -> tribe_id
        self._crosswalk, self._tribe_to_geoids = load_aiannh_crosswalk(
            self.crosswalk_path, label="SVI",
        )

        # Load pre-computed area-weighted AIANNH-to-county crosswalk
        self._area_weights = load_area_weights(
            TRIBAL_COUNTY_WEIGHTS_PATH, label="SVI",
        )

    # -- Step 4: Load SVI CSV --

    def _load_svi_csv(self) -> dict[str, dict]:
        """Parse the CDC SVI 2022 county-level CSV file.

        Opens with encoding="utf-8-sig" to handle BOM. Extracts per county:
        - RPL_THEME1 (Socioeconomic Status percentile)
        - RPL_THEME2 (Household Characteristics percentile)
        - RPL_THEME4 (Housing Type & Transportation percentile)
        - RPL_THEMES (overall SVI, stored for reference only)
        - E_TOTPOP (estimated total population)
        - F_THEME1, F_THEME2, F_THEME4 (flag counts per theme)

        Does NOT extract RPL_THEME3 (Racial & Ethnic Minority Status).

        FIPS column detection: tries STCNTY first, then FIPS.
        Zero-pads FIPS to 5 digits.

        Returns:
            Dict keyed by county FIPS (5-digit, zero-padded) -> SVI metrics dict.
            Empty dict if the file does not exist.
        """
        if not self.svi_csv_path.exists():
            logger.warning(
                "SVI county CSV not found at %s -- "
                "SVI data will be unavailable. "
                "Download from https://www.atsdr.cdc.gov/placeandhealth/svi/data_documentation_download.html",
                self.svi_csv_path,
            )
            return {}

        county_data: dict[str, dict] = {}
        logger.info("Loading SVI 2022 county data from %s", self.svi_csv_path)

        with open(self.svi_csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            headers_upper = {h.upper(): h for h in headers}

            # FIPS column: try STCNTY first, then FIPS
            fips_col = None
            for candidate in ["STCNTY", "FIPS"]:
                if candidate in headers_upper:
                    fips_col = headers_upper[candidate]
                    break

            if fips_col is None:
                logger.error(
                    "SVI CSV at %s has no STCNTY or FIPS column. "
                    "Headers: %s",
                    self.svi_csv_path,
                    headers,
                )
                return {}

            logger.info("SVI CSV using FIPS column: %s", fips_col)

            row_count = 0
            sentinel_count = 0
            for row in reader:
                fips = row.get(fips_col, "").strip()
                fips = fips.zfill(5) if fips else fips
                if not fips:
                    continue

                # Extract theme percentiles with -999 sentinel handling
                rpl_theme1 = _safe_svi_float(row.get("RPL_THEME1"))
                rpl_theme2 = _safe_svi_float(row.get("RPL_THEME2"))
                rpl_theme4 = _safe_svi_float(row.get("RPL_THEME4"))
                rpl_themes = _safe_svi_float(row.get("RPL_THEMES"))

                # Flag counts
                f_theme1 = int(_safe_svi_float(row.get("F_THEME1"), default=0.0))
                f_theme2 = int(_safe_svi_float(row.get("F_THEME2"), default=0.0))
                f_theme4 = int(_safe_svi_float(row.get("F_THEME4"), default=0.0))

                # Population
                e_totpop = _safe_svi_float(row.get("E_TOTPOP"), default=0.0)

                # Track sentinel occurrences for diagnostics
                raw_vals = [
                    row.get("RPL_THEME1", ""),
                    row.get("RPL_THEME2", ""),
                    row.get("RPL_THEME4", ""),
                ]
                for rv in raw_vals:
                    if str(rv).strip() == "-999":
                        sentinel_count += 1

                record: dict = {
                    "fips": fips,
                    "rpl_theme1": rpl_theme1,
                    "rpl_theme2": rpl_theme2,
                    "rpl_theme4": rpl_theme4,
                    "rpl_themes": rpl_themes,  # reference only, not used in composite
                    "e_totpop": e_totpop,
                    "f_theme1": f_theme1,
                    "f_theme2": f_theme2,
                    "f_theme4": f_theme4,
                }

                county_data[fips] = record
                row_count += 1

        logger.info(
            "Loaded SVI data for %d counties (%d sentinel -999 values replaced)",
            row_count,
            sentinel_count,
        )
        return county_data

    # -- Step 5: Aggregate Tribe SVI --

    def _aggregate_tribe_svi(
        self,
        tribe_id: str,
        tribe: dict,
        county_data: dict[str, dict],
    ) -> dict:
        """Aggregate SVI data for a single Tribe using area-weighted averaging.

        Resolution chain:
          1. tribe_id -> AIANNH GEOIDs (from crosswalk)
          2. AIANNH GEOIDs -> county FIPS + area weights (from area crosswalk)
          3. Fallback: equal weights for matched counties

        Aggregation:
          - Skip counties where ALL 3 included themes are 0.0
          - Compute weighted average per theme
          - Composite = mean(weighted_theme1, weighted_theme2, weighted_theme4)
          - NEVER uses RPL_THEMES (which includes Theme 3)
          - Coverage_pct = matched counties / total crosswalk counties
          - Data gap detection for missing/partial data

        Args:
            tribe_id: EPA tribe identifier.
            tribe: Tribe dict from registry.
            county_data: Full SVI county data dict keyed by FIPS.

        Returns:
            Dict with SVI profile data including themes, composite, coverage,
            and data gaps. Returns empty/gap profile if no data matched.
        """
        if not county_data:
            return self._empty_svi_result("SVI county data not loaded")

        # Step 1: Find AIANNH GEOIDs for this Tribe
        geoids = self._tribe_to_geoids.get(tribe_id, [])

        # Step 2: Collect county weights from area-weighted crosswalk
        county_weights: dict[str, float] = {}  # fips -> weight
        total_crosswalk_counties = 0

        if geoids and self._area_weights:
            for geoid in geoids:
                entries = self._area_weights.get(geoid, [])
                for entry in entries:
                    fips = entry["county_fips"]
                    weight = entry["weight"]
                    # If same county appears via multiple GEOIDs, sum the weights
                    county_weights[fips] = county_weights.get(fips, 0.0) + weight
                    total_crosswalk_counties += 1

        if not county_weights:
            return self._empty_svi_result(
                "No county crosswalk entries found for this Tribe"
            )

        # Step 3: Collect matching county SVI records
        matched_records: list[dict] = []
        for fips in county_weights:
            if fips in county_data:
                record = county_data[fips]
                # Skip counties where ALL 3 included themes are 0.0
                if (record["rpl_theme1"] == 0.0
                        and record["rpl_theme2"] == 0.0
                        and record["rpl_theme4"] == 0.0):
                    continue
                matched_records.append(record)

        if not matched_records:
            return self._empty_svi_result(
                f"Counties identified ({len(county_weights)}) but none had non-zero SVI theme data"
            )

        # Step 4: Normalize weights to matched counties only
        total_w = sum(
            county_weights.get(r["fips"], 0.0) for r in matched_records
        )
        if total_w == 0:
            # Equal weight fallback
            total_w = len(matched_records)
            norm_weights = {r["fips"]: 1.0 / total_w for r in matched_records}
        else:
            norm_weights = {
                r["fips"]: county_weights.get(r["fips"], 0.0) / total_w
                for r in matched_records
            }

        # Step 5: Area-weighted theme averages
        weighted_theme1 = round(
            sum(r["rpl_theme1"] * norm_weights[r["fips"]] for r in matched_records), 4
        )
        weighted_theme2 = round(
            sum(r["rpl_theme2"] * norm_weights[r["fips"]] for r in matched_records), 4
        )
        weighted_theme4 = round(
            sum(r["rpl_theme4"] * norm_weights[r["fips"]] for r in matched_records), 4
        )

        # Weighted flag counts (rounded to nearest int)
        weighted_f1 = round(
            sum(r["f_theme1"] * norm_weights[r["fips"]] for r in matched_records)
        )
        weighted_f2 = round(
            sum(r["f_theme2"] * norm_weights[r["fips"]] for r in matched_records)
        )
        weighted_f4 = round(
            sum(r["f_theme4"] * norm_weights[r["fips"]] for r in matched_records)
        )

        # Step 6: Custom 3-theme composite = mean(theme1, theme2, theme4)
        # NEVER use RPL_THEMES (which includes Theme 3)
        composite = round(
            (weighted_theme1 + weighted_theme2 + weighted_theme4) / 3.0, 4
        )

        # Step 7: Coverage percentage (area-weight-based, matching NRI builder)
        total_possible_weight = sum(county_weights.values())
        matched_weight = sum(
            county_weights.get(r["fips"], 0.0) for r in matched_records
        )
        coverage_pct = round(
            matched_weight / total_possible_weight
            if total_possible_weight > 0
            else 0.0,
            4,
        )

        # Step 8: Data gap detection
        data_gaps: list[str] = []
        if coverage_pct < 0.5:
            data_gaps.append(DataGapType.MISSING_SVI)

        # Check for Alaska partial coverage
        tribe_states = tribe.get("states", [])
        if "AK" in tribe_states and coverage_pct < 1.0:
            data_gaps.append(DataGapType.ALASKA_PARTIAL)

        return {
            "themes": {
                "theme1": {
                    "percentile": weighted_theme1,
                    "flag_count": weighted_f1,
                    "name": SVI_THEME_NAMES["theme1"],
                },
                "theme2": {
                    "percentile": weighted_theme2,
                    "flag_count": weighted_f2,
                    "name": SVI_THEME_NAMES["theme2"],
                },
                "theme4": {
                    "percentile": weighted_theme4,
                    "flag_count": weighted_f4,
                    "name": SVI_THEME_NAMES["theme4"],
                },
            },
            "composite": composite,
            "coverage_pct": coverage_pct,
            "counties_matched": len(matched_records),
            "counties_in_crosswalk": len(county_weights),
            "data_gaps": data_gaps,
        }

    def _empty_svi_result(self, note: str) -> dict:
        """Return a minimal SVI result when no data is available.

        Args:
            note: Explanation of why data is unavailable.

        Returns:
            Dict with zero values and MISSING_SVI data gap.
        """
        return {
            "themes": {
                "theme1": {
                    "percentile": 0.0,
                    "flag_count": 0,
                    "name": SVI_THEME_NAMES["theme1"],
                },
                "theme2": {
                    "percentile": 0.0,
                    "flag_count": 0,
                    "name": SVI_THEME_NAMES["theme2"],
                },
                "theme4": {
                    "percentile": 0.0,
                    "flag_count": 0,
                    "name": SVI_THEME_NAMES["theme4"],
                },
            },
            "composite": 0.0,
            "coverage_pct": 0.0,
            "counties_matched": 0,
            "counties_in_crosswalk": 0,
            "data_gaps": [DataGapType.MISSING_SVI],
            "note": note,
        }

    # -- Step 7: Build all profiles --

    def build_all_profiles(self) -> int:
        """Build and cache SVI profiles for all Tribes.

        Main orchestration method:
          1. Load SVI county data from CSV
          2. For each Tribe:
             a. Aggregate SVI themes (area-weighted)
             b. Compute custom 3-theme composite
             c. Validate against SVIProfile Pydantic model
             d. Write JSON cache file (atomic)
          3. Generate coverage report

        Single-writer-per-tribe_id assumption: this method writes one JSON
        file per tribe_id sequentially.

        Returns:
            Number of profile files written.
        """
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load SVI county data
        county_data = self._load_svi_csv()

        all_tribes = self._registry.get_all()
        logger.info(
            "Building SVI profiles for %d Tribes (SVI counties: %d)",
            len(all_tribes),
            len(county_data),
        )

        files_written = 0
        matched_count = 0
        validation_errors = 0
        unmatched_tribes: list[dict] = []

        # Per-state tracking for coverage report
        state_stats: dict[str, dict] = {}

        for tribe in all_tribes:
            tribe_id = Path(tribe["tribe_id"]).name
            if tribe_id != tribe["tribe_id"] or ".." in tribe_id:
                logger.warning("Skipping suspicious tribe_id: %r", tribe["tribe_id"])
                continue

            tribe_states = tribe.get("states", [])

            # Initialize per-state tracking
            for st in tribe_states:
                if st not in state_stats:
                    state_stats[st] = {
                        "total": 0,
                        "matched": 0,
                        "unmatched": 0,
                    }
                state_stats[st]["total"] += 1

            # Aggregate SVI for this Tribe
            svi_result = self._aggregate_tribe_svi(
                tribe_id, tribe, county_data,
            )

            has_data = svi_result.get("counties_matched", 0) > 0
            if has_data:
                matched_count += 1
                for st in tribe_states:
                    if st in state_stats:
                        state_stats[st]["matched"] += 1
            else:
                unmatched_tribes.append({
                    "name": tribe["name"],
                    "tribe_id": tribe_id,
                    "states": tribe_states,
                })
                for st in tribe_states:
                    if st in state_stats:
                        state_stats[st]["unmatched"] += 1

            # Build SVITheme list for Pydantic validation
            themes_data = svi_result["themes"]
            svi_themes: list[SVITheme] = []
            for theme_id in sorted(SVI_INCLUDED_THEMES):
                theme_info = themes_data.get(theme_id, {})
                svi_themes.append(SVITheme(
                    theme_id=theme_id,
                    name=theme_info.get("name", SVI_THEME_NAMES.get(theme_id, theme_id)),
                    percentile=theme_info.get("percentile", 0.0),
                    flag_count=theme_info.get("flag_count", 0),
                ))

            # Validate against SVIProfile Pydantic schema
            try:
                svi_profile = SVIProfile(
                    tribe_id=tribe_id,
                    themes=svi_themes,
                    composite=svi_result["composite"],
                    coverage_pct=svi_result["coverage_pct"],
                    source_year=SVI_SOURCE_YEAR,
                    data_gaps=svi_result.get("data_gaps", []),
                )
            except Exception as exc:
                logger.warning(
                    "SVI validation failed for %s: %s",
                    tribe_id, exc,
                )
                validation_errors += 1
                continue

            # Build output dict
            profile_dict = {
                "tribe_id": tribe_id,
                "tribe_name": tribe["name"],
                "svi": svi_profile.model_dump(),
                "counties_matched": svi_result["counties_matched"],
                "counties_in_crosswalk": svi_result["counties_in_crosswalk"],
                "source_year": SVI_SOURCE_YEAR,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            if "note" in svi_result:
                profile_dict["note"] = svi_result["note"]

            # Atomic write
            cache_file = self.output_dir / f"{tribe_id}.json"
            atomic_write_json(cache_file, profile_dict)
            files_written += 1

        # Log summary
        logger.info(
            "SVI profile build complete: %d files written, "
            "%d with SVI data, %d without SVI data, %d validation errors",
            files_written,
            matched_count,
            len(unmatched_tribes),
            validation_errors,
        )

        if unmatched_tribes:
            names = [t["name"] for t in unmatched_tribes]
            logger.warning(
                "%d Tribes have no SVI county data "
                "(no area-weighted crosswalk match): %s%s",
                len(names),
                ", ".join(names[:10]),
                f"... and {len(names) - 10} more"
                if len(names) > 10 else "",
            )

        # Generate coverage report
        coverage_data = {
            "total_profiles": files_written,
            "matched": matched_count,
            "unmatched_count": len(unmatched_tribes),
            "unmatched_tribes": unmatched_tribes,
            "state_stats": state_stats,
        }
        self._generate_coverage_report(coverage_data)

        return files_written

    # -- Step 9: Coverage report --

    def _generate_coverage_report(self, coverage_data: dict) -> None:
        """Generate SVI coverage report in JSON and Markdown formats.

        Writes two files to the outputs directory:
          - svi_coverage_report.json (machine-readable)
          - svi_coverage_report.md (human-readable with tables)

        Args:
            coverage_data: Dict with tracking data accumulated during
                build_all_profiles().
        """
        total = coverage_data["total_profiles"]
        matched = coverage_data["matched"]
        unmatched_count = coverage_data["unmatched_count"]
        unmatched_tribes = coverage_data["unmatched_tribes"]
        state_stats = coverage_data["state_stats"]

        # Build JSON report
        report_json = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": f"CDC/ATSDR SVI {SVI_SOURCE_YEAR}",
            "themes_included": sorted(SVI_INCLUDED_THEMES),
            "themes_excluded": sorted(SVI_EXCLUDED_THEMES),
            "summary": {
                "total_profiles": total,
                "matched": matched,
                "unmatched": unmatched_count,
                "matched_pct": round(matched / max(total, 1) * 100, 1),
            },
            "unmatched_tribes": [
                {"name": t["name"], "tribe_id": t["tribe_id"], "states": t["states"]}
                for t in unmatched_tribes
            ],
            "per_state": {
                st: {
                    "total": stats["total"],
                    "matched": stats["matched"],
                    "unmatched": stats["unmatched"],
                }
                for st, stats in sorted(state_stats.items())
            },
        }

        json_path = OUTPUTS_DIR / "svi_coverage_report.json"
        atomic_write_json(json_path, report_json)
        logger.info("SVI coverage report (JSON) written to %s", json_path)

        # Build Markdown report
        md_lines = [
            "# SVI Coverage Report",
            "",
            f"Generated: {report_json['generated_at']}",
            f"Source: CDC/ATSDR SVI {SVI_SOURCE_YEAR}",
            f"Themes included: {', '.join(sorted(SVI_INCLUDED_THEMES))}",
            f"Themes excluded: {', '.join(sorted(SVI_EXCLUDED_THEMES))} (DEC-02)",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total profiles | {total} |",
            f"| SVI matched | {matched} ({report_json['summary']['matched_pct']}%) |",
            f"| Unmatched | {unmatched_count} |",
            "",
            "## Per-State Breakdown",
            "",
            "| State | Total Tribes | SVI Matched | Unmatched |",
            "|-------|-------------|-------------|-----------|",
        ]

        for st in sorted(state_stats.keys()):
            stats = state_stats[st]
            md_lines.append(
                f"| {st} | {stats['total']} | {stats['matched']} "
                f"| {stats['unmatched']} |"
            )

        md_lines.extend([
            "",
            "## Tribes Without SVI Data",
            "",
        ])

        if unmatched_tribes:
            for t in unmatched_tribes:
                states_str = ", ".join(t["states"]) if t["states"] else "N/A"
                md_lines.append(f"- {t['name']} ({t['tribe_id']}) -- {states_str}")
        else:
            md_lines.append("None -- all Tribes have SVI data.")

        md_lines.append("")  # trailing newline

        md_path = OUTPUTS_DIR / "svi_coverage_report.md"
        atomic_write_text(md_path, "\n".join(md_lines))
        logger.info("SVI coverage report (Markdown) written to %s", md_path)
