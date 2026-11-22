import json

from app.service import ensure_data_files, LEGACY_DEFAULTS, MANIFEST
from conftest import ROOT


def make_defaults(tmp_path, content="v1"):
    d = tmp_path / "defaults"
    d.mkdir(exist_ok=True)
    for n in ("config", "skills", "ranks", "titles", "system_messages"):
        (d / f"{n}.json").write_text(json.dumps({"v": content, "n": n}))
    return d


def test_first_start_installs_everything(tmp_path):
    d, data = make_defaults(tmp_path), tmp_path / "data"
    log = ensure_data_files(data, d)
    assert len(log) == 5 and (data / "skills.json").exists() and (data / MANIFEST).exists()


def test_untouched_file_is_updated(tmp_path):
    data = tmp_path / "data"
    ensure_data_files(data, make_defaults(tmp_path, "v1"))
    log = ensure_data_files(data, make_defaults(tmp_path, "v2"))
    assert json.loads((data / "skills.json").read_text())["v"] == "v2"
    assert "skills: mis à jour" in log


def test_edited_file_is_kept(tmp_path):
    data = tmp_path / "data"
    ensure_data_files(data, make_defaults(tmp_path, "v1"))
    (data / "config.json").write_text('{"mine": true}')
    log = ensure_data_files(data, make_defaults(tmp_path, "v2"))
    assert json.loads((data / "config.json").read_text()) == {"mine": True}
    assert json.loads((data / "config.nouveau.json").read_text())["v"] == "v2"
    assert any(line.startswith("config: modifié") for line in log)
    assert json.loads((data / "skills.json").read_text())["v"] == "v2"


def test_phase1_files_without_manifest_are_updated(tmp_path):
    """Volumes created before the manifest existed: a known phase-1 file counts as untouched."""
    data = tmp_path / "data"
    data.mkdir()
    legacy = data / "skills.json"
    legacy.write_bytes(b"phase1")
    import hashlib
    LEGACY_DEFAULTS["skills"].add(hashlib.sha256(b"phase1").hexdigest())
    ensure_data_files(data, make_defaults(tmp_path, "v2"))
    assert json.loads(legacy.read_text())["v"] == "v2"


def test_same_dir_is_a_no_op():
    assert ensure_data_files(ROOT / "data", ROOT / "data") == []
