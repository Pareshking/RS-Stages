"""Production entrypoint for the RS-Stages quantitative research platform.

Streamlit reruns the entrypoint script on widget interaction. ``app_v7`` is
an executable presentation module (it renders the selected page at import
time), so a plain ``from app_v7 import *`` is unsafe: after the first run the
module can remain cached in ``sys.modules`` and a rerun can execute no page
rendering at all. Reload it explicitly on every Streamlit run.
"""
import importlib

import app_v7

importlib.reload(app_v7)
