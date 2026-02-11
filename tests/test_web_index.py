"""Tests for scripts/build_web_index.py -- web index builder."""

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
        assert "packet_count" in result
        assert "total_tribes" in result
        assert "tribes" in result
        assert isinstance(result["tribes"], list)

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

    def test_has_packet_true_when_docx_exists(self, tmp_path):
        """Tribes with DOCX files have has_packet=True."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry(3))
        packets_dir = tmp_path / "packets"
        packets_dir.mkdir()
        # Create a DOCX file for tribe epa_000000001
        (packets_dir / "epa_000000001.docx").write_bytes(b"PK mock docx content")
        output_path = tmp_path / "tribes.json"

        result = build_index(registry_path, packets_dir, output_path)

        tribe_map = {t["id"]: t for t in result["tribes"]}
        assert tribe_map["epa_000000001"]["has_packet"] is True
        assert tribe_map["epa_000000002"]["has_packet"] is False
        assert tribe_map["epa_000000003"]["has_packet"] is False
        assert result["packet_count"] == 1

    def test_has_packet_false_when_no_docx(self, tmp_path):
        """Tribes without DOCX files have has_packet=False and file_size_kb=0."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry(2))
        packets_dir = tmp_path / "packets"
        packets_dir.mkdir()
        output_path = tmp_path / "tribes.json"

        result = build_index(registry_path, packets_dir, output_path)

        for tribe in result["tribes"]:
            assert tribe["has_packet"] is False
            assert tribe["file_size_kb"] == 0
        assert result["packet_count"] == 0

    def test_file_size_kb_accurate(self, tmp_path):
        """file_size_kb reflects actual DOCX file size."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry(1))
        packets_dir = tmp_path / "packets"
        packets_dir.mkdir()
        # Create a known-size file (2048 bytes = 2.0 KB)
        content = b"X" * 2048
        (packets_dir / "epa_000000001.docx").write_bytes(content)
        output_path = tmp_path / "tribes.json"

        result = build_index(registry_path, packets_dir, output_path)

        tribe = result["tribes"][0]
        assert tribe["file_size_kb"] == 2.0

    def test_missing_packets_dir_handled(self, tmp_path):
        """build_index() handles missing packets directory gracefully."""
        from scripts.build_web_index import build_index

        registry_path = tmp_path / "registry.json"
        _write_json(registry_path, _mock_registry(2))
        packets_dir = tmp_path / "nonexistent_packets"
        output_path = tmp_path / "tribes.json"

        result = build_index(registry_path, packets_dir, output_path)

        assert result["packet_count"] == 0
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
