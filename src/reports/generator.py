"""Report generator.

Produces Markdown briefings and JSON output from scored and change-detected
policy items, formatted for Tribal Leaders. Includes Knowledge Graph
insights: barriers, authorities, and funding vehicle summaries.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

OUTPUTS_DIR = Path("outputs")
ARCHIVE_DIR = OUTPUTS_DIR / "archive"


class ReportGenerator:
    """Generates policy briefings in Markdown and JSON."""

    def __init__(self, programs: list[dict]):
        self.programs = {p["id"]: p for p in programs}
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    def generate(self, scored_items: list[dict], changes: dict,
                 graph_data: dict | None = None,
                 monitor_data: dict | None = None,
                 classifications: dict | None = None) -> dict:
        """Generate both Markdown and JSON reports. Returns file paths."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d")
        md_content = self._build_markdown(
            scored_items, changes, timestamp, graph_data,
            monitor_data, classifications,
        )
        json_content = self._build_json(
            scored_items, changes, timestamp, graph_data,
            monitor_data, classifications,
        )

        # Write latest
        md_path = OUTPUTS_DIR / "LATEST-BRIEFING.md"
        json_path = OUTPUTS_DIR / "LATEST-RESULTS.json"
        md_path.write_text(md_content)
        json_path.write_text(json.dumps(json_content, indent=2, default=str))

        # Archive
        archive_md = ARCHIVE_DIR / f"briefing-{timestamp}.md"
        archive_json = ARCHIVE_DIR / f"results-{timestamp}.json"
        shutil.copy2(md_path, archive_md)
        shutil.copy2(json_path, archive_json)

        logger.info("Reports written: %s, %s", md_path, json_path)
        return {"markdown": str(md_path), "json": str(json_path)}

    def _build_markdown(self, items: list[dict], changes: dict,
                        timestamp: str, graph_data: dict | None = None,
                        monitor_data: dict | None = None,
                        classifications: dict | None = None) -> str:
        """Build a Markdown briefing for Tribal Leaders."""
        if monitor_data is None:
            logger.warning("monitor_data is None; monitor-dependent sections will be limited")
        if classifications is None:
            logger.warning("classifications is None; advocacy goals section will be skipped")

        lines = [
            f"# TCR Policy Briefing — {timestamp}",
            "",
            f"**Scan Date:** {timestamp}  ",
            f"**Items Above Threshold:** {len(items)}  ",
            f"**New Since Last Scan:** {changes['summary']['new_count']}  ",
        ]
        if graph_data:
            gs = graph_data.get("summary", {})
            lines.append(f"**Knowledge Graph:** {gs.get('total_nodes', 0)} nodes, {gs.get('total_edges', 0)} edges  ")
        lines.append("")

        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        if changes["summary"]["new_count"] > 0:
            lines.append(f"This scan identified **{changes['summary']['new_count']} new policy development(s)** since the last scan.")
        else:
            lines.append("No new policy developments since the last scan.")
        lines.append("")

        # Urgent/time-sensitive sections (above the fold)
        lines.extend(self._format_reconciliation_watch(monitor_data))
        lines.extend(self._format_iija_countdown(monitor_data))

        # New items section
        if changes["new_items"]:
            lines.append("## New Developments")
            lines.append("")
            for item in changes["new_items"]:
                lines.extend(self._format_item(item, is_new=True))
            lines.append("")

        # Critical program updates
        critical_items = [i for i in items if any(
            self.programs.get(pid, {}).get("priority") == "critical"
            for pid in i.get("matched_programs", [])
        )]
        if critical_items:
            lines.append("## Critical Program Updates")
            lines.append("")
            for item in critical_items:
                lines.extend(self._format_item(item))
            lines.append("")

        # Confidence Index Dashboard (with Hot Sheets column)
        ci_programs = [p for p in self.programs.values() if "confidence_index" in p]
        if ci_programs:
            lines.append("## Confidence Index Dashboard")
            lines.append("")
            lines.append("| Program | CI | Status | Hot Sheets | Determination |")
            lines.append("|---------|---:|--------|:----------:|--------------|")
            for prog in sorted(ci_programs, key=lambda p: p.get("confidence_index", 0)):
                ci = prog.get("confidence_index", 0)
                status = prog.get("ci_status", "N/A")
                det = prog.get("ci_determination", "")[:70]
                ci_pct = f"{ci * 100:.0f}%"

                # Hot Sheets sync indicator
                hs = prog.get("hot_sheets_status")
                if hs:
                    hs_status = hs.get("status", "")
                    original = prog.get("original_ci_status")
                    if original and original != hs_status:
                        hs_badge = f"OVERRIDE ({original}->{hs_status})"
                    elif hs_status == status:
                        hs_badge = "ALIGNED"
                    else:
                        hs_badge = f"DIVERGED ({hs_status})"
                else:
                    hs_badge = "--"

                lines.append(f"| {prog['name']} | {ci_pct} | {status} | {hs_badge} | {det} |")
            lines.append("")

            # Flagged programs warning
            flagged = [p for p in ci_programs if p.get("ci_status") == "FLAGGED"]
            if flagged:
                lines.append("### FLAGGED — Requires Specialist Attention")
                lines.append("")
                for prog in flagged:
                    lines.append(f"**{prog['name']}** (CI: {prog['confidence_index'] * 100:.0f}%)")
                    lines.append("")
                    lines.append(f"> {prog.get('ci_determination', '')}")
                    if prog.get("specialist_focus"):
                        lines.append(">")
                        lines.append(f"> **Specialist Focus:** {prog['specialist_focus']}")
                    lines.append("")

        # Analytical sections (after FLAGGED detail)
        lines.extend(self._format_advocacy_goals(classifications))
        lines.extend(self._format_structural_asks(graph_data))

        # Knowledge Graph: Barriers & Authorities
        if graph_data:
            lines.extend(self._format_graph_barriers(graph_data))
            lines.extend(self._format_graph_authorities(graph_data))

        # Advocacy Levers
        matched_program_ids = set()
        for item in items:
            matched_program_ids.update(item.get("matched_programs", []))
        if matched_program_ids:
            lines.append("## Active Advocacy Levers")
            lines.append("")
            lines.append("| Program | Priority | CI | Advocacy Lever |")
            lines.append("|---------|----------|---:|---------------|")
            for pid in sorted(matched_program_ids):
                prog = self.programs.get(pid)
                if prog:
                    ci = prog.get("confidence_index")
                    ci_str = f"{ci * 100:.0f}%" if ci is not None else "\u2014"
                    lines.append(f"| {prog['name']} | {prog['priority'].upper()} | {ci_str} | {prog['advocacy_lever']} |")
            lines.append("")

        # All items by score (reference data, near end)
        lines.append("## All Relevant Items (by score)")
        lines.append("")
        for item in items:
            lines.extend(self._format_item_brief(item))
        lines.append("")

        lines.append("---")
        lines.append(f"*Generated by TCR Policy Scanner on {timestamp}*")
        return "\n".join(lines)

    def _format_structural_asks(self, graph_data: dict) -> list[str]:
        """Format Five Structural Asks mapped to barriers and programs (RPT-01)."""
        if not graph_data:
            return []

        nodes = graph_data.get("nodes", {})
        edges = graph_data.get("edges", [])

        # Find structural ask nodes (id starts with "ask_")
        asks = {
            nid: n for nid, n in nodes.items()
            if n.get("_type") == "AdvocacyLeverNode" and nid.startswith("ask_")
        }
        if not asks:
            return []

        lines = [
            "## Five Structural Asks",
            "",
        ]

        for ask_id, ask in sorted(asks.items()):
            name = ask.get("description", ask_id)
            urgency = ask.get("urgency", "")
            target = ask.get("target", "")

            # Find programs this ask ADVANCES
            program_ids = [
                e["target"] for e in edges
                if e["source"] == ask_id and e["type"] == "ADVANCES"
            ]
            program_names = []
            for pid in program_ids:
                prog = self.programs.get(pid)
                if prog:
                    program_names.append(prog["name"])

            # Find barriers this ask mitigates
            barrier_ids = [
                e["source"] for e in edges
                if e["target"] == ask_id and e["type"] == "MITIGATED_BY"
            ]
            barrier_descs = []
            for bid in barrier_ids:
                bar = nodes.get(bid, {})
                if bar:
                    barrier_descs.append(bar.get("description", bid))

            urgency_badge = f" [{urgency}]" if urgency else ""
            lines.append(f"### {name}{urgency_badge}")
            lines.append(f"**Target:** {target}")
            if program_names:
                lines.append(f"**Programs:** {', '.join(program_names)}")
            if barrier_descs:
                lines.append(f"**Mitigates:**")
                for bd in barrier_descs:
                    lines.append(f"- {bd}")
            lines.append("")

        return lines

    def _format_iija_countdown(self, monitor_data: dict | None) -> list[str]:
        """Format IIJA sunset countdown table (RPT-03). Always renders."""
        lines = [
            "## IIJA Sunset Countdown",
            "",
        ]

        if not monitor_data:
            lines.append("*No monitor data available.*")
            lines.append("")
            return lines

        iija_alerts = [
            a for a in monitor_data.get("alerts", [])
            if a.get("monitor") == "iija_sunset"
        ]

        if not iija_alerts:
            lines.append("No IIJA-funded programs currently tracked.")
            lines.append("")
            return lines

        lines.append("| Program | Deadline | Days Remaining | Severity | Type |")
        lines.append("|---------|----------|---------------:|----------|------|")

        for alert in sorted(iija_alerts, key=lambda a: a.get("metadata", {}).get("days_remaining") or 9999):
            meta = alert.get("metadata", {})
            program_names = [
                self.programs.get(pid, {}).get("name", pid)
                for pid in alert.get("program_ids", [])
            ]
            name = ", ".join(program_names)
            deadline = meta.get("deadline", "N/A")
            days = meta.get("days_remaining")
            days_str = str(days) if days is not None else "N/A"
            severity = alert.get("severity", "INFO")
            threat_type = meta.get("threat_type", "sunset")

            lines.append(f"| {name} | {deadline} | {days_str} | {severity} | {threat_type} |")

        lines.append("")
        return lines

    def _format_reconciliation_watch(self, monitor_data: dict | None) -> list[str]:
        """Format Reconciliation Watch section (RPT-05). Always renders."""
        lines = [
            "## Reconciliation Watch",
            "",
        ]

        if not monitor_data:
            lines.append("*No monitor data available.*")
            lines.append("")
            return lines

        recon_alerts = [
            a for a in monitor_data.get("alerts", [])
            if a.get("monitor") == "reconciliation"
        ]

        if not recon_alerts:
            lines.append("No active reconciliation threats detected in current scan.")
            lines.append("")
            return lines

        for alert in recon_alerts:
            meta = alert.get("metadata", {})
            lines.append(f"**{alert.get('severity', 'WARNING')}:** {alert.get('title', '')}")
            lines.append("")
            lines.append(f"> {alert.get('detail', '')}")
            if meta.get("matched_keywords"):
                lines.append(f"> Keywords: {', '.join(meta['matched_keywords'])}")
            lines.append("")

        return lines

    def _format_advocacy_goals(self, classifications: dict | None) -> list[str]:
        """Format advocacy goal classifications per program (RPT-06)."""
        if not classifications:
            return []

        # Separate classified from unclassified (avoids table dominated by no-match rows)
        classified = {
            pid: c for pid, c in classifications.items()
            if c.get("advocacy_goal") is not None
        }

        if not classified:
            return []

        lines = [
            "## Advocacy Goal Classifications",
            "",
            "| Program | Advocacy Goal | Rule | Confidence | Reason |",
            "|---------|--------------|------|-----------|--------|",
        ]

        for pid, c in sorted(classified.items(),
                             key=lambda x: x[1].get("rule", "Z")):
            prog = self.programs.get(pid)
            name = prog["name"] if prog else pid
            goal = c.get("goal_label", "--")
            rule = c.get("rule", "--")
            conf = c.get("confidence", "--")
            reason = c.get("reason", "")[:80]
            lines.append(f"| {name} | {goal} | {rule} | {conf} | {reason} |")

        # Unclassified summary
        unclassified = [
            pid for pid, c in classifications.items()
            if c.get("advocacy_goal") is None
        ]
        if unclassified:
            lines.append("")
            names = [self.programs.get(pid, {}).get("name", pid) for pid in unclassified]
            lines.append(f"*{len(unclassified)} programs unclassified:* {', '.join(names)}")

        lines.append("")
        return lines

    def _format_graph_barriers(self, graph_data: dict) -> list[str]:
        """Format barrier/lever relationships from the knowledge graph."""
        nodes = graph_data.get("nodes", {})
        edges = graph_data.get("edges", [])

        barriers = {nid: n for nid, n in nodes.items()
                    if n.get("_type") == "BarrierNode"}
        if not barriers:
            return []

        lines = [
            "## Barriers & Mitigation Pathways",
            "",
        ]

        # Build barrier -> programs and barrier -> levers maps
        for bar_id, barrier in sorted(barriers.items()):
            severity = barrier.get("severity", "")
            sev_badge = f" [{severity}]" if severity else ""

            # Find which programs are blocked by this barrier
            blocked_pids = [e["source"] for e in edges
                            if e["target"] == bar_id and e["type"] == "BLOCKED_BY"]
            blocked_names = []
            for pid in blocked_pids:
                prog = self.programs.get(pid)
                if prog:
                    blocked_names.append(prog["name"])

            # Find levers that mitigate this barrier
            lever_ids = [e["target"] for e in edges
                         if e["source"] == bar_id and e["type"] == "MITIGATED_BY"]
            lever_descs = []
            for lid in lever_ids:
                lever = nodes.get(lid, {})
                if lever:
                    lever_descs.append(lever.get("description", lid))

            if blocked_names:
                lines.append(f"**{barrier.get('description', bar_id)}**{sev_badge}")
                lines.append(f"- Affects: {', '.join(blocked_names)}")
                if lever_descs:
                    lines.append(f"- Mitigation: {'; '.join(lever_descs)}")
                lines.append("")

        return lines

    def _format_graph_authorities(self, graph_data: dict) -> list[str]:
        """Format statutory authority relationships from the knowledge graph."""
        nodes = graph_data.get("nodes", {})
        edges = graph_data.get("edges", [])

        authorities = {nid: n for nid, n in nodes.items()
                       if n.get("_type") == "AuthorityNode"}
        if not authorities:
            return []

        lines = [
            "## Statutory Authority Map",
            "",
            "| Authority | Type | Durability | Programs |",
            "|-----------|------|-----------|----------|",
        ]

        for auth_id, auth in sorted(authorities.items()):
            citation = auth.get("citation", auth_id)
            auth_type = auth.get("authority_type", "")
            durability = auth.get("durability", "")

            # Find programs authorized by this authority
            auth_pids = [e["source"] for e in edges
                         if e["target"] == auth_id and e["type"] == "AUTHORIZED_BY"]
            prog_names = []
            for pid in auth_pids:
                prog = self.programs.get(pid)
                if prog:
                    prog_names.append(prog["name"])

            if prog_names:
                lines.append(f"| {citation} | {auth_type} | {durability} | {', '.join(prog_names)} |")

        lines.append("")
        return lines

    def _format_item(self, item: dict, is_new: bool = False) -> list[str]:
        """Format a single item as a detailed Markdown block."""
        new_badge = " **[NEW]**" if is_new else ""
        score = item.get("relevance_score", 0)
        lines = [
            f"### {item['title']}{new_badge}",
            "",
            f"- **Score:** {score:.2f}",
            f"- **Source:** {item.get('source', '').replace('_', ' ').title()}",
            f"- **Published:** {item.get('published_date', 'N/A')}",
            f"- **Type:** {item.get('document_type', 'N/A')}",
        ]
        if item.get("matched_program_names"):
            lines.append(f"- **Programs:** {', '.join(item['matched_program_names'])}")
        if item.get("cfda"):
            lines.append(f"- **CFDA:** {item['cfda']}")
        if item.get("abstract"):
            abstract = item["abstract"][:500]
            lines.append(f"- **Summary:** {abstract}")
        if item.get("url"):
            lines.append(f"- **Link:** [{item['url']}]({item['url']})")
        lines.append("")
        return lines

    def _format_item_brief(self, item: dict) -> list[str]:
        """Format a single item as a one-line summary."""
        score = item.get("relevance_score", 0)
        programs = ", ".join(item.get("matched_program_names", []))
        return [
            f"- **{score:.2f}** | [{item['title']}]({item.get('url', '')}) | {programs}",
        ]

    def _build_json(self, items: list[dict], changes: dict,
                    timestamp: str, graph_data: dict | None = None,
                    monitor_data: dict | None = None,
                    classifications: dict | None = None) -> dict:
        """Build the JSON report structure."""
        result = {
            "scan_date": timestamp,
            "summary": changes["summary"],
            "scan_results": items,
            "changes": {
                "new_items": changes["new_items"],
                "updated_items": changes["updated_items"],
                "removed_items": [{"source_id": i.get("source_id"), "title": i.get("title")} for i in changes["removed_items"]],
            },
        }
        if graph_data:
            result["knowledge_graph"] = graph_data
        if monitor_data:
            result["monitor_data"] = monitor_data
        if classifications:
            result["classifications"] = classifications
        return result
