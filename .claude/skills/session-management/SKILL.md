---
name: session-management
description: Coordinate multi-phase tasks with session files that work with the orchestrator's MCP tools
---

# Skill: Session Management

Use this skill for multi-phase task coordination. Session files must follow the **exact format** below for MCP tools to work.

---

## Session File Location

```
.claude/tasks/
├── session-current.md    # Active session (MCP tools read/write this)
├── session-1.md          # Archived
├── session-2.md          # Archived
└── ...
```

---

## Session File Format (CRITICAL)

**This exact format is required for MCP session tools to work.**

```markdown
# Session: [Short descriptive name]

## Status
- Phase: 1 of N
- Current Agent: [first-agent-name]
- State: pending

## User Request
[Verbatim user request here]

## Phases
1. [ ] agent-name - Short description of what this phase does
2. [ ] other-agent - Short description of next phase
3. [ ] finalize - Validate and commit

## Work Log
(agents will update this)
```

### Format Rules

| Element | Format | Example |
|---------|--------|---------|
| Title | `# Session: name` | `# Session: Add user auth` |
| Status section | Bullet list under `## Status` | `- Phase: 1 of 3` |
| Phase line | `N. [x] agent - description` | `1. [ ] api-agent - Create endpoints` |
| Checkbox | `[ ]` pending, `[x]` complete | `2. [x] db-agent - Add schema` |

**Do NOT use:**
- `### Phase 1: Name` headers
- `**Assigned Agent**: name` format
- Nested task lists under phases
- Any other structure

---

## Session Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                     SESSION LIFECYCLE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. CREATE      session-planner creates session-current.md      │
│       │         - Uses exact format above                        │
│       │         - Phases as flat numbered list                   │
│       ▼                                                          │
│  2. EXECUTE     Orchestrator loop runs                           │
│       │         - MCP tools read/update session file             │
│       │         - Each phase spawns assigned agent               │
│       │         - Agent updates Work Log when done               │
│       ▼                                                          │
│  3. COMPLETE    All phases marked [x]                            │
│       │         - State changes to "complete"                    │
│       │         - Finalize agent runs last                       │
│       ▼                                                          │
│  4. ARCHIVE     Session preserved                                │
│                 - session-current.md → session-N.md              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## MCP Session Tools

The orchestrator has these MCP tools (they require the exact format above):

| Tool | Purpose |
|------|---------|
| `session_get_status` | Get current phase, agent, state |
| `session_get_next_phase` | Get next incomplete phase |
| `session_mark_phase_complete` | Mark phase done, update state |
| `session_is_complete` | Check if all phases done |

---

## Example Session File

```markdown
# Session: Add document tagging

## Status
- Phase: 1 of 3
- Current Agent: schema-agent
- State: pending

## User Request
Add ability to tag documents with custom labels

## Phases
1. [ ] schema-agent - Add Tag model and document_tags junction table
2. [ ] api-agent - Create tag CRUD endpoints and document tagging
3. [ ] finalize - Validate build and propose commit

## Work Log
(agents will update this)
```

After phase 1 completes:

```markdown
# Session: Add document tagging

## Status
- Phase: 2 of 3
- Current Agent: api-agent
- State: pending

## User Request
Add ability to tag documents with custom labels

## Phases
1. [x] schema-agent - Add Tag model and document_tags junction table
2. [ ] api-agent - Create tag CRUD endpoints and document tagging
3. [ ] finalize - Validate build and propose commit

## Work Log
### Phase 1 (schema-agent)
Created Tag model with id, name, color fields.
Added document_tags junction table for many-to-many relationship.
Files: src/db/schema.ts
```

---

## Agent Work Log Updates

When an agent completes work, append to Work Log:

```markdown
### Phase N (agent-name)
Brief description of what was done.
Key files modified: path/to/file.ts, path/to/other.ts
```

---

## TodoWrite Synchronization

Keep TodoWrite in sync with session phases:

**Session File:**
```markdown
## Phases
1. [x] schema-agent - Add Tag model
2. [ ] api-agent - Create endpoints
3. [ ] finalize - Validate and commit
```

**TodoWrite:**
```javascript
TodoWrite(todos=[
  {"content": "Add Tag model", "status": "completed", "activeForm": "Adding Tag model"},
  {"content": "Create endpoints", "status": "in_progress", "activeForm": "Creating endpoints"},
  {"content": "Validate and commit", "status": "pending", "activeForm": "Validating and committing"}
])
```

---

## Quick Reference

| Action | How |
|--------|-----|
| Create session | Write to `.claude/tasks/session-current.md` using exact format |
| Check status | Use `session_get_status` MCP tool |
| Get next phase | Use `session_get_next_phase` MCP tool |
| Mark complete | Use `session_mark_phase_complete` MCP tool |
| Archive session | Rename `session-current.md` to `session-N.md` |

---

## Common Mistakes (AVOID)

1. **Wrong title format**: Use `# Session: name` not `# Session 1 - name`
2. **Missing Status section**: Must have `## Status` with Phase/Agent/State bullets
3. **Wrong phase format**: Use `1. [ ] agent - desc` not `### Phase 1:` headers
4. **Nested tasks**: Keep phases flat, one line each
5. **Missing finalize**: Always end with `finalize` agent
