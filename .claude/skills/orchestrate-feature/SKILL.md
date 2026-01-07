---
name: orchestrate-feature
description: Route work to specialist agents with explicit delegation. Never implement directly.
---

# Feature Orchestration Skill

## The Golden Rule

**You are a ROUTER, not an IMPLEMENTER.**

Your job is to:
1. Use session MCP tools to track progress
2. Spawn the right agents for each phase
3. Validate completion
4. Never write application code

---

## Session MCP Tools

Use these tools to manage session state:

| Tool | Purpose |
|------|---------|
| `session_get_status` | Get current phase, agent, state |
| `session_get_next_phase` | Get next incomplete phase |
| `session_mark_phase_complete` | Mark phase done, advance to next |
| `session_is_complete` | Check if all phases done |

---

## Routing Protocol

For ANY task involving file modifications:

1. **Use `session_get_next_phase`** to get the current phase and agent
2. **Read AGENTS.md** to understand the agent's ownership
3. **Spawn the agent** with proper context
4. **Use `session_mark_phase_complete`** after agent returns

---

## Orchestrator Constraints

### You MUST:
1. Use MCP session tools to track progress
2. Use the routing table for EVERY file modification decision
3. Spawn the appropriate agent - NEVER modify source files yourself
4. Wait for each agent to complete before proceeding
5. Spawn finalize agent when all phases complete

### You MUST NEVER:
1. Use Edit or Write tools on source files
2. Use Bash to run build commands directly
3. Implement features yourself
4. Skip the routing table lookup

---

## Agent Invocation Template

When spawning an agent:

```
Task(
  subagent_type="general-purpose",
  prompt="""
## CONTEXT
You are the {agent-name} agent.
Session: .claude/tasks/session-current.md
Phase: {N} of {total}

Previous work: {summary of completed phases}

## TASK
{specific task from session file}

## INSTRUCTIONS
1. Read your agent definition: .claude/agents/{agent-name}.md
2. Check .claude/skills/ for relevant domain skills
3. Read session file for full context

Rules:
- Only modify files you own (see AGENTS.md)
- Update session Work Log when done
- Do NOT make git commits

## DIRECTIVES
1. Read your agent definition first
2. Check for relevant skills in .claude/skills/
3. Read session file for context
4. Complete the task
5. Update session file Work Log
6. Return summary

Begin by reading your agent definition.
"""
)
```

---

## Session File Format

**CRITICAL**: Sessions must use this exact format for MCP tools to work:

```markdown
# Session: [Short name]

## Status
- Phase: 1 of N
- Current Agent: [agent-name]
- State: pending

## User Request
[verbatim request]

## Phases
1. [ ] agent-name - description
2. [ ] other-agent - description
3. [ ] finalize - Validate and commit

## Work Log
(agents will update this)
```

**Phase format**: `N. [ ] agent-name - description`

---

## Execution Order

Follow dependency order:

```
1. FOUNDATION     → Infrastructure, config, dependencies
2. DATA LAYER     → Database, schema, models
3. BUSINESS LOGIC → Services, workers, processing
4. INTERFACE      → API, UI, endpoints
5. FINALIZE       → Validation, types, commit (ALWAYS LAST)
```

---

## Handling Failures

If an agent reports failure:
1. DO NOT try to fix it yourself
2. Read the error message
3. Determine if it's a routing issue (wrong agent)
4. Either:
   - Spawn the same agent again with more context
   - Spawn a different agent to fix the prerequisite
   - Ask the user for guidance

---

## Completion Checklist

Before declaring a feature complete:

- [ ] `session_is_complete` returns true
- [ ] `finalize` agent has run and passed
- [ ] Commit proposed (if requested)

---

## Quick Reference

```
PLANNING WORK     → session-planner
VALIDATION        → finalize
DOMAIN WORK       → [check project AGENTS.md]
```

**When in doubt: Check the routing table. Never implement yourself.**
