"""Launch the Streamlit content strategy & asset planner dashboard.

Distribution is manual: copy captions and image prompts to client approval and social tools.
"""

import subprocess
import sys
from pathlib import Path


def run() -> None:
    app_path = Path(__file__).resolve().parent / "app.py"
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path)],
        check=False,
    )


if __name__ == "__main__":
    run()
