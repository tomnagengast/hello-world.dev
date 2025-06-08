# Parallel Development Workflow

<!--
## Usage
```bash
claude
# Initialize parallel development for a new feature
/project:dispatch @specs/<spec>.md
```
-->

## Variables
FEATURE_OR_PLAN: $ARGUMENTS

## Do

- Log args passed to command with `echo "FEATURE_OR_PLAN: $FEATURE_OR_PLAN"`

> Great, this all looks good. And now, before we hand it off to the dev team, I want you to do a first pass of FEATURE_OR_PLAN to understand what needs to be done and what can be done in parallel. Once you have a plan for the dev team to follow, create git worktrees for the dev team based on how you see work being split up and executed. the team can work in as many concurrent workstreams as you see fit.
> For workstreams with more ambiguity, dispatch multiple teams to take a stab at implementation and we'll be able to pick the best one.
> Once the worktrees are all set up and instructions are in place for the dev teams, simulate them by running claude code instances in parallel subprocesses. You'll need to manage the instances by resuming their work by referencing the session id returned after their first turn. You shouldn't be doing any work though, all coding, testing, and validation should be done by the dev team instances.

## Resource

- Git worktrees should be created in the `./.worktrees` directory
- You and your instance can use the internet to look up references needed to complete the tasks
- When dispatching workers, use the Claude Code SDK ([SDK Docs](https://docs.anthropic.com/en/docs/claude-code/sdk), [CLI Docs](https://docs.anthropic.com/en/docs/claude-code/cli-usage))
  - Take advantage of the `--output-format json` flag to store session IDs for workers so that they maintain context as they're completing their tasks
  - Workers should run using Claude Sonnet with `--model sonnet`
- Use TMUX for session management
  - Auto approve the initial Claude Code prompt with `tmux new -d -s claude '<team-id>'; sleep 1; tmux send -t claude Enter;`
