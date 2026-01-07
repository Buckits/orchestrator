# Claude Code AI Agent Framework

A reusable framework for building AI-powered development workflows using Claude Code CLI and the autonomous-coding orchestration loop.

---

## Overview

This framework provides:

- **Specialist Agents** - Domain experts that own specific files/directories
- **Skills** - Reusable knowledge patterns loaded before execution
- **Session Management** - Multi-phase task coordination across context windows
- **Hooks** - Prompt analysis for automatic skill recommendations
- **Orchestration** - Routing complex tasks to the right specialists

```
┌─────────────────────────────────────────────────────────────────┐
│                     HOW IT WORKS                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User Request: "Build a user authentication feature"            │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────┐                        │
│  │  Hook analyzes prompt               │                        │
│  │  Recommends: session-management,    │                        │
│  │  orchestrate-feature skills         │                        │
│  └─────────────────────────────────────┘                        │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────┐                        │
│  │  session-planner agent              │                        │
│  │  Creates session-current.md         │                        │
│  │  Plans phases and agents            │                        │
│  └─────────────────────────────────────┘                        │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────┐                        │
│  │  Execution (CLI or autonomous loop) │                        │
│  │  Spawns specialists per phase       │                        │
│  │  Updates session file               │                        │
│  └─────────────────────────────────────┘                        │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────┐                        │
│  │  finalize agent                     │                        │
│  │  Validates, proposes commit         │                        │
│  └─────────────────────────────────────┘                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
.claude/
├── README.md                    # This file - framework documentation
├── settings.json                # Claude Code project settings (hooks config)
├── settings.local.json          # Local permissions (gitignored)
│
├── agents/                      # Specialist agent definitions
│   ├── AGENTS.md                # ⭐ Master registry, routing table, ownership matrix
│   ├── session-planner.md       # Plans multi-phase features, creates sessions
│   ├── finalize.md              # Validation, type generation, commit proposal
│   ├── framework-maintainer.md  # Adds/modifies agents and skills
│   └── [domain-agent].md        # Your domain-specific agents
│
├── skills/                      # Reusable knowledge patterns
│   ├── skill-rules.json         # ⭐ Skill activation triggers and metadata
│   ├── session-management/      # Multi-phase coordination
│   │   └── SKILL.md
│   ├── orchestrate-feature/     # Feature orchestration patterns
│   │   └── SKILL.md
│   ├── sub-agent-invocation/    # Agent delegation patterns
│   │   └── SKILL.md
│   ├── git-commits/             # Commit formatting (human approval required)
│   │   └── SKILL.md
│   └── [domain-skill]/          # Your domain-specific skills
│       └── SKILL.md
│
├── tasks/                       # Session persistence
│   ├── session-current.md       # ⭐ Active session (phases, progress, notes)
│   ├── session-001.md           # Archived sessions
│   ├── session-002.md
│   └── ...
│
├── hooks/                       # Prompt analysis hooks
│   └── SkillActivationHook/     # Recommends skills based on user prompts
│       ├── skill-activation-prompt.mjs
│       ├── skill-activation-prompt.sh
│       └── recommendation-log.json
│
└── templates/                   # Prompt templates (for autonomous-coding)
    └── orchestrator.template.md
```

---

## Core Components

### 1. Agents (`agents/`)

Agents are **domain specialists** with exclusive file ownership. Each agent:
- Owns specific directories/files (only they can modify)
- Has deep expertise in their domain
- Loads required skills before execution
- Updates session files when working in a session

#### Required Agents (Framework Core)

| Agent | Purpose | Owns |
|-------|---------|------|
| `session-planner` | Creates session files for multi-phase work | `.claude/tasks/session-*.md` |
| `finalize` | Validates changes, proposes commits | None (runs commands only) |
| `framework-maintainer` | Adds/modifies agents and skills | `.claude/agents/`, `.claude/skills/` |

#### AGENTS.md - The Master Registry

`agents/AGENTS.md` is the **single source of truth** for agent coordination:

```markdown
## Agent Registry
| Agent | File | Purpose | Primary Skill |

## Ownership Matrix
| Agent | OWNS (only they modify) | NEVER touches |

## Routing Table
IF task involves...  →  SPAWN this agent

## Dependency Graph
Execution order when multiple agents needed
```

