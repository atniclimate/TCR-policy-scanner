"""NRI expanded metrics extraction pipeline: FEMA NRI version-pinned builder.

Builds per-Tribe NRI expanded profiles for the vulnerability assessment
pipeline. Extracts metrics beyond what the original HazardProfileBuilder
captures:
  - SHA256 version pinning (XCUT-03) for reproducible builds
  - National percentile computation from RISK_SCORE rank (18.5-DEC-01)
  - EAL breakdown by consequence type (buildings, population, agriculture, pop equiv)
  - Community resilience score (RESL_SCORE)
  - Connecticut FIPS handling for legacy vs planning region codes

Follows the HazardProfileBuilder 9-step template from src/packets/hazards.py.

The NRI expanded profile feeds the hazard_exposure component (0.40 weight)
of the composite vulnerability score defined in DEC-04.

Usage:
    builder = NRIExpandedBuilder(config)
    count = builder.build_all_profiles()
    print(f"Built {count} NRI expanded profiles")
"""

import bisect
import contextlib
import csv
import hashlib
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.packets.hazards import NRI_HAZARD_CODES, _safe_float
from src.paths import (
    AIANNH_CROSSWALK_PATH,
    NRI_DIR,
    OUTPUTS_DIR,
    PROJECT_ROOT,
    TRIBAL_COUNTY_WEIGHTS_PATH,
    VULNERABILITY_PROFILES_DIR,
)
from src.schemas.vulnerability import NRIExpanded

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# -- Connecticut FIPS mapping (XCUT-03) --
# ---------------------------------------------------------------------------
# Connecticut transitioned from 8 counties to 9 planning regions in 2022.
# NRI data may use either legacy county FIPS (09001-09015) or new planning
# region FIPS (09110-09190). The crosswalk uses one format; the NRI CSV
# may use the other. We detect and remap to match.

CT_LEGACY_TO_PLANNING: dict[str, str] = {
    "09001": "09120",  # Fairfield -> Capitol
    "09003": "09160",  # Hartford -> South Central
    "09005": "09190",  # Litchfield -> Western
    "09007": "09130",  # Middlesex -> Lower Connecticut River Valley
    "09009": "09170",  # New Haven -> Southeastern
    "09011": "09140",  # New London -> Naugatuck Valley
    "09013": "09180",  # Tolland -> Upper Connecticut River Valley
    "09015": "09150",  # Windham -> Northwestern
}

CT_PLANNING_TO_LEGACY: dict[str, str] = {v: k for k, v in CT_LEGACY_TO_PLANNING.items()}

# Required NRI CSV headers for expanded metrics extraction
_REQUIRED_HEADERS: frozenset[str] = frozenset({
    "STCOFIPS",
    "RISK_SCORE",
    "RISK_RATNG",
    "EAL_VALT",
    "EAL_VALB",
    "EAL_VALP",
    "EAL_VALA",
    "EAL_VALPE",
    "SOVI_SCORE",
    "RESL_SCORE",
    "POPULATION",
    "BUILDVALUE",
})


# ---------------------------------------------------------------------------
# -- Public validation function --
# ---------------------------------------------------------------------------


def validate_nri_checksum(csv_path: Path, expected_sha256: str) -> bool:
    """Validate the SHA256 checksum of an NRI CSV file.

    Reads the file in 64KB chunks to compute the SHA256 hash without
    loading the entire file into memory.

    Args:
        csv_path: Path to the NRI CSV file.
        expected_sha256: Expected hex-encoded SHA256 digest.

    Returns:
        True if the computed SHA256 matches expected_sha256, False otherwise.
    """
    computed = _compute_sha256(csv_path)
    return computed == expected_sha256.lower()


def _compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file in 64KB chunks.

    Args:
        file_path: Path to the file to hash.

    Returns:
        Hex-encoded SHA256 digest string (lowercase).

    Raises:
        FileNotFoundError: If file_path does not exist.
        OSError: If file cannot be read.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(65536)  # 64KB chunks
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


