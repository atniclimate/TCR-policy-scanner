"""Tests for scripts/build_web_index.py -- web index builder.

Tests cover the updated 4-document-type format:
  - Per-Tribe documents dict (internal_strategy + congressional_overview)
  - Regions section with Doc C/D
  - Metadata section with per-type doc counts
  - Backward compatibility with flat packet directory
"""

import json
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
