#!/usr/bin/env bash
# Example CLI usage. Export OPENROUTER_API_KEY first.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 main.py --classify "Hola Sergio, recibido! Cualquier novedad te aviso."
echo
python3 main.py --classify "Could you share your salary expectations?"
echo
python3 main.py --demo
