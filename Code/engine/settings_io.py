"""Atomic small JSON settings writes, with unique same-directory staging files."""
import json
import os
from pathlib import Path
import tempfile


def write_json_atomic(path,payload):
    """Replace settings only after serialization and flush both succeed."""
    path=Path(path);temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,
                prefix=path.name+'.',suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name)
            json.dump(payload,stream,indent=2,allow_nan=False)
            stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
