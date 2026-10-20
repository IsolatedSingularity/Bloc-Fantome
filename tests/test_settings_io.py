"""Settings persistence must retain a complete recovery point on write failure."""
import json
from unittest.mock import Mock
import pytest
import blocFantome as module


@pytest.mark.parametrize('failure',['serialize','replace'])
def test_failed_app_config_write_retains_previous_json(tmp_path,monkeypatch,failure):
    path=tmp_path/'preferences.json';original=b'{"retained":true}'
    path.write_bytes(original);monkeypatch.setattr(module,'APP_CONFIG_FILE',str(path))
    app=module.BlocFantome()
    try:
        if failure=='serialize':monkeypatch.setattr(json,'dump',Mock(side_effect=OSError('write failed')))
        else:monkeypatch.setattr('os.replace',Mock(side_effect=OSError('replacement failed')))
        app._saveAppConfig()
        assert path.read_bytes()==original
        assert sorted(p.name for p in tmp_path.iterdir())==['preferences.json']
    finally:app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True)
