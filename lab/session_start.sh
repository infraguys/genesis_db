#!/bin/bash

set -ue
set -o pipefail


session=patroni
# Start a new tmux session
tmux kill-session -t $session || true
tmux new-session -s $session -d
tmux set -g mouse on
# tmux bind-key -t "(emacs|vi)-copy" "j" page-up
# tmux bind-key -t "(emacs|vi)-copy" ";" page-down

# Split vertically (creates 2 panes)
tmux split-window -h

# Split top pane horizontally (creates 3 panes)
tmux select-pane -t 0
tmux split-window -v

# Split bottom pane horizontally (creates 4 panes)
tmux select-pane -t 2
tmux split-window -v

# Now run commands in each pane:
tmux send-keys -t 0 "head ./README.md -n21" Enter
readarray servers_map < <(yq -r .raft.partner_addrs[] /var/lib/postgresql/patroni/patroni.yml  | cut -d':' -f 1)
start_tab=1
for server in "${servers_map[@]}"; do
    server=${server%$'\n'}
    tmux send-keys -t $start_tab "ssh -i .ssh/lab -o StrictHostKeyChecking=no ubuntu@${server} -t 'sudo journalctl -xu genesis-patroni -n 100 -f; bash -l'" Enter
    (( start_tab+=1 ))
done

tmux attach-session -t $session
