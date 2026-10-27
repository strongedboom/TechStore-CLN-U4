import sys
from pathlib import Path

# Permite importar app y cargar_csv al correr `python -m pytest` desde la raíz.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
