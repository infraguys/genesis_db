#!/bin/bash

set -ue
set -o pipefail

sudo -u postgres PGPASSWORD="12345678" pgbench -i db -U user -h 127.0.0.1
