import sys
from pathlib import Path

# Garantiza que la raíz del proyecto esté al frente de sys.path para que
# `import etl` resuelva al paquete raíz y no a tests/etl/.
sys.path.insert(0, str(Path(__file__).parent))
