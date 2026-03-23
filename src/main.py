"""Launch the Streamlit content strategy & asset planner dashboard.

Local:  `uv run python src/main.py`  → spawns `streamlit run src/app.py`
Cloud:  Streamlit runs `streamlit run src/main.py` → we exec `app.py` in-process (no nested server).
"""

from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path

_APP = Path(__file__).resolve().parent / "app.py"


def _run_streamlit_app() -> None:
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(_APP)],
        check=False,
    )


if __name__ == "__main__":
    # When Cloud (or CLI) runs `streamlit run src/main.py`, Streamlit is already imported.
    # Do not spawn a second Streamlit process — run the real app file in-process.
    if "streamlit" in sys.modules:
        runpy.run_path(str(_APP), run_name="__main__")
    else:
        _run_streamlit_app()
