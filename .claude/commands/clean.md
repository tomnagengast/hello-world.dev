# Clean Up Old Dev Work

<!--
## Usage
```bash
claude

# Clean local
/project:clean
/project:clean origin
```
-->

## Variables
REMOTE_NAME: $ARGUMENTS

## Do

> Clean up all git worktrees, including:
    - git references
    - git branches
    - tmux sessions created for the worktree (branch will be in the session name if exists)

- If REMOTE_NAME:
    > Clean up all dev branches on REMOTE_NAME
