# Parallel Development Workflow

## Usage
```bash
claude
# Initialize parallel development for a new feature
/project:dispatch @specs/2025_06_07_14_35_00_conversation_system.md
```

**Purpose**: Intelligently sets up and manages parallel development workflows using git worktrees, automatically creating isolated development environments for concurrent feature development with Claude Code SDK.

**When to use**:
- Starting development on a new feature that can be parallelized
- Executing complex plans that benefit from multiple development streams
- Managing concurrent work on different aspects of the same feature

## Variables
FEATURE_OR_PLAN: $ARGUMENTS

## Execute these commands
- Log args passed to command with `echo "FEATURE_OR_PLAN: $FEATURE_OR_PLAN"`

> Intelligently set up and execute parallel development workflow

### 0. Tools
- You and your instance can use the internet to look up references needed to complete the tasks
- When dispatching workers, use the Claude Code SDK ([SDK Docs](https://docs.anthropic.com/en/docs/claude-code/sdk), [CLI Docs](https://docs.anthropic.com/en/docs/claude-code/cli-usage))
  - Take advantage of the `--output-format json` flag to store session IDs for workers so that they maintain context as they're completing their tasks
  - Workers should run using Claude Sonnet with `--model sonnet`

### 1. Analyze Input
- Determine if FEATURE_OR_PLAN is a feature name (needs init) or a plan to execute
- Extract feature name from plan path if needed (e.g., `conversation_system` from `@specs/2025_06_07_14_35_00_conversation_system.md`)
- Check if `.worktrees/FEATURE_NAME/` exists
- If sessions.json exists, check for any active sessions that need to be resumed

### 2. Initialize Worktrees (if needed)
> If worktrees don't exist for this feature:

- FEATURE_NAME is extracted from FEATURE_OR_PLAN (remove @specs/ prefix and .md suffix, extract meaningful name)
- WORKSTREAMS is the number of workstreams that can be run in parallel
- Create `.worktrees/` directory if it doesn't exist
- Store current directory: `MAIN_DIR=$(pwd)`
- For WORKSTREAM in WORKSTREAMS:
  - WORKTREE_PATH is `$MAIN_DIR/.worktrees/$FEATURE_NAME/$WORKSTREAM`
  - BRANCH_NAME is `$FEATURE_NAME/$WORKSTREAM`
  - Check if branch exists: `git branch --list $BRANCH_NAME`
  - If branch exists, delete it: `git branch -D $BRANCH_NAME`
  - RUN `git worktree add -b $BRANCH_NAME $WORKTREE_PATH`
  - RUN `cp $MAIN_DIR/.env $WORKTREE_PATH/.env 2>/dev/null || true`
  - RUN `cd $WORKTREE_PATH && uv sync`
  - If `.env` exists in worktree:
    - UPDATE `PORT` value if present: `PORT=$((BASE_PORT + workstream_index))`
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
    - **Resources**: Links to relevant documentation, APIs, or references

### 4. Execute Parallel Development
> Once worktrees and TASKS.md are ready:

- Note the actual source directory name from project structure
- RUN `ls -la hello_world/` (or whatever the actual source directory is)
- RUN `ls -la .worktrees/$FEATURE_NAME/` to show worktree structure

#### Initialize Worker Sessions:
- Create session tracking infrastructure:
  ```bash
  touch $MAIN_DIR/.worktrees/$FEATURE_NAME/sessions.json
  touch $MAIN_DIR/.worktrees/$FEATURE_NAME/COORDINATION.md
  echo "# Coordination Notes\n\nUse this file to document important decisions and interfaces between workstreams.\n" > $MAIN_DIR/.worktrees/$FEATURE_NAME/COORDINATION.md
  ```

- For each workstream in `.worktrees/$FEATURE_NAME/`:
  ```bash
  cd $WORKTREE_PATH

  # Create workstream-specific system prompt
  SYSTEM_PROMPT="You are implementing the $WORKSTREAM workstream. Your working directory is $WORKTREE_PATH.
  Read TASKS.md for your objectives. You can use the internet to look up documentation and references.
  Create RESULTS.md when complete. Check COORDINATION.md periodically for updates from other workstreams.
  Focus only on your workstream - do not modify files outside your scope."

  # Start Claude Sonnet session
  session_info=$(claude --model sonnet --output-format json \
    --system-prompt "$SYSTEM_PROMPT" \
    "Read TASKS.md and begin implementation. Start by understanding the requirements and creating a plan.")

  # Extract session ID and store
  session_id=$(echo $session_info | jq -r '.session_id')
  timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  # Update sessions.json
  jq --arg ws "$WORKSTREAM" --arg sid "$session_id" --arg ts "$timestamp" \
    '.[$ws] = {"session_id": $sid, "started_at": $ts, "status": "active"}' \
    $MAIN_DIR/.worktrees/$FEATURE_NAME/sessions.json > tmp.json && \
    mv tmp.json $MAIN_DIR/.worktrees/$FEATURE_NAME/sessions.json
  ```

#### Monitor and Guide Workers:
- Show active sessions: `cat .worktrees/$FEATURE_NAME/sessions.json | jq .`
- For each active session, check progress:
  ```bash
  # Check worker status
  claude --session-id $session_id --output-format json \
    "What's your current progress? List completed tasks and what you're working on now."
  ```
- If coordination is needed between workers, update COORDINATION.md

#### Worker Task Guidelines:
Each worker should be instructed to:
1. **Read and understand TASKS.md completely**
2. **Create an implementation plan**
3. **Implement features incrementally with tests**
4. **Document important decisions in code comments**
5. **Update COORDINATION.md if creating interfaces used by other workstreams**
6. **Create RESULTS.md with**:
   - Summary of all changes made
   - List of files created/modified
   - Any challenges encountered and solutions
   - Integration notes for other workstreams
   - Suggestions for future improvements
7. **Commit changes with descriptive messages**

### 5. Review Results
> After workers complete their tasks:

- Collect all RESULTS.md files:
  ```bash
  find .worktrees/$FEATURE_NAME -name "RESULTS.md" -exec echo "=== {} ===" \; -exec cat {} \; -exec echo "" \;
  ```
- Check for completion status:
  ```bash
  for workstream in core-pipeline robustness architecture testing; do
    session_id=$(jq -r ".$workstream.session_id" .worktrees/$FEATURE_NAME/sessions.json)
    echo "Checking $workstream (session: $session_id)..."
    claude --session-id $session_id --output-format json "Have you completed all tasks and created RESULTS.md?"
  done
  ```
- Identify integration points and potential conflicts
- Create merge strategy for combining workstream branches

### 6. Error Handling
- If worktree creation fails, clean up partial state
- If branch already exists, remove it before creating new one
- If uv sync fails, note the error but continue
- Always return to main directory after operations
- If a worker session fails:
  ```bash
  # Resume from saved session
  session_id=$(jq -r ".$WORKSTREAM.session_id" .worktrees/$FEATURE_NAME/sessions.json)
  cd .worktrees/$FEATURE_NAME/$WORKSTREAM
  claude --session-id $session_id --output-format json "Continue where you left off. Check your previous work and resume implementation."
  ```

### 7. Session Management
> Maintain worker sessions throughout development:

#### Session Tracking File Structure:
`.worktrees/$FEATURE_NAME/sessions.json`:
```json
{
  "core-pipeline": {
    "session_id": "sess_xxx",
    "started_at": "2024-01-06T10:00:00Z",
    "status": "active",
    "last_checkpoint": "Completed WhisperKit integration"
  },
  "robustness": {
    "session_id": "sess_yyy",
    "started_at": "2024-01-06T10:05:00Z",
    "status": "active",
    "last_checkpoint": "Working on error recovery"
  }
}
```

#### Session Commands:
- **Resume session**: `claude --session-id $session_id --output-format json "Continue implementation"`
- **Check status**: `claude --session-id $session_id --output-format json "Report current status"`
- **Close session**: `claude --session-id $session_id --output-format json "Finalize work and exit"`

### 8. Worker Communication
> Enable coordination between parallel workers:

#### Shared Resources:
1. **COORDINATION.md**: Central coordination file for important decisions
2. **Interface definitions**: Document in relevant source files
3. **Integration tests**: Create in shared test directory

#### Communication Protocol:
- Workers should check COORDINATION.md before making architectural decisions
- Document any new APIs or interfaces that other workstreams will use
- Flag any blocking dependencies in COORDINATION.md
- Use semantic commit messages for easier integration

### 9. Completion and Integration
> Final steps to integrate all workstreams:

1. **Verify all workers completed**:
   ```bash
   # Check all RESULTS.md exist
   for ws in core-pipeline robustness architecture testing; do
     if [ -f ".worktrees/$FEATURE_NAME/$ws/RESULTS.md" ]; then
       echo "✓ $ws completed"
     else
       echo "✗ $ws incomplete"
     fi
   done
   ```

2. **Close all sessions**:
   ```bash
   for ws in core-pipeline robustness architecture testing; do
     session_id=$(jq -r ".$ws.session_id" .worktrees/$FEATURE_NAME/sessions.json)
     claude --session-id $session_id --output-format json "exit"
   done
   ```

3. **Create integration branch**:
   ```bash
   git checkout -b $FEATURE_NAME/integration
   for ws in core-pipeline robustness architecture testing; do
     git merge --no-ff $FEATURE_NAME/$ws -m "Merge $ws workstream"
   done
   ```

4. **Generate final report** with:
   - Summary of all workstream achievements
   - Integration test results
   - Any remaining conflicts or issues
   - Recommendations for deployment

## Example Execution Log
```bash
# Main orchestrator (Opus) output
FEATURE_OR_PLAN: @specs/2025_06_07_14_35_00_conversation_system.md
Extracted feature name: conversation_system
Creating 4 workstreams: core-pipeline, robustness, architecture, testing
Initializing worktrees...
✓ Created .worktrees/conversation_system/core-pipeline
✓ Created .worktrees/conversation_system/robustness
✓ Created .worktrees/conversation_system/architecture
✓ Created .worktrees/conversation_system/testing

Generating TASKS.md files...
✓ Created TASKS.md for core-pipeline
✓ Created TASKS.md for robustness
✓ Created TASKS.md for architecture
✓ Created TASKS.md for testing

Dispatching Claude Sonnet workers...
✓ Started session sess_abc123 for core-pipeline
✓ Started session sess_def456 for robustness
✓ Started session sess_ghi789 for architecture
✓ Started session sess_jkl012 for testing

Workers are now implementing their tasks...
Check .worktrees/conversation_system/sessions.json for status
```