def _resolve_path(raw_path: str) -> Path:
    """Resolve a path relative to project root if not absolute.

    Args:
        raw_path: File or directory path (absolute or relative).

    Returns:
        Resolved Path object.
    """
    p = Path(raw_path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


# ---------------------------------------------------------------------------
# -- NRIExpandedBuilder --
# ---------------------------------------------------------------------------


class NRIExpandedBuilder:
    """Builds per-Tribe NRI expanded profiles with version pinning.

    Reads the FEMA NRI county-level CSV, computes national risk percentiles,
    extracts EAL breakdowns and community resilience scores, and writes
    per-Tribe NRI expanded JSON files validated against the NRIExpanded
    Pydantic schema.

    Follows the 9-step HazardProfileBuilder template:
      1. __init__ with config
      2. _load_crosswalk
      3. _load_area_weights
      4. _load_nri_csv (with SHA256 version pinning)
      5. compute_national_percentiles
      6. _aggregate_tribe_nri
      7. build_all_profiles
      8. _atomic_write
      9. generate_coverage_report

    Attributes:
        nri_csv_path: Path to NRI_Table_Counties.csv.
        expected_sha256: Optional expected SHA256 for version pinning.
        output_dir: Directory for per-Tribe NRI expanded JSON files.
    """

    def __init__(self, config: dict) -> None:
        """Initialize the builder.

        Args:
            config: Application configuration dict. Reads paths from
                config["nri_expanded"][*], falling back to defaults.
        """
        nri_cfg = config.get("nri_expanded", {})

        raw = nri_cfg.get("nri_csv_path")
        self.nri_csv_path: Path = (
            _resolve_path(raw) if raw
            else NRI_DIR / "NRI_Table_Counties.csv"
        )

        self.expected_sha256: str | None = nri_cfg.get("expected_sha256")

        raw = nri_cfg.get("output_dir")
        self.output_dir: Path = (
            _resolve_path(raw) if raw
            else VULNERABILITY_PROFILES_DIR
        )

        # Step 2: Load crosswalk
        self._crosswalk: dict[str, str] = {}
        self._tribe_to_geoids: dict[str, list[str]] = {}
        self._load_crosswalk()

        # Step 3: Load area weights
        self._area_weights: dict[str, list[dict]] = self._load_area_weights()

        # NRI county data (populated by _load_nri_csv)
        self._county_data: dict[str, dict] = {}
        self._nri_sha256: str = ""
        self._nri_version: str = "NRI_v1.20"

        # National percentiles (populated by compute_national_percentiles)
        self._sorted_risk_scores: list[float] = []

    # -- Step 2: Load crosswalk --

    def _load_crosswalk(self) -> None:
        """Load and invert the AIANNH-to-tribe_id crosswalk.

        The crosswalk JSON has structure:
            {"mappings": {"GEOID": "tribe_id", ...}}

        One Tribe may span multiple AIANNH areas, so the reverse mapping
        is tribe_id -> list[GEOID].
        """
        try:
            with open(AIANNH_CROSSWALK_PATH, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.warning(
                "AIANNH crosswalk not found at %s -- "
                "all Tribes will get empty NRI expanded profiles",
                AIANNH_CROSSWALK_PATH,
            )
            return
        except json.JSONDecodeError as exc:
            logger.error(
                "Crosswalk at %s is invalid JSON: %s",
                AIANNH_CROSSWALK_PATH, exc,
            )
            return

        self._crosswalk = data.get("mappings", {})

        # Build reverse mapping: tribe_id -> [geoid, ...]
        for geoid, tribe_id in self._crosswalk.items():
            if tribe_id not in self._tribe_to_geoids:
                self._tribe_to_geoids[tribe_id] = []
            self._tribe_to_geoids[tribe_id].append(geoid)

        logger.info(
            "NRI expanded crosswalk: %d GEOIDs -> %d tribes",
            len(self._crosswalk),
            len(self._tribe_to_geoids),
        )

    # -- Step 3: Load area weights --

    def _load_area_weights(self) -> dict[str, list[dict]]:
        """Load pre-computed area-weighted AIANNH-to-county crosswalk.

        Returns:
            Dict mapping AIANNH GEOID -> list of
            {county_fips, weight, overlap_area_sqkm}.
            Empty dict if file not found.
        """
        if not TRIBAL_COUNTY_WEIGHTS_PATH.exists():
            logger.warning(
                "Area-weighted crosswalk not found at %s -- "
                "NRI expanded profiles will have no geographic data",
                TRIBAL_COUNTY_WEIGHTS_PATH,
            )
            return {}

        try:
            with open(TRIBAL_COUNTY_WEIGHTS_PATH, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error(
                "Failed to load area weights from %s: %s",
                TRIBAL_COUNTY_WEIGHTS_PATH, exc,
            )
            return {}

        crosswalk = data.get("crosswalk", {})
        logger.info(
            "NRI expanded area weights: %d AIANNH entities",
            len(crosswalk),
        )
        return crosswalk

    # -- Step 4: Load NRI CSV with version pinning (XCUT-03) --

    def _load_nri_csv(self) -> dict[str, dict]:
        """Parse the NRI county-level CSV with SHA256 version pinning.

        Computes SHA256 in 64KB chunks for reproducibility. If
        expected_sha256 is set, compares and logs WARNING on mismatch.
        Handles Connecticut FIPS remapping for legacy vs planning region.

        Returns:
            Dict keyed by STCOFIPS -> metrics dict.
            Empty dict if CSV not found.
        """
        if not self.nri_csv_path.exists():
            logger.warning(
                "NRI CSV not found at %s -- "
                "NRI expanded profiles will be unavailable",
                self.nri_csv_path,
            )
            return {}

        # SHA256 version pinning (XCUT-03)
        self._nri_sha256 = _compute_sha256(self.nri_csv_path)
        logger.info("NRI CSV SHA256: %s", self._nri_sha256)

        if self.expected_sha256:
            if self._nri_sha256 != self.expected_sha256.lower():
                logger.warning(
                    "NRI CSV SHA256 mismatch! Expected %s, got %s. "
                    "Data may have been updated since last pinned version.",
                    self.expected_sha256,
                    self._nri_sha256,
                )
            else:
                logger.info("NRI CSV SHA256 matches expected checksum")

        # Read CSV with BOM handling
        county_data: dict[str, dict] = {}

        with open(self.nri_csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = set(reader.fieldnames or [])

            # Validate required headers
            missing = _REQUIRED_HEADERS - headers
            if missing:
                logger.warning(
                    "NRI CSV missing required headers: %s. "
                    "Some expanded metrics may be unavailable.",
                    sorted(missing),
                )

            # Detect CT FIPS format in crosswalk to decide remapping direction
            crosswalk_fips = set()
            for entries in self._area_weights.values():
                for entry in entries:
                    fips = entry.get("county_fips", "")
                    if fips.startswith("09"):
                        crosswalk_fips.add(fips)

            crosswalk_uses_legacy = any(
                f in CT_LEGACY_TO_PLANNING for f in crosswalk_fips
            )
            crosswalk_uses_planning = any(
                f in CT_PLANNING_TO_LEGACY for f in crosswalk_fips
            )

            row_count = 0
            ct_remapped = 0

            for row in reader:
                fips = row.get("STCOFIPS", "").strip()
                fips = fips.zfill(5) if fips else fips
                if not fips:
                    continue

                # CT FIPS handling: remap to match crosswalk format
                original_fips = fips
                if fips.startswith("09"):
                    if crosswalk_uses_legacy and fips in CT_PLANNING_TO_LEGACY:
                        # NRI uses planning, crosswalk uses legacy -> remap to legacy
                        fips = CT_PLANNING_TO_LEGACY[fips]
                        ct_remapped += 1
                    elif crosswalk_uses_planning and fips in CT_LEGACY_TO_PLANNING:
                        # NRI uses legacy, crosswalk uses planning -> remap to planning
                        fips = CT_LEGACY_TO_PLANNING[fips]
                        ct_remapped += 1

                record: dict = {
                    "fips": fips,
                    "original_fips": original_fips,
                    "county": row.get("COUNTY", ""),
                    "state": row.get("STATE", ""),
                    # Composite risk
                    "risk_score": _safe_float(row.get("RISK_SCORE")),
                    "risk_rating": row.get("RISK_RATNG", "").strip(),
                    # EAL breakdown by consequence type
                    "eal_total": _safe_float(row.get("EAL_VALT")),
                    "eal_buildings": _safe_float(row.get("EAL_VALB")),
                    "eal_population": _safe_float(row.get("EAL_VALP")),
                    "eal_agriculture": _safe_float(row.get("EAL_VALA")),
                    "eal_population_equivalence": _safe_float(row.get("EAL_VALPE")),
                    # Social vulnerability and community resilience
                    "sovi_score": _safe_float(row.get("SOVI_SCORE")),
                    "resl_score": _safe_float(row.get("RESL_SCORE")),
                    # Demographics
                    "population": _safe_float(row.get("POPULATION")),
                    "building_value": _safe_float(row.get("BUILDVALUE")),
                    # Per-hazard EAL for top hazard ranking
                    "hazards": {},
                }

                for code in NRI_HAZARD_CODES:
                    record["hazards"][code] = {
                        "eal_total": _safe_float(row.get(f"{code}_EALT")),
                        "risk_score": _safe_float(row.get(f"{code}_RISKS")),
                    }

                county_data[fips] = record
                row_count += 1

            if ct_remapped > 0:
                logger.info(
                    "Remapped %d Connecticut FIPS codes to match crosswalk format",
                    ct_remapped,
                )

        logger.info("NRI expanded: loaded %d counties", row_count)
        self._county_data = county_data
        return county_data

    # -- Step 5: Compute national percentiles (18.5-DEC-01) --

    def compute_national_percentiles(self) -> None:
        """Compute national risk percentiles from RISK_SCORE ranking.

        RISK_NPCTL does not exist in NRI v1.20 (18.5-DEC-01). We compute
        percentile as rank / (N-1) * 100 using all counties with RISK_SCORE > 0.

        Uses bisect_left for efficient percentile lookup of arbitrary scores.

        Special cases:
        - Single county: percentile = 50.0
        - Zero score: percentile = 0.0
        """
        scores = [
            row["risk_score"]
            for row in self._county_data.values()
            if row["risk_score"] > 0
        ]

        if not scores:
            logger.warning("No counties with RISK_SCORE > 0 -- cannot compute percentiles")
            self._sorted_risk_scores = []
            return

        scores.sort()
        self._sorted_risk_scores = scores
        logger.info(
            "National percentile base: %d counties, range [%.2f, %.2f]",
            len(scores),
            scores[0],
            scores[-1],
        )

    def _get_risk_percentile(self, risk_score: float) -> float:
        """Look up the national percentile for a given risk score.

        Args:
            risk_score: Area-weighted risk score for a Tribe.

        Returns:
            Percentile in range [0.0, 100.0].
        """
        if risk_score <= 0:
            return 0.0

        n = len(self._sorted_risk_scores)
        if n == 0:
            return 0.0
        if n == 1:
            return 50.0

        rank = bisect.bisect_left(self._sorted_risk_scores, risk_score)
        percentile = (rank / (n - 1)) * 100.0
        return round(min(percentile, 100.0), 2)

    # -- Step 6: Aggregate tribe NRI --

    def _aggregate_tribe_nri(
        self,
        tribe_id: str,
        geoids: list[str],
    ) -> dict:
        """Area-weighted aggregation of NRI expanded metrics for one Tribe.

        Args:
            tribe_id: EPA tribe identifier.
            geoids: List of AIANNH GEOIDs for this Tribe.

        Returns:
            Dict with all NRI expanded fields ready for Pydantic validation.
        """
        if not self._county_data:
            return self._empty_profile(tribe_id, "NRI county data not loaded")

        if not geoids:
            return self._empty_profile(tribe_id, "No AIANNH GEOIDs in crosswalk")

        # Collect county weights from area-weighted crosswalk
        county_weights: dict[str, float] = {}
        total_possible_weight: float = 0.0

        for geoid in geoids:
            entries = self._area_weights.get(geoid, [])
            for entry in entries:
                fips = entry["county_fips"]
                weight = entry["weight"]
                county_weights[fips] = county_weights.get(fips, 0.0) + weight
                total_possible_weight += weight

        if not county_weights:
            return self._empty_profile(
                tribe_id, "No county weights from area crosswalk"
            )

        # Match to available county data
        matched = [
            (fips, self._county_data[fips], county_weights[fips])
            for fips in county_weights
            if fips in self._county_data
        ]

        if not matched:
            return self._empty_profile(
                tribe_id,
                f"Counties identified ({len(county_weights)}) but none in NRI data",
            )

        # Normalize weights to matched counties only
        matched_weight = sum(w for _, _, w in matched)
        if matched_weight == 0:
            # Equal weight fallback
            equal_w = 1.0 / len(matched)
            norm = [(fips, row, equal_w) for fips, row, _ in matched]
            coverage_pct = 0.0
        else:
            norm = [
                (fips, row, w / matched_weight)
                for fips, row, w in matched
            ]
            coverage_pct = (
                matched_weight / total_possible_weight
                if total_possible_weight > 0
                else 0.0
            )

        # Area-weighted aggregation of all expanded metrics
        risk_score = sum(row["risk_score"] * w for _, row, w in norm)
        eal_total = sum(row["eal_total"] * w for _, row, w in norm)
        eal_buildings = sum(row["eal_buildings"] * w for _, row, w in norm)
        eal_population = sum(row["eal_population"] * w for _, row, w in norm)
        eal_agriculture = sum(row["eal_agriculture"] * w for _, row, w in norm)
        eal_pop_equiv = sum(
            row["eal_population_equivalence"] * w for _, row, w in norm
        )
        sovi_score = sum(row["sovi_score"] * w for _, row, w in norm)
        resl_score = sum(row["resl_score"] * w for _, row, w in norm)

        # National percentile from computed ranking
        risk_percentile = self._get_risk_percentile(risk_score)

        # Top 5 hazards by EAL (area-weighted)
        hazard_eals: dict[str, float] = {}
        for code in NRI_HAZARD_CODES:
            hazard_eal = sum(
                row["hazards"].get(code, {}).get("eal_total", 0.0) * w
                for _, row, w in norm
            )
            if hazard_eal > 0:
                hazard_eals[code] = round(hazard_eal, 2)

        sorted_hazards = sorted(
            hazard_eals.items(), key=lambda x: x[1], reverse=True
        )
        top_hazards = [
            {
                "type": NRI_HAZARD_CODES[code],
                "code": code,
                "eal_total": eal,
            }
            for code, eal in sorted_hazards[:5]
        ]

        hazard_count = len(hazard_eals)

        return {
            "tribe_id": tribe_id,
            "risk_score": round(risk_score, 2),
            "risk_percentile": round(risk_percentile, 2),
            "eal_total": round(eal_total, 2),
            "eal_buildings": round(eal_buildings, 2),
            "eal_population": round(eal_population, 2),
            "eal_agriculture": round(eal_agriculture, 2),
            "eal_population_equivalence": round(eal_pop_equiv, 2),
            "community_resilience": round(resl_score, 2),
            "social_vulnerability_nri": round(sovi_score, 2),
            "hazard_count": hazard_count,
            "top_hazards": top_hazards,
            "coverage_pct": round(min(coverage_pct, 1.0), 4),
        }

    def _empty_profile(self, tribe_id: str, note: str) -> dict:
        """Return a minimal NRI expanded profile when no data is available.

        Args:
            tribe_id: EPA tribe identifier.
            note: Explanation of why data is unavailable.

        Returns:
            Dict with zero/empty values and a note field.
        """
        return {
            "tribe_id": tribe_id,
            "risk_score": 0.0,
            "risk_percentile": 0.0,
            "eal_total": 0.0,
            "eal_buildings": 0.0,
            "eal_population": 0.0,
            "eal_agriculture": 0.0,
            "eal_population_equivalence": 0.0,
            "community_resilience": 0.0,
            "social_vulnerability_nri": 0.0,
            "hazard_count": 0,
            "top_hazards": [],
            "coverage_pct": 0.0,
            "note": note,
        }

    # -- Step 7: Build all profiles --

    def build_all_profiles(self) -> int:
        """Build and cache NRI expanded profiles for all Tribes in crosswalk.

        Main orchestration method:
          1. Load NRI CSV with SHA256 checksum
          2. Compute national percentiles
          3. For each Tribe in crosswalk:
             a. Aggregate area-weighted NRI expanded metrics
             b. Validate against NRIExpanded Pydantic schema
             c. Write via atomic write
          4. Generate coverage report

        Single-writer-per-tribe_id assumption: this method writes one JSON
        file per tribe_id sequentially.

        Returns:
            Number of profile files written.
        """
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Step 4: Load NRI CSV
        self._load_nri_csv()
        if not self._county_data:
            logger.warning("No NRI county data -- skipping all profiles")
            return 0

        # Step 5: Compute national percentiles
        self.compute_national_percentiles()

        files_written = 0
        validation_errors = 0

        for tribe_id, geoids in self._tribe_to_geoids.items():
            # Path traversal guard
            safe_id = Path(tribe_id).name
            if safe_id != tribe_id or ".." in tribe_id:
                logger.warning("Skipping suspicious tribe_id: %r", tribe_id)
                continue

            # Step 6: Aggregate
            profile_data = self._aggregate_tribe_nri(tribe_id, geoids)

            # Remove note field before Pydantic validation (not in schema)
            note = profile_data.pop("note", None)

            # Validate against NRIExpanded schema
            try:
                validated = NRIExpanded(**profile_data)
            except Exception as exc:
                logger.warning(
                    "NRI expanded validation failed for %s: %s",
                    tribe_id, exc,
                )
                validation_errors += 1
                continue

            # Build output JSON
            output = validated.model_dump()
            output["nri_version"] = self._nri_version
            output["nri_sha256"] = self._nri_sha256
            output["generated_at"] = datetime.now(timezone.utc).isoformat()
            if note:
                output["note"] = note

            # Step 8: Atomic write
            output_path = self.output_dir / f"{tribe_id}_nri_expanded.json"
            self._atomic_write(output_path, output)
            files_written += 1

        logger.info(
            "NRI expanded build complete: %d files written, %d validation errors",
            files_written,
            validation_errors,
        )

        # Step 9: Coverage report
        self._generate_coverage_report(files_written, validation_errors)

        return files_written

    # -- Step 8: Atomic write --

    def _atomic_write(self, output_path: Path, data: dict) -> None:
        """Write JSON data atomically with path traversal guard.

        Uses tempfile.mkstemp + os.fdopen + os.replace pattern for
        crash safety. Cleans up temp file on error.

        Args:
            output_path: Target file path.
            data: Dict to serialize as JSON.

        Raises:
            ValueError: If output_path attempts path traversal.
        """
        # Path traversal guard
        safe_name = Path(output_path.name).name
        if safe_name != output_path.name or ".." in str(output_path):
            raise ValueError(
                f"Path traversal detected in output path: {output_path}"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=output_path.parent,
            suffix=".tmp",
            prefix=f"{output_path.stem}_",
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, output_path)
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise

    # -- Step 9: Coverage report --

    def _generate_coverage_report(
        self,
        files_written: int,
        validation_errors: int,
    ) -> None:
        """Generate NRI expanded coverage report.

        Args:
            files_written: Number of profile files successfully written.
            validation_errors: Number of Pydantic validation failures.
        """
        total_tribes = len(self._tribe_to_geoids)

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "nri_version": self._nri_version,
            "nri_sha256": self._nri_sha256,
            "summary": {
                "total_tribes_in_crosswalk": total_tribes,
                "profiles_written": files_written,
                "validation_errors": validation_errors,
                "coverage_pct": round(
                    files_written / max(total_tribes, 1) * 100, 1
                ),
                "counties_in_nri": len(self._county_data),
                "counties_in_percentile_base": len(self._sorted_risk_scores),
            },
        }

        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = OUTPUTS_DIR / "nri_expanded_coverage_report.json"

        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=OUTPUTS_DIR, suffix=".tmp", prefix="nri_exp_cov_"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, report_path)
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise

        logger.info("NRI expanded coverage report written to %s", report_path)
