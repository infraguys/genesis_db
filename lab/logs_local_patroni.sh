#!/bin/bash

set -ue
set -o pipefail

sudo journalctl -xu genesis-patroni -n 100 -f
