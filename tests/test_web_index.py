"""Tests for scripts/build_web_index.py -- web index builder.

Tests cover the updated 4-document-type format:
  - Per-Tribe documents dict (internal_strategy + congressional_overview)
  - Regions section with Doc C/D
  - Metadata section with per-type doc counts
  - Backward compatibility with flat packet directory
  - Alias embedding and per-Tribe timestamps
"""

import json
import time
from pathlib import Path


def _write_json(path: Path, data) -> None:
    """Write JSON data to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _mock_registry(count: int = 3) -> list[dict]:
    """Create a mock Tribal registry with count entries.

    Uses tribe_id as the primary key, matching actual tribal_registry.json.
    """
    return [
        {
            "tribe_id": f"epa_{i:09d}",
            "name": f"Test Tribe {i}",
            "states": ["WA"] if i % 2 == 0 else ["OR", "WA"],
            "ecoregion": "Pacific Northwest",
        }
        for i in range(1, count + 1)
    ]


def _mock_regional_config() -> dict:
    """Create a mock regional config matching real structure."""
    return {
        "version": "1.0",
        "regions": {
            "pnw": {
                "name": "Pacific Northwest / Columbia River Basin",
                "short_name": "Pacific Northwest",
                "states": ["WA", "OR", "ID", "MT"],
            },
            "alaska": {
                "name": "Alaska",
                "short_name": "Alaska",
                "states": ["AK"],
            },
        },
    }


class TestBuildIndex:
    """Tests for build_index() function."""

    def test_produces_valid_json(self, tmp_path):
        """build_index() produces valid JSON with required schema fields."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry())
        packets_dir = tmp_path / "packets"
        packets_dir.mkdir()
        output_path = tmp_path / "tribes.json"

        result = build_index(registry_path, packets_dir, output_path)

        assert "generated_at" in result
        assert "total_tribes" in result
        assert "tribes" in result
        assert "regions" in result
        assert "metadata" in result
        assert isinstance(result["tribes"], list)
        assert isinstance(result["regions"], list)

        # Verify file was written and matches returned dict
        assert output_path.exists()
        with open(output_path, "r", encoding="utf-8") as f:
            written = json.load(f)
        assert written == result

    def test_all_registry_tribes_included(self, tmp_path):
        """All Tribes from registry appear in output."""
        from scripts.build_web_index import build_index

        registry = _mock_registry(5)
        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, registry)
        packets_dir = tmp_path / "packets"
        packets_dir.mkdir()
        output_path = tmp_path / "tribes.json"

        result = build_index(registry_path, packets_dir, output_path)

        assert result["total_tribes"] == 5
        names = {t["name"] for t in result["tribes"]}
        for tribe in registry:
            assert tribe["name"] in names

    def test_documents_dict_per_tribe(self, tmp_path):
        """Each Tribe entry has a documents dict with doc-type keys."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry(3))
        packets_dir = tmp_path / "packets"

        # Create internal + congressional subdirectories
        internal_dir = packets_dir / "internal"
        internal_dir.mkdir(parents=True)
        congressional_dir = packets_dir / "congressional"
        congressional_dir.mkdir(parents=True)

        # Tribe 1 has both docs
        (internal_dir / "epa_000000001.docx").write_bytes(b"PK mock")
        (congressional_dir / "epa_000000001.docx").write_bytes(b"PK mock")
        # Tribe 2 has only congressional
        (congressional_dir / "epa_000000002.docx").write_bytes(b"PK mock")

        output_path = tmp_path / "tribes.json"
        result = build_index(registry_path, packets_dir, output_path)

        tribe_map = {t["id"]: t for t in result["tribes"]}

        # Tribe 1: both documents
        t1 = tribe_map["epa_000000001"]
        assert "internal_strategy" in t1["documents"]
        assert "congressional_overview" in t1["documents"]
        assert t1["has_complete_data"] is True

        # Tribe 2: congressional only
        t2 = tribe_map["epa_000000002"]
        assert "internal_strategy" not in t2["documents"]
        assert "congressional_overview" in t2["documents"]
        assert t2["has_complete_data"] is False

        # Tribe 3: no documents
        t3 = tribe_map["epa_000000003"]
        assert t3["documents"] == {}
        assert t3["has_complete_data"] is False

    def test_has_complete_data_only_when_both_docs(self, tmp_path):
        """has_complete_data is True only when both internal + congressional exist."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry(2))
        packets_dir = tmp_path / "packets"

        internal_dir = packets_dir / "internal"
        internal_dir.mkdir(parents=True)
        congressional_dir = packets_dir / "congressional"
        congressional_dir.mkdir(parents=True)

        # Only internal for tribe 1
        (internal_dir / "epa_000000001.docx").write_bytes(b"PK mock")

        output_path = tmp_path / "tribes.json"
        result = build_index(registry_path, packets_dir, output_path)

        tribe_map = {t["id"]: t for t in result["tribes"]}
        assert tribe_map["epa_000000001"]["has_complete_data"] is False
        assert tribe_map["epa_000000002"]["has_complete_data"] is False

    def test_metadata_section_with_doc_counts(self, tmp_path):
        """Metadata section includes accurate per-type doc counts."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry(3))
        packets_dir = tmp_path / "packets"

        internal_dir = packets_dir / "internal"
        internal_dir.mkdir(parents=True)
        congressional_dir = packets_dir / "congressional"
        congressional_dir.mkdir(parents=True)

        # 2 internal, 3 congressional
        (internal_dir / "epa_000000001.docx").write_bytes(b"PK mock")
        (internal_dir / "epa_000000002.docx").write_bytes(b"PK mock")
        (congressional_dir / "epa_000000001.docx").write_bytes(b"PK mock")
        (congressional_dir / "epa_000000002.docx").write_bytes(b"PK mock")
        (congressional_dir / "epa_000000003.docx").write_bytes(b"PK mock")

        output_path = tmp_path / "tribes.json"
        result = build_index(registry_path, packets_dir, output_path)

        meta = result["metadata"]
        assert meta["doc_a_count"] == 2
        assert meta["doc_b_count"] == 3
        assert meta["doc_c_count"] == 0
        assert meta["doc_d_count"] == 0
        assert meta["total_tribes"] == 3

    def test_regions_section_from_regional_files(self, tmp_path):
        """Regions section built from regional subdirectory + config."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry(1))
        packets_dir = tmp_path / "packets"

        # Create regional directories with files
        reg_internal = packets_dir / "regional" / "internal"
        reg_internal.mkdir(parents=True)
        reg_congressional = packets_dir / "regional" / "congressional"
        reg_congressional.mkdir(parents=True)

        (reg_internal / "pnw.docx").write_bytes(b"PK mock")
        (reg_congressional / "pnw.docx").write_bytes(b"PK mock")
        (reg_congressional / "alaska.docx").write_bytes(b"PK mock")

        # Write regional config
        config_path = tmp_path / "regional_config.json"
        _write_json(config_path, _mock_regional_config())

        output_path = tmp_path / "tribes.json"
        result = build_index(
            registry_path, packets_dir, output_path, config_path
        )

        regions = result["regions"]
        assert len(regions) == 2  # pnw + alaska (from config + files)

        region_map = {r["region_id"]: r for r in regions}

        # pnw has both docs
        pnw = region_map["pnw"]
        assert pnw["region_name"] == "Pacific Northwest / Columbia River Basin"
        assert "internal_strategy" in pnw["documents"]
        assert "congressional_overview" in pnw["documents"]

        # alaska has congressional only
        ak = region_map["alaska"]
        assert ak["region_name"] == "Alaska"
        assert "internal_strategy" not in ak["documents"]
        assert "congressional_overview" in ak["documents"]

        # Metadata counts
        meta = result["metadata"]
        assert meta["doc_c_count"] == 1  # pnw internal
        assert meta["doc_d_count"] == 2  # pnw + alaska congressional

    def test_regions_empty_without_files(self, tmp_path):
        """Regions section is empty when no regional files exist."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry(1))
        packets_dir = tmp_path / "packets"
        packets_dir.mkdir()
        output_path = tmp_path / "tribes.json"

        result = build_index(registry_path, packets_dir, output_path)

        assert result["regions"] == []
        assert result["metadata"]["doc_c_count"] == 0
        assert result["metadata"]["doc_d_count"] == 0

    def test_backward_compat_flat_directory(self, tmp_path):
        """Flat packets directory (pre-multi-doc) still works."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry(2))
        packets_dir = tmp_path / "packets"
        packets_dir.mkdir()

        # Flat directory files (old layout)
        (packets_dir / "epa_000000001.docx").write_bytes(b"PK mock")

        output_path = tmp_path / "tribes.json"
        result = build_index(registry_path, packets_dir, output_path)

        tribe_map = {t["id"]: t for t in result["tribes"]}
        t1 = tribe_map["epa_000000001"]
        assert "congressional_overview" in t1["documents"]
        assert t1["documents"]["congressional_overview"] == "epa_000000001.docx"

    def test_missing_packets_dir_handled(self, tmp_path):
        """build_index() handles missing packets directory gracefully."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry(2))
        packets_dir = tmp_path / "nonexistent_packets"
        output_path = tmp_path / "tribes.json"

        result = build_index(registry_path, packets_dir, output_path)

        assert result["metadata"]["doc_a_count"] == 0
        assert result["metadata"]["doc_b_count"] == 0
        assert result["total_tribes"] == 2

    def test_registry_dict_format(self, tmp_path):
        """build_index() handles registry wrapped in {"tribes": [...]} format."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        registry_data = {
            "metadata": {"total_tribes": 3},
            "tribes": _mock_registry(3),
        }
        _write_json(registry_path, registry_data)
        packets_dir = tmp_path / "packets"
        packets_dir.mkdir()
        output_path = tmp_path / "tribes.json"

        result = build_index(registry_path, packets_dir, output_path)

        assert result["total_tribes"] == 3
        # Verify tribe_id correctly extracted
        ids = {t["id"] for t in result["tribes"]}
        assert "epa_000000001" in ids

    def test_document_paths_use_subdirectory_prefix(self, tmp_path):
        """Document paths in tribes.json include subdirectory prefix."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry(1))
        packets_dir = tmp_path / "packets"

        internal_dir = packets_dir / "internal"
        internal_dir.mkdir(parents=True)
        congressional_dir = packets_dir / "congressional"
        congressional_dir.mkdir(parents=True)

        (internal_dir / "epa_000000001.docx").write_bytes(b"PK mock")
        (congressional_dir / "epa_000000001.docx").write_bytes(b"PK mock")

        output_path = tmp_path / "tribes.json"
        result = build_index(registry_path, packets_dir, output_path)

        docs = result["tribes"][0]["documents"]
        assert docs["internal_strategy"] == "internal/epa_000000001.docx"
        assert docs["congressional_overview"] == "congressional/epa_000000001.docx"

    def test_regional_document_paths_correct(self, tmp_path):
        """Regional document paths include regional/ prefix."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry(1))
        packets_dir = tmp_path / "packets"

        reg_internal = packets_dir / "regional" / "internal"
        reg_internal.mkdir(parents=True)
        reg_congressional = packets_dir / "regional" / "congressional"
        reg_congressional.mkdir(parents=True)

        (reg_internal / "pnw.docx").write_bytes(b"PK mock")
        (reg_congressional / "pnw.docx").write_bytes(b"PK mock")

        output_path = tmp_path / "tribes.json"
        result = build_index(registry_path, packets_dir, output_path)

        pnw = result["regions"][0]
        assert pnw["documents"]["internal_strategy"] == "regional/internal/pnw.docx"
        assert pnw["documents"]["congressional_overview"] == "regional/congressional/pnw.docx"