**Both the autonomous-coding loop AND local Claude CLI read AGENTS.md for routing decisions.**

---

### 2. Skills (`skills/`)

Skills provide **reusable knowledge patterns** loaded before execution. Unlike agents, skills don't own files - they provide context.

#### Required Skills (Framework Core)

| Skill | Purpose |
|-------|---------|
| `session-management` | Session file format, lifecycle, TodoWrite sync |
| `orchestrate-feature` | Multi-agent feature orchestration patterns |
| `sub-agent-invocation` | How to properly delegate to specialist agents |
| `git-commits` | Commit formatting (requires human approval) |

#### skill-rules.json - Activation Triggers

Defines when skills should be recommended:

```json
{
  "skills": {
    "session-management": {
      "type": "orchestration",
      "priority": "critical",
      "file": "session-management/SKILL.md",
      "promptTriggers": {
        "keywords": ["build feature", "multi-phase", "session"],
        "intentPatterns": ["build.*feature", "implement.*system"]
      }
    }
  },
  "agents": {
    "session-planner": {
      "description": "Plans multi-phase features",
      "triggers": ["complex feature", "plan implementation"]
    }
  }
}
```

---

### 3. Sessions (`tasks/`)

Sessions persist context across multiple interactions or context windows.

#### session-current.md

The active session file tracks:
- User's original request
- Planned phases with assigned agents
- Progress checkboxes
- Implementation notes from each agent
- Architectural decisions

```markdown
# Session 001 - User Authentication

## Session Overview
**User Request**: Add user authentication with JWT tokens
**Workflow Mode**: Development

## Task Breakdown

### Phase 1: Database Schema
**Assigned Agent**: database-prisma
- [x] Create User model
- [x] Add Session model

### Phase 2: API Endpoints
**Assigned Agent**: api-module
- [ ] POST /auth/login
- [ ] POST /auth/logout

## Agent Work Sections

### database-prisma
**Status**: Completed
**Implementation Notes**: Created User with email unique index...
```

#### Session Lifecycle

```
1. CREATE    → session-planner analyzes request, creates session-current.md
2. EXECUTE   → Specialists work on phases, update session file
3. COMPLETE  → All phases done, finalize agent validates
4. ARCHIVE   → session-current.md renamed to session-{N}.md
```

---

### 4. Hooks (`hooks/`)

Hooks run automatically in response to Claude Code events.

#### SkillActivationHook

A `UserPromptSubmit` hook that analyzes every user prompt and recommends relevant skills:

```javascript
// skill-activation-prompt.mjs
// 1. Reads user prompt from stdin
// 2. Matches against skill-rules.json triggers
// 3. Outputs skill recommendations
// 4. Tracks recommendations to avoid repeats
```

**Configuration in settings.json:**

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "node .claude/hooks/SkillActivationHook/skill-activation-prompt.mjs \"$PROMPT\""
          }
        ]
      }
    ]
  }
}
```

---

## Execution Modes

### Mode 1: Local Claude CLI

Direct interaction with Claude Code:

```bash
claude

# User: "Build a user profile feature"
# → Hook recommends session-management skill
# → Claude uses session-planner to create session file
# → User says "keep going" to execute phases
# → Specialists work on each phase
# → finalize agent validates and proposes commit
```

### Mode 2: Autonomous Coding Loop

Python orchestrator spawns fresh Claude contexts:

```bash
# From autonomous-coding repo
./run-project.sh /path/to/your/project
```

The loop:
1. Detects `.claude/agents/` → uses orchestration mode
2. Reads `session-current.md` for current phase
3. Spawns specialist agent for that phase
4. Agent updates session file
5. Loop continues until all phases complete

---

## Adding to Your Project

### Step 1: Copy Framework Files

Copy these directories to your project:

```
.claude/
├── agents/
│   ├── AGENTS.md              # Customize for your domains
│   ├── session-planner.md     # Keep as-is
│   ├── finalize.md            # Customize validation commands
│   └── framework-maintainer.md # Keep as-is
├── skills/
│   ├── skill-rules.json       # Add your domain skills
│   ├── session-management/
│   ├── orchestrate-feature/
│   ├── sub-agent-invocation/
│   └── git-commits/
├── tasks/                     # Empty, sessions created here
├── hooks/
│   └── SkillActivationHook/
└── settings.json              # Hook configuration
```

### Step 2: Create Your CLAUDE.md

Add a `CLAUDE.md` at project root with:

```markdown
# CLAUDE.md - Your Project

