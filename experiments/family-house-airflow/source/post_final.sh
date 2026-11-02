#!/bin/bash
source /usr/lib/openfoam/openfoam2306/etc/bashrc
export PATH=/usr/local/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
set -e
cd /tmp/case
postProcess -func writeCellCentres -latestTime > /tmp/cell-centres.log 2>&1
echo POST_PROCESS_FINISHED