def _mock_aliases(tribe_ids: list[str] | None = None) -> dict:
    """Create a mock aliases file with housing variants for filtering tests."""
    if tribe_ids is None:
        tribe_ids = ["epa_000000001"]
    aliases = {}
    for tid in tribe_ids:
        aliases[f"{tid} short name"] = tid
        aliases[f"{tid} longer alternate name"] = tid
        aliases[f"{tid} medium name here"] = tid
        aliases[f"{tid} housing authority"] = tid  # Should be filtered
        aliases[f"{tid} housing program"] = tid  # Should be filtered
    return {"aliases": aliases}


class TestAliasEmbedding:
    """Tests for _load_filtered_aliases and alias embedding in tribes.json."""

    def test_aliases_embedded_in_tribe_entries(self, tmp_path):
        """Each Tribe entry contains an aliases list."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry(2))
        aliases_path = tmp_path / "aliases.json"
        _write_json(aliases_path, _mock_aliases(["epa_000000001"]))
        packets_dir = tmp_path / "packets"
        packets_dir.mkdir()
        output_path = tmp_path / "tribes.json"

        result = build_index(
            registry_path, packets_dir, output_path, aliases_path=aliases_path
        )

        tribe_map = {t["id"]: t for t in result["tribes"]}

        # Tribe 1 has aliases
        t1 = tribe_map["epa_000000001"]
        assert isinstance(t1["aliases"], list)
        assert len(t1["aliases"]) > 0

        # Tribe 2 has empty aliases (no alias data for it)
        t2 = tribe_map["epa_000000002"]
        assert t2["aliases"] == []

    def test_housing_aliases_filtered_out(self, tmp_path):
        """Aliases containing 'housing' are excluded."""
        from scripts.build_web_index import _load_filtered_aliases

        aliases_path = tmp_path / "aliases.json"
        _write_json(aliases_path, _mock_aliases(["epa_000000001"]))

        result = _load_filtered_aliases(aliases_path)
        aliases = result.get("epa_000000001", [])

        for alias in aliases:
            assert "housing" not in alias.lower()
        # 5 total aliases minus 2 housing = 3 remaining
        assert len(aliases) == 3

    def test_aliases_sorted_by_length_shortest_first(self, tmp_path):
        """Aliases are sorted by string length, shortest first."""
        from scripts.build_web_index import _load_filtered_aliases

        aliases_path = tmp_path / "aliases.json"
        _write_json(aliases_path, _mock_aliases(["epa_000000001"]))

        result = _load_filtered_aliases(aliases_path)
        aliases = result["epa_000000001"]

        lengths = [len(a) for a in aliases]
        assert lengths == sorted(lengths)

    def test_aliases_capped_at_max_per_tribe(self, tmp_path):
        """No more than max_per_tribe aliases per Tribe."""
        from scripts.build_web_index import _load_filtered_aliases

        # Create 20 non-housing aliases
        tid = "epa_000000001"
        raw = {f"alias variant {i:03d}": tid for i in range(20)}
        aliases_path = tmp_path / "aliases.json"
        _write_json(aliases_path, {"aliases": raw})

        result = _load_filtered_aliases(aliases_path, max_per_tribe=10)
        assert len(result[tid]) == 10

        result5 = _load_filtered_aliases(aliases_path, max_per_tribe=5)
        assert len(result5[tid]) == 5

    def test_missing_aliases_file_returns_empty(self, tmp_path):
        """Missing aliases file produces empty dict, no crash."""
        from scripts.build_web_index import _load_filtered_aliases

        result = _load_filtered_aliases(tmp_path / "nonexistent.json")
        assert result == {}

    def test_oversized_aliases_file_returns_empty(self, tmp_path):
        """Aliases file exceeding 10MB returns empty dict."""
        from scripts.build_web_index import MAX_ALIASES_SIZE, _load_filtered_aliases

        # Create a file just over the limit
        aliases_path = tmp_path / "huge_aliases.json"
        aliases_path.write_bytes(b"x" * (MAX_ALIASES_SIZE + 1))

        result = _load_filtered_aliases(aliases_path)
        assert result == {}

    def test_missing_aliases_file_graceful_in_build_index(self, tmp_path):
        """build_index with missing aliases file still produces valid output."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry(2))
        packets_dir = tmp_path / "packets"
        packets_dir.mkdir()
        output_path = tmp_path / "tribes.json"

        result = build_index(
            registry_path,
            packets_dir,
            output_path,
            aliases_path=tmp_path / "nonexistent.json",
        )

        # All tribes should have empty aliases
        for tribe in result["tribes"]:
            assert tribe["aliases"] == []


