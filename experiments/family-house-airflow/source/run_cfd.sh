#!/bin/bash
source /usr/lib/openfoam/openfoam2306/etc/bashrc
export PATH=/usr/local/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
export OMP_NUM_THREADS=4
export OMPI_ALLOW_RUN_AS_ROOT=1
export OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
set -e
cd /tmp/case
archive="/tmp/previous-results-$(date +%Y%m%d-%H%M%S)"
for result in [1-9]*; do
    if [[ -d "$result" && "$result" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
        mkdir -p "$archive"
        mv -- "$result" "$archive/"
    fi
done
cd /tmp/meshCase
bash ./Allmesh > /tmp/mesh-run.log 2>&1
checkMesh -meshQuality > /tmp/mesh-check.log 2>&1
grep -q 'Mesh OK.' /tmp/mesh-check.log
cd /tmp/case
bash ./Allrun > /tmp/solver-run.log 2>&1
postProcess -func writeCellCentres -latestTime > /tmp/cell-centres.log 2>&1
echo CFD_RUN_FINISHED
