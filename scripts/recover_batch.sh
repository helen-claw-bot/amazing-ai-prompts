#!/usr/bin/env bash
set -e

BASE="E://AI//downloads//CHTT2"
SIM=0.3

for ep in $(seq -f "%02g" 18 32); do
    DIR="${BASE}//S01E${ep}_faces"
    echo "========================================"
    echo "  S01E${ep}_faces"
    echo "========================================"
    python scripts/recover_skipped_frames.py --dir "$DIR" --sim $SIM
done

echo ""
echo "✅ 全部完成 (E18 - E32)"
