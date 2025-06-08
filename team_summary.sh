#!/bin/bash

echo "=== Team Development Summary ==="
echo "Time: $(date)"
echo "================================"

for team in team-1a-audio-pyaudio team-1b-audio-sounddevice team-2-ai-providers team-3-tts-audio team-4-state-metrics team-5-integration; do
    echo -e "\n[$team]"
    
    # Check if session is active
    if tmux has-session -t $team 2>/dev/null; then
        echo "Status: Active ✓"
        
        # Check git changes
        cd /Users/tom/personal/hello-world.dev/.worktrees/$team 2>/dev/null
        if [ $? -eq 0 ]; then
            # Count files
            added=$(git status --porcelain | grep "^??" | grep -v INSTRUCTIONS | wc -l | tr -d ' ')
            modified=$(git status --porcelain | grep "^ M" | wc -l | tr -d ' ')
            echo "Files: $modified modified, $added added"
            
            # List changed files
            git status --porcelain | grep -v INSTRUCTIONS | head -3 | while read line; do
                echo "  $line"
            done
            
            # Check for commits
            commits=$(git log --oneline -n 1 2>/dev/null)
            if [[ ! "$commits" =~ "d98e4d4" ]]; then
                echo "Commits: Yes"
            fi
        fi
    else
        echo "Status: Inactive ✗"
    fi
done

echo -e "\n================================"
echo "To check a specific team: tmux attach -t <team-name>"
echo "To send a message: tmux send -t <team-name> \"message\"; tmux send -t <team-name> Enter"