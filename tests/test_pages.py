import importlib.util
import json
import sqlite3
from pathlib import Path
import pytest
from app import database
from app.config import settings

spec=importlib.util.spec_from_file_location('build_pages',Path(__file__).resolve().parents[1]/'scripts/build_pages.py')
build=importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

def data():
    return ({'stations':[{'station_id':'demo','temperature_c':25}], 'updated_at':'2026-09-25T00:00:00+00:00'},
            {'forecasts':[{'regionName':'北部地區','dataDate':database.today().isoformat(),'minT':23,'maxT':30,'avgT':26.5}]})

def test_public_export_excludes_private_database_and_settings(tmp_path):
    latest,forecast=data()
    database.save_product('private-test',{'secret':'must-not-publish'},'2026-09-25T00:00:00+00:00')
    database.save_snapshot(latest['stations'],'2026-09-25T00:00:00+00:00')
    out=tmp_path/'site'
    build.export_public(out,latest,forecast,{})
    assert not (out/'.env').exists()
    assert not (out/'weather.db').exists()
    assert 'window.CWA_STATIC=true' in (out/'index.html').read_text()
    manifest=json.loads((out/'data/weather.json').read_text())
    assert manifest['latest']['stations']==latest['stations']
    for item in manifest['history']['snapshots']:
        assert (out/item['file']).is_file()
    with sqlite3.connect(out/'data/forecasts.sqlite') as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()==[('WeeklyForecasts',)]
        assert db.execute('SELECT count(*) FROM WeeklyForecasts').fetchone()[0]==1
    assert all(b'must-not-publish' not in p.read_bytes() for p in out.rglob('*') if p.is_file())

def test_empty_or_secret_snapshot_never_deploys(tmp_path,monkeypatch):
    latest,forecast=data()
    with pytest.raises(RuntimeError,match='empty'):
        build.export_public(tmp_path/'empty',{'stations':[]},forecast,{})
    monkeypatch.setattr(settings,'CWA_API_KEY','test-secret-do-not-publish')
    latest['stations'][0]['station_name']=settings.CWA_API_KEY
    with pytest.raises(RuntimeError,match='Secret'):
        build.export_public(tmp_path/'leak',latest,forecast,{})
