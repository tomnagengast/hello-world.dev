# Parallel Development Workflow

## Usage
```bash
claude
# Initialize parallel development for a new feature
/project:dispatch @specs/2025_06_07_14_35_00_conversation_system.md
```

**Purpose**: Intelligently sets up and manages parallel development workflows using git worktrees, automatically creating isolated development environments for concurrent feature development.

**When to use**:
- Starting development on a new feature that can be parallelized
- Executing complex plans that benefit from multiple development streams
- Managing concurrent work on different aspects of the same feature

## Variables
FEATURE_OR_PLAN: $ARGUMENTS

## Execute these commands
- Log args passed to command with `echo FEATURE_OR_PLAN`

> Intelligently set up and execute parallel development workflow

### 1. Analyze Input
- Determine if FEATURE_OR_PLAN is a feature name (needs init) or a plan to execute
- Check if `.worktrees/FEATURE_OR_PLAN/` exists

### 2. Initialize Worktrees (if needed)
> If worktrees don't exist for this feature:

- WORKSTREAMS is the number of workstreams that can be run in parallel
- Create `.worktrees/` directory if it doesn't exist
- For WORKSTREAM in WORKSTREAMS:
  - NUM_AGENTS is the number of agents to dispatch (higher ambiguity = more agents)
  - For i in NUM_AGENTS:
    - BRANCH_NAME is `./.worktrees/FEATURE_OR_PLAN/WORKSTREAM-i`
    - RUN `git worktree add -b FEATURE_OR_PLAN/WORKSTREAM-i BRANCH_NAME`
    - RUN `cp ./.env BRANCH_NAME/.env` if .env exists
    - RUN `cd BRANCH_NAME && uv sync`
    - UPDATE `BRANCH_NAME/.env` if it exists:
        - `PORT: $PORT+(i)`
    - RUN `cd BRANCH_NAME && pwd && git ls-files` to validate
- RUN `git worktree list` to verify all trees

### 3. Create TASKS.md for Each Worktree
> Generate detailed task files for each worktree:

For each worktree in `.worktrees/FEATURE_OR_PLAN/`:
- Create a comprehensive `TASKS.md` file that includes:
  - **Your Mission**: Clear objective for this workstream
  - **Key Files**: List of files to create/modify
  - **Implementation Checklist**: Step-by-step tasks with checkboxes
  - **Technical Requirements**: Specific implementation details
  - **Testing Requirements**: How to verify the implementation
  - **Success Criteria**: Definition of done
  - **Example Code**: Reference implementations if helpful
  - **Dependencies**: What this workstream depends on or blocks

### 4. Execute Parallel Development
> Once worktrees and TASKS.md are ready:

RUN `eza conversation_system --tree --git-ignore`
RUN `eza .worktrees --tree --level 3`

#### If FEATURE_OR_PLAN is a detailed plan:
- READ: FEATURE_OR_PLAN
- Show the TASKS.md files created for each workstream
- Divide work into sub-features that can be parallelized
- Assign subagents based on complexity:
  - Standard complexity: 2 agents
  - High ambiguity: 3-4 agents
  - Straightforward: 1 agent

#### Dispatch subagents:
- Each agent works in their respective `.worktrees/FEATURE_OR_PLAN/sub-feature-i/` directory
- Agents follow the TASKS.md in their worktree
- Each agent creates a `RESULTS.md` file documenting their changes
- Agents should not start servers/clients - focus on code changes only

### 5. Review Results
- List all RESULTS.md files created
- Provide summary of parallel development outcomes
