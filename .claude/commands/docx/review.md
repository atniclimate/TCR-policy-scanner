---
description: Launch the 5-agent DOCX Hot Sheet review swarm for a Tribe's advocacy packet
arguments:
  - name: tribe
    description: Tribe name (e.g., "Muckleshoot", "Tulalip", "Quinault Nation")
    required: true
  - name: audience
    description: Target audience — tribal_leader, legislator, or intertribal (default tribal_leader)
    required: false
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Task
---

# DOCX Hot Sheet Agent Review

Launch the 3-pass agent review cycle for **$ARGUMENTS.tribe**.

## Context

The DOCX production team consists of 5 specialist reviewers and 1 orchestrator:

| Agent | Priority | Focus | Definition |
|-------|----------|-------|------------|
| accuracy-agent | 1 (highest) | Data correctness, dollar verification, delegation accuracy | `D:\Claude-Workspace\.claude\agents\docx-production\accuracy-agent.md` |
| audience-director | 2 | 2-page constraint, tone calibration, audience fit | `D:\Claude-Workspace\.claude\agents\docx-production\audience-director.md` |
| political-translator | 3 | Strategic framing, ask specificity, sovereignty framing | `D:\Claude-Workspace\.claude\agents\docx-production\political-translator.md` |
| design-aficionado | 4 | Visual hierarchy, spacing, grid integrity | `D:\Claude-Workspace\.claude\agents\docx-production\design-aficionado.md` |
| copy-editor | 5 (lowest) | Text compression, readability, redundancy | `D:\Claude-Workspace\.claude\agents\docx-production\copy-editor.md` |

Conflict resolution priority: accuracy > audience > political > design > copy.

Target audience for this review: **$ARGUMENTS.audience** (default: tribal_leader).

## Execution Protocol

### Pass 1: Draft Generation

1. Generate the DOCX advocacy packet for **$ARGUMENTS.tribe** using the existing pipeline:
   ```python
   from src.packets.orchestrator import PacketOrchestrator
   ```
   Run the equivalent of: `python -m src.main --prep-packets --tribe "$ARGUMENTS.tribe"`

2. Locate the generated .docx file in `outputs/packets/` and the data caches:
   - Award cache: `data/award_cache/<tribe_id>.json`
   - Hazard profile: `data/hazard_profiles/<tribe_id>.json`
   - Program inventory: `data/program_inventory.json`

3. Record the tribe_id, CI statuses of relevant programs, and the DOCX output path.

### Pass 2: Parallel Agent Review (5 agents)

Launch ALL 5 review agents IN PARALLEL using the Task tool. Each agent:
- subagent_type: `general-purpose`
- Must READ its agent definition file first (see table above)
- Must follow the review protocol in its definition exactly
- Must produce a JSON critique array as its output

**Agent dispatch template** (repeat for all 5, adjusting agent name and file):

```
Task(
  subagent_type="general-purpose",
  description="<agent-name> review of <tribe> Hot Sheet",
  prompt="""
  You are acting as the <agent-name> reviewer for the DOCX Hot Sheet production team.

  FIRST: Read your full agent definition and review protocol:
    Read file: D:\Claude-Workspace\.claude\agents\docx-production\<agent-name>.md

  THEN: Review the following Tribe's data for a Hot Sheet review:
    - Tribe: $ARGUMENTS.tribe
    - Audience: $ARGUMENTS.audience (default: tribal_leader)
    - DOCX source code: F:\tcr-policy-scanner\src\packets\docx_hotsheet.py
    - DOCX engine: F:\tcr-policy-scanner\src\packets\docx_engine.py
    - Style definitions: F:\tcr-policy-scanner\src\packets\docx_styles.py
    - Template builder: F:\tcr-policy-scanner\src\packets\docx_template.py
    - Award cache: F:\tcr-policy-scanner\data\award_cache\<tribe_id>.json
    - Hazard profile: F:\tcr-policy-scanner\data\hazard_profiles\<tribe_id>.json
    - Program inventory: F:\tcr-policy-scanner\data\program_inventory.json
    - Sections renderer: F:\tcr-policy-scanner\src\packets\docx_sections.py
    - Economic module: F:\tcr-policy-scanner\src\packets\economic.py

  Read the source files and data caches relevant to your review focus.
  Apply your review protocol systematically.

  OUTPUT: Return ONLY a JSON array of critique objects matching your agent's
  critique schema. No prose, no markdown — just the JSON array.
  If you find no issues, return an empty array: []
  """
)
```

IMPORTANT: Launch all 5 agents in a SINGLE message with 5 parallel Task tool calls.
Replace `<agent-name>` and `<tribe_id>` with actual values.

### Pass 3: Conflict Resolution

After all 5 agents return (or at least 3 of 5):

1. Parse each agent's JSON critique array output.

2. Feed critiques into the Python-side orchestrator:
   ```python
   from src.packets.agent_review import AgentReviewOrchestrator
   reviewer = AgentReviewOrchestrator(enabled=True)
   reviewer.register_critiques("accuracy-agent", accuracy_critiques)
   reviewer.register_critiques("audience-director", audience_critiques)
   # ... etc for all completed agents
   # Mark any timed-out agents:
   reviewer.mark_agent_failed("agent-name")
   ```

3. Resolve conflicts:
   ```python
   conflicts = reviewer.resolve_conflicts()
   gate = reviewer.check_quality_gate()
   log = reviewer.get_resolution_log()
   ```

4. If the quality gate FAILS, report why and stop.

5. If the quality gate PASSES, present the resolution log.

### Output Report

Present results in this format:

```
## Review Complete: $ARGUMENTS.tribe

### Pass 2 Summary
- Agents completed: X/5
- Total critiques: N (critical: X, major: Y, minor: Z)

### Conflicts Resolved
| Section | Agents | Winner | Reason |
|---------|--------|--------|--------|
| ...     | ...    | ...    | ...    |

### Approved Revisions
| Agent | Section | Severity | Summary |
|-------|---------|----------|---------|
| ...   | ...     | ...      | ...     |

### Quality Gate: PASSED/FAILED
- Agents: X/5 (min 3)
- Critical resolved: X/X
- Unresolved accuracy: 0

### Recommended Actions
1. [List specific actions from approved revisions]
```

## Quality Gate Rules

- At least 3 of 5 agents must complete (quality minimum)
- ALL critical-severity critiques must be addressed
- ZERO unresolved accuracy critiques allowed
- Document must remain exactly 2 pages

## Notes

- If an agent times out, mark it failed and continue with available results
- The accuracy-agent has HIGHEST priority — its findings override all others
- The 2-page constraint is NON-NEGOTIABLE (audience-director enforces this)
- Never cut accuracy-required additions to save space — cut lower-priority content instead
- Always capitalize: Tribal, Indigenous, Nation, Peoples
