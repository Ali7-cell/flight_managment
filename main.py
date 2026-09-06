import os
import sys
from pathlib import Path

# Ensure backend directory and packages are in sys.path
BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"

for path in [
    str(BACKEND_DIR),
    str(BACKEND_DIR / "packages" / "flight_domain"),
    str(BASE_DIR),
]:
    if path not in sys.path:
        sys.path.insert(0, path)

from apps.api.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
