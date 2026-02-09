"""Scan-to-scan change detection.

Compares current scan results against the previous scan to identify
new items, removed items, and items with score changes.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_FILE = Path("outputs/LATEST-RESULTS.json")


class ChangeDetector:
    """Detects changes between scan cycles."""

    def __init__(self, cache_path: Path | None = None):
        self.cache_path = cache_path or CACHE_FILE

    def detect_changes(self, current_items: list[dict]) -> dict:
        """Compare current items to the previous scan and return a change report."""
        previous_items = self._load_previous()
        prev_by_id = {self._item_key(item): item for item in previous_items}
        curr_by_id = {self._item_key(item): item for item in current_items}

        new_items = []
        updated_items = []
        removed_items = []

        for key, item in curr_by_id.items():
            if key not in prev_by_id:
                new_items.append(item)
            else:
                prev = prev_by_id[key]
                score_delta = item.get("relevance_score", 0) - prev.get("relevance_score", 0)
                if abs(score_delta) > 0.05:
                    item_with_delta = dict(item)
                    item_with_delta["score_delta"] = round(score_delta, 4)
                    item_with_delta["previous_score"] = prev.get("relevance_score", 0)
                    updated_items.append(item_with_delta)

        for key, item in prev_by_id.items():
            if key not in curr_by_id:
                removed_items.append(item)

        changes = {
            "new_items": sorted(new_items, key=lambda x: x.get("relevance_score", 0), reverse=True),
            "updated_items": sorted(updated_items, key=lambda x: abs(x.get("score_delta", 0)), reverse=True),
            "removed_items": removed_items,
            "summary": {
                "new_count": len(new_items),
                "updated_count": len(updated_items),
                "removed_count": len(removed_items),
                "total_current": len(current_items),
                "total_previous": len(previous_items),
            },
        }

        logger.info(
            "Changes: %d new, %d updated, %d removed",
            len(new_items), len(updated_items), len(removed_items),
        )
        return changes

    def save_current(self, items: list[dict]) -> None:
        """Save current results as the baseline for the next scan."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w") as f:
            json.dump({"scan_results": items}, f, indent=2, default=str)
        logger.info("Saved %d items to %s", len(items), self.cache_path)

    def _load_previous(self) -> list[dict]:
        """Load results from the previous scan."""
        if not self.cache_path.exists():
            logger.info("No previous scan results found at %s", self.cache_path)
            return []
        try:
            with open(self.cache_path) as f:
                data = json.load(f)
            return data.get("scan_results", [])
        except (json.JSONDecodeError, KeyError):
            logger.warning("Could not parse previous results at %s", self.cache_path)
            return []

    @staticmethod
    def _item_key(item: dict) -> str:
        """Generate a unique key for an item across sources."""
        return f"{item.get('source', '')}:{item.get('source_id', '')}"
