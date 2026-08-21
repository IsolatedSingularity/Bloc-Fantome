"""Point a frozen build at the explicitly bundled Tcl/Tk libraries."""

import os
import sys


bundle_root = getattr(sys, "_MEIPASS", "")
if bundle_root:
    os.environ["TCL_LIBRARY"] = os.path.join(bundle_root, "_tcl_data")
    os.environ["TK_LIBRARY"] = os.path.join(bundle_root, "_tk_data")
