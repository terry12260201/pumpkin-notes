#!/bin/bash
cd "$(dirname "$0")"
echo "整理主機啟動中（關掉這個視窗就停）…"
python3 worker.py
read -r -p "已停止，按 Enter 關閉…"