class TestPerTribeTimestamp:
    """Tests for per-Tribe generated_at timestamps."""

    def test_generated_at_from_docx_mtime(self, tmp_path):
        """generated_at uses most recent DOCX file modification time."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry(1))
        packets_dir = tmp_path / "packets"
        internal_dir = packets_dir / "internal"
        internal_dir.mkdir(parents=True)
        (internal_dir / "epa_000000001.docx").write_bytes(b"PK mock")

        output_path = tmp_path / "tribes.json"
        result = build_index(
            registry_path,
            packets_dir,
            output_path,
            aliases_path=tmp_path / "no_aliases.json",
        )

        tribe = result["tribes"][0]
        assert tribe["generated_at"] is not None
        # Should be ISO 8601 with timezone
        assert "+" in tribe["generated_at"] or "Z" in tribe["generated_at"]

    def test_generated_at_null_when_no_docx(self, tmp_path):
        """generated_at is null when no DOCX files exist for the Tribe."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry(1))
        packets_dir = tmp_path / "packets"
        packets_dir.mkdir()

        output_path = tmp_path / "tribes.json"
        result = build_index(
            registry_path,
            packets_dir,
            output_path,
            aliases_path=tmp_path / "no_aliases.json",
        )

        tribe = result["tribes"][0]
        assert tribe["generated_at"] is None

    def test_generated_at_uses_latest_mtime(self, tmp_path):
        """generated_at picks the most recent file across subdirectories."""
        from scripts.build_web_index import _get_tribe_generated_at

        packets_dir = tmp_path / "packets"
        internal_dir = packets_dir / "internal"
        internal_dir.mkdir(parents=True)
        congressional_dir = packets_dir / "congressional"
        congressional_dir.mkdir(parents=True)

        # Create internal file first
        internal_file = internal_dir / "epa_000000001.docx"
        internal_file.write_bytes(b"PK older")

        # Small delay then create congressional file (newer)
        time.sleep(0.05)
        congressional_file = congressional_dir / "epa_000000001.docx"
        congressional_file.write_bytes(b"PK newer")

        result = _get_tribe_generated_at("epa_000000001", packets_dir)
        assert result is not None

        # The congressional file mtime should be the one used (newer)
        from datetime import datetime, timezone

        expected_mtime = congressional_file.stat().st_mtime
        expected_ts = datetime.fromtimestamp(
            expected_mtime, tz=timezone.utc
        ).isoformat()
        assert result == expected_ts
