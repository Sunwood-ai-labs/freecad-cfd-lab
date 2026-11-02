#!/bin/bash
source /usr/lib/openfoam/openfoam2306/etc/bashrc
export PATH=/usr/local/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
set -e
cd /tmp/case
reconstructPar -time "$1" > "/tmp/reconstruct-$1.log" 2>&1
postProcess -func writeCellCentres -time "$1" > "/tmp/cell-centres-$1.log" 2>&1
echo "RECONSTRUCTED $1"
