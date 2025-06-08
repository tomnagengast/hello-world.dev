#!/bin/bash

TEAM=$1

if [ -z "$TEAM" ]; then
    echo "Usage: ./check_team.sh <team-name>"
    echo "Available teams:"
    tmux ls | grep team | cut -d: -f1
    exit 1
fi

echo "Checking progress for $TEAM"
echo "==========================="

# Check session status
if tmux has-session -t $TEAM 2>/dev/null; then
    echo "✓ Session is active"
    
    # Capture recent output
    echo -e "\nRecent activity:"
    tmux capture-pane -t $TEAM -p | tail -20
    
    # Check git status
    echo -e "\nGit status:"
    cd /Users/tom/personal/hello-world.dev/.worktrees/$TEAM 2>/dev/null && git status -s
    
    echo -e "\nTo interact with this session: tmux attach -t $TEAM"
else
    echo "✗ Session is not active"
fi