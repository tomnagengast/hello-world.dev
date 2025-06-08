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
- Log args passed to command with `echo "FEATURE_OR_PLAN: $FEATURE_OR_PLAN"`

> Intelligently set up and execute parallel development workflow

### 1. Analyze Input
- Determine if FEATURE_OR_PLAN is a feature name (needs init) or a plan to execute
- Extract feature name from plan path if needed (e.g., `conversation_system` from `@specs/2025_06_07_14_35_00_conversation_system.md`)
- Check if `.worktrees/FEATURE_NAME/` exists

### 2. Initialize Worktrees (if needed)
> If worktrees don't exist for this feature:

- FEATURE_NAME is extracted from FEATURE_OR_PLAN (remove @specs/ prefix and .md suffix, extract meaningful name)
- WORKSTREAMS is the number of workstreams that can be run in parallel
- Create `.worktrees/` directory if it doesn't exist
- Store current directory: `MAIN_DIR=$(pwd)`
- For WORKSTREAM in WORKSTREAMS:
  - NUM_AGENTS is the number of agents to dispatch (higher ambiguity = more agents)
  - For i in NUM_AGENTS:
    - WORKTREE_PATH is `$MAIN_DIR/.worktrees/$FEATURE_NAME/$WORKSTREAM-$i`
    - BRANCH_NAME is `$FEATURE_NAME/$WORKSTREAM-$i`
    - Check if branch exists: `git branch --list $BRANCH_NAME`
    - If branch exists, delete it: `git branch -D $BRANCH_NAME`
    - RUN `git worktree add -b $BRANCH_NAME $WORKTREE_PATH`
    - RUN `cp $MAIN_DIR/.env $WORKTREE_PATH/.env 2>/dev/null || true`
    - RUN `cd $WORKTREE_PATH && uv sync`
    - If `.env` exists in worktree:
        - UPDATE `PORT` value if present: `PORT=$((PORT + i))`
    - RUN `cd $WORKTREE_PATH && pwd && git ls-files | head -10` to validate
- RUN `git worktree list` to verify all trees

### 3. Create TASKS.md for Each Worktree
> Generate detailed task files for each worktree:

- CD back to main directory: `cd $MAIN_DIR`
- For each worktree in `.worktrees/$FEATURE_NAME/`:
  - Create a comprehensive `$WORKTREE_PATH/TASKS.md` file that includes:
    - **Your Mission**: Clear objective for this workstream
    - **Key Files**: List of files to create/modify (use actual source directory name)
    - **Implementation Checklist**: Step-by-step tasks with checkboxes
    - **Technical Requirements**: Specific implementation details
    - **Testing Requirements**: How to verify the implementation
    - **Success Criteria**: Definition of done
    - **Example Code**: Reference implementations if helpful
    - **Dependencies**: What this workstream depends on or blocks

### 4. Execute Parallel Development
> Once worktrees and TASKS.md are ready:

- Note the actual source directory name from project structure
- RUN `ls -la hello_world/` (or whatever the actual source directory is)
- RUN `ls -la .worktrees/$FEATURE_NAME/` to show worktree structure

#### If FEATURE_OR_PLAN is a detailed plan:
- READ: FEATURE_OR_PLAN content
- Show the TASKS.md files created for each workstream
- Divide work into sub-features that can be parallelized
- Assign subagents based on complexity:
  - Standard complexity: 2 agents
  - High ambiguity: 3-4 agents
  - Straightforward: 1 agent

#### Dispatch subagents:
- Each agent works in their respective worktree directory
- Agents follow the TASKS.md in their worktree
- Each agent creates a `RESULTS.md` file documenting their changes
- Agents should not start servers/clients - focus on code changes only

### 5. Review Results
- List all RESULTS.md files created
- Provide summary of parallel development outcomes
- Show any merge conflicts or integration issues

### 6. Error Handling
- If worktree creation fails, clean up partial state
- If branch already exists, remove it before creating new one
- If uv sync fails, note the error but continue
- Always return to main directory after operations
