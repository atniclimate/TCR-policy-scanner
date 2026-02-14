# DOCX Agent Swarm Review Coordination

## Agent Domains (Non-Overlapping)

| Agent | Role | Domain Files | Output |
|-------|------|-------------|--------|
| 1 - Style & Layout | design-aficionado | docx_styles.py, docx_template.py, hot_sheet_template.docx | style_layout_findings.json |
| 2 - Content Integrity | accuracy-agent | docx_hotsheet.py, docx_sections.py, docx_regional_sections.py | content_integrity_findings.json |
| 3 - Orchestration & Data Flow | code-reviewer | orchestrator.py, context.py, economic.py, relevance.py | orchestration_findings.json |
| 4 - Quality Gate | code-reviewer | agent_review.py, quality_review.py, doc_types.py | quality_gate_findings.json |
| 5 - Test Coverage | test-writer | test_docx_*.py, test_packets.py | test_coverage_findings.json |

## Shared Reference Files (Read-Only for All)
- src/packets/context.py
- src/packets/doc_types.py

## Rules
1. READ-ONLY audit -- no source file modifications
2. Each agent writes findings to outputs/docx_review/{agent_name}_findings.json
3. JSON format: {file, line, severity, category, description, suggestion}
4. Severity levels: critical, major, minor
5. After all agents complete, findings synthesized into SYNTHESIS.md
