#!/bin/bash

set -ue
set -o pipefail

sudo -u postgres PGPASSWORD="12345678" pgbench --time=5 --client=1 --rate=1000 --failures-detailed db -U user -h 127.0.0.1
