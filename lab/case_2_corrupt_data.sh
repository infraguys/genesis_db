#!/bin/bash

set -ue
set -o pipefail

sudo su postgres <<'EOF'
for i in /var/lib/postgresql/patroni/data/base/*/*; do
    # Just make file empty
    > $i
done
EOF
