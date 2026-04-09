"""
Pytest konfigürasyon dosyası.

src/ layout kullanıldığından, bu conftest.py src dizinini
sys.path'in BAŞINA ekler. Böylece kullanıcı seviyesinde yüklü
eski "mapindata" paketi yerine bu projenin src/mapindata'sı kullanılır.

Bu dosya pytest tarafından otomatik olarak yüklenir.
"""

import sys
from pathlib import Path

# src/ dizinini path'in BAŞINA ekle — kullanıcı site-packages'taki
# eski "mapindata" paketinden önce bu projenin src/ dizinini kullan.
srcPath = str(Path(__file__).parent / "src")
if srcPath not in sys.path:
    sys.path.insert(0, srcPath)

# Eğer eski mapindata paketi zaten önbelleğe alındıysa temizle
for key in list(sys.modules.keys()):
    if key == "mapindata" or key.startswith("mapindata."):
        del sys.modules[key]
