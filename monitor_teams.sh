#!/bin/bash

echo "Monitoring team progress..."
echo "========================="

while true; do
    clear
    echo "Team Progress Monitor - $(date)"
    echo "========================================"
    
    # Check each team's git status and recent commits
    for team in team-1a-audio-pyaudio team-1b-audio-sounddevice team-2-ai-providers team-3-tts-audio team-4-state-metrics team-5-integration; do
        echo -e "\n[$team]"
        
        # Check if session is still active
        if tmux has-session -t $team 2>/dev/null; then
            echo "✓ Session active"
            
            # Check git status
            cd /Users/tom/personal/hello-world.dev/.worktrees/$team 2>/dev/null
            if [ $? -eq 0 ]; then
                # Count modified files
                modified=$(git status --porcelain | wc -l | tr -d ' ')
                echo "  Modified files: $modified"
                
                # Check for commits
                commits=$(git log --oneline -n 1 --pretty=format:"%h %s" 2>/dev/null)
                if [ "$commits" != "d98e4d4 Update dispatch command instructions to manage sessions with tmux" ]; then
                    echo "  Latest commit: $commits"
                fi
                
                # Check if currently editing files
                editing=$(lsof +D . 2>/dev/null | grep -E "(py|md|toml)$" | wc -l | tr -d ' ')
                if [ "$editing" -gt 0 ]; then
                    echo "  Files being edited: $editing"
                fi
            fi
        else
            echo "✗ Session inactive"
        fi
    done
    
    echo -e "\n========================================"
    echo "Press Ctrl+C to stop monitoring"
    echo "To check a session: tmux attach -t <team-name>"
    
    sleep 30
done