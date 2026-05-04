#!/bin/bash

set -ue
set -o pipefail

sudo journalctl -xu exordos-patroni -n 100 -f
