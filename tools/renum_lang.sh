#!/bin/bash

SCRIPT_DIR=$(dirname $(readlink -f $0))
ROOT_DIR=$(readlink "$SCRIPT_DIR/..")

FROM_ID=$1
TO_ID=$2

if ! [[ "$FROM_ID" =~ 30[[:digit:]]{3} ]]; then
    echo "Invalid source id: $FROM_ID"
    exit 1
fi
echo "Source id: $FROM_ID"

if ! [[ "$TO_ID" =~ 30[[:digit:]]{3} ]]; then
    echo "Invalid destination id: $TO_ID"
    exit 1
fi
echo "Destination id: $TO_ID"

FILES=$(grep -r -E "$FROM_ID" "$ROOT_DIR/plugin.video.crunchyroll" | awk -F ":" '{ print $1}')
for file in "${FILES[@]}"; do
    sed -i "s/$FROM_ID/$TO_ID/g" $file
done
