#!/bin/bash

set -ue
set -o pipefail

psql "host=$(yq -r '.raft.partner_addrs | map(split(":")[0]) | join(",")' ~/patroni/patroni.yml) dbname=db user=user password=12345678 target_session_attrs=read-write"
