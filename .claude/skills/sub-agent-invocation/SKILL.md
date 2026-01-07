---
name: sub-agent-invocation
description: Delegate to specialist agents with constitutional invocation patterns including context, instructions, references, and success criteria
---

# Skill: Sub-Agent Invocation

Use this skill when delegating work to specialist agents. Proper invocation ensures agents have full context and produce quality results.

---

## When to Use This Skill

- Delegating to any specialist agent
- Coordinating multiple agents on a feature
- Needing comprehensive agent output
- Following session-based workflows

---

## Constitutional Requirements

Every agent invocation MUST include these four components:

```
┌─────────────────────────────────────────────────────────────────┐
│              MANDATORY INVOCATION COMPONENTS                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. CONTEXT        What the agent needs to understand            │
│                    - User's original request                     │
│                    - Project state                               │
│                    - Related work already done                   │
│                                                                  │
│  2. INSTRUCTIONS   Specific task assignment                      │
│                    - Clear, actionable requirements              │
│                    - Scope boundaries                            │
│                    - Expected deliverables                       │
│                                                                  │
│  3. REFERENCES     Supporting information                        │
│                    - Session file location                       │
│                    - Relevant skills to load                     │
│                    - Example patterns                            │
│                                                                  │
│  4. DIRECTIVES     Quality and format requirements               │
│                    - Thinking depth                              │
│                    - Output format                               │
│                    - Validation requirements                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Invocation Template

```
Task(
  subagent_type="general-purpose",
  prompt="""
USER'S ORIGINAL REQUEST:
[Verbatim user request - do not paraphrase]

CONTEXT:
- Project: [Current state and goal]
- Background: [Why this task matters]
- Dependencies: [What this builds on or requires]
- Session: [Session file path if applicable]

TASK ASSIGNMENT:
[Clear, specific requirements with defined scope]

Requirements:
1. [Specific requirement]
2. [Specific requirement]
3. [Specific requirement]

Out of Scope:
- [What NOT to do]

REFERENCES:
- Agent definition: .claude/agents/{agent-name}.md
- Skills: Check .claude/skills/ for relevant domain skills
- Session: Read [session file path] for context
- Examples: See [file path] for similar implementations

DIRECTIVES:
Think hard and provide thorough implementation.

DELIVERABLES:
1. [Expected output 1]
2. [Expected output 2]

SUCCESS CRITERIA:
- [How to know task is complete]
- [Quality requirements]
"""
)
```

---

## Routing Decision Matrix

### Use Session Planner When:

| Scenario | Example |
|----------|---------|
| Multi-agent coordination needed | "Build user profile feature" |
| Complex, ambiguous request | "Improve the document system" |
| New feature development | "Add tagging to documents" |
| Strategic planning required | "How should we architect X?" |

### Use Domain Agent When:

| Scenario | Example |
|----------|---------|
| Single domain change | "Add email field to User" |
| Clear, scoped task | "Add GET /api/tags endpoint" |
| Build validation | "Check if build passes" |

---

## Parallel vs Sequential Execution

### Parallel Execution

Use when agents work on independent components:

```
// Can run in parallel - no dependencies between them
Task(subagent_type="agent-1", prompt="Create component A...")
Task(subagent_type="agent-2", prompt="Create component B...")
```

### Sequential Execution

Use when agents depend on previous work:

```
// Must run sequentially - later work depends on earlier
1. Task(subagent_type="agent-1", prompt="Create foundation...")
   // Wait for completion
2. Task(subagent_type="agent-2", prompt="Build on foundation...")
   // Wait for completion
3. Task(subagent_type="finalize", prompt="Validate all...")
```

---

## Context Passing Between Agents

### From Earlier to Later Agent

```
CONTEXT:
- Previous agent completed [work description]
- Artifacts created: [list of files/components]
- Key details: [important information for this phase]
```

---

## Session Integration

When working within a session:

### Include Session Reference

```
CONTEXT:
- Session: .claude/tasks/session-current.md
- Phase: 2 of 4 (Current Phase Name)
- Previous Work: [Summary from Phase 1]
```

### Require Session Update

```
DIRECTIVES:
After completing work:
1. Update session file with implementation notes
2. Mark tasks complete in TodoWrite
3. Provide next agent context
```

---

## Thoroughness Levels

### Quick Check
```
Think and provide a focused solution.
```
Use for: Simple additions, clear requirements

### Standard
```
Think hard and provide a thorough implementation.
```
Use for: Most development work

### Deep Analysis
```
Think very hard and provide comprehensive analysis with alternatives considered.
```
Use for: Architecture decisions, complex debugging

---

## Common Mistakes to Avoid

### ❌ Vague Context
```
"Create a tag system"
```

### ✅ Specific Context
```
"Create a Tag model with name, color, userId fields for document categorization.
The Tag model should have a many-to-many relationship with Document."
```

### ❌ Missing Dependencies
```
"Create tag API endpoints"
```

### ✅ Include Dependencies
```
"Create tag API endpoints. The Tag model was created in Phase 1 and is
available. See the model file for schema details."
```

### ❌ No Success Criteria
```
"Make it work"
```

### ✅ Clear Success Criteria
```
"SUCCESS CRITERIA:
- All CRUD endpoints return correct status codes
- Validation errors handled properly
- Build passes without errors"
```

---

## Quick Reference

### Checklist Before Invocation

- [ ] User's original request included verbatim
- [ ] Context explains current state
- [ ] Task assignment is specific and scoped
- [ ] References point to relevant files/examples
- [ ] Success criteria are measurable
- [ ] Session file referenced (if applicable)
