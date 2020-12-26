#!/bin/bash
set -eu

if [ $# -ne 1 ]; then
    echo "USAGE: ASPERA_SCP_PASS=SECRET $(basename $0) /data/idrftp-incoming/idrNNNN-aaaa-bbbb"
        echo "    This must only be run with the idrNNNN-aaaa-bbbb directory,"
        echo "    not a parent or sub directory"
    exit 1
fi

SOURCE="${1%/}"
FILESET="$(basename "$SOURCE")"
DESTINATION=idrftp@hx-fasp-1.ebi.ac.uk:
LOGSDIR="$HOME/ascp/logs"

docker run -it --rm \
    -v "$SOURCE:/$FILESET:ro" \
    -v "$LOGSDIR:/logs" \
    -u root \
    -e ASPERA_SCP_PASS="$ASPERA_SCP_PASS" \
    openmicroscopy/aspera-client \
    -T -Q -l 1000M -P33001 -L /logs -k 1 --symbolic-links=copy -p -d \
    "/$FILESET/" "$DESTINATION"