## Agent System
Reference: `.claude/agents/AGENTS.md`

### Available Agents
| Agent | Domain | When to Use |
| `session-planner` | Planning | Multi-phase features |
| `your-domain-agent` | Your Domain | Your use case |
| `finalize` | Validation | After changes complete |

## Skills System
Reference: `.claude/skills/skill-rules.json`
```

### Step 3: Add Domain Agents

Use `framework-maintainer` agent or manually create:

```markdown
---
name: your-agent
description: When to use this agent...
model: opus
color: blue
---

You are the [Name] Agent...

## Exclusive Ownership
### Files I OWN:
- your/paths/

### Files I NEVER touch:
- other/paths/
```

### Step 4: Add Domain Skills

Create skill directories with SKILL.md files and register in skill-rules.json.

---

## Key Principles

### 1. Agents Own Files

Every file path has exactly one agent that can modify it. The ownership matrix in AGENTS.md is authoritative.

### 2. Skills Provide Knowledge

Skills are loaded for context, not execution. Multiple agents can use the same skill.

### 3. Sessions Bridge Contexts

Session files persist state across context windows. The autonomous-coding loop relies on this.

### 4. Commits Require Approval

The git-commits skill requires explicit human approval before any commit executes.

### 5. Routing via AGENTS.md

Both manual (CLI) and automated (loop) execution use AGENTS.md for routing decisions.

---

## Common Workflows

### Simple Task (No Session)

```
User: "Add a field to the User model"
  → Direct to database-prisma agent
  → Agent makes change
  → finalize agent validates
```

### Complex Feature (With Session)

```
User: "Build document tagging with search"
  → session-planner creates session-current.md
  → Phase 1: database-prisma creates models
  → Phase 2: api-module creates endpoints
  → Phase 3: finalize validates
  → User approves commit
```

### Autonomous Coding

```
1. Create session-current.md with phases
2. Run: ./run-project.sh /your/project
3. Loop executes phases automatically
4. Review and approve commits
```

---

## Customization Points

| Component | How to Customize |
|-----------|------------------|
| Add new agent | Use framework-maintainer or create file + update AGENTS.md |
| Add new skill | Create skill dir + update skill-rules.json |
| Change routing | Edit AGENTS.md routing table |
| Change triggers | Edit skill-rules.json promptTriggers |
| Change validation | Edit finalize.md commands |
| Change commit format | Edit git-commits/SKILL.md |

---

## Integration with autonomous-coding

This framework is designed to work with the [autonomous-coding](https://github.com/anthropics/autonomous-coding) Python loop:

1. Mount your project with `.claude/agents/` directory
2. Create `session-current.md` with phases
3. Run the loop - it will:
   - Detect orchestration mode
   - Read session file for current phase
   - Spawn appropriate specialist
   - Update session on completion
   - Continue until done

```bash
# Docker
docker run -v /your/project:/project autonomous-coding

# Direct
python main.py --project-dir /your/project --mode orchestration
```

---

## File Reference

| File | Purpose | Who Modifies |
|------|---------|--------------|
| `AGENTS.md` | Agent registry, routing, ownership | framework-maintainer |
| `skill-rules.json` | Skill triggers and metadata | framework-maintainer |
| `session-current.md` | Active session state | session-planner, all agents |
| `settings.json` | Hook configuration | Manual |
| Agent `.md` files | Agent definitions | framework-maintainer |
| Skill `SKILL.md` files | Skill knowledge | framework-maintainer |

---

## Troubleshooting

### "Agent not found"
- Check AGENTS.md registry
- Verify agent file exists in `agents/`

### "Skill not loading"
- Check skill-rules.json has entry
- Verify SKILL.md exists at specified path

### "Session not progressing"
- Check session-current.md format
- Verify phase agent assignments match AGENTS.md

### "Autonomous loop not detecting mode"
- Ensure `.claude/agents/` directory exists
- Check for `session-current.md` file

---

## Version

Framework Version: 2.0

Compatible with:
- Claude Code CLI
- autonomous-coding loop
- Claude Opus 4 / Sonnet 4 models
