"""Read-back voice fetching (poesia.voices), without the network."""

from pathlib import Path

import pytest

from poesia import voices


def _fake_download(calls: list[str]):
    def retrieve(url: str, dest: Path) -> None:
        calls.append(url)
        Path(dest).write_bytes(b"x")

    return retrieve


def test_fetch_downloads_config_and_model_per_voice(tmp_path, monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(voices.urllib.request, "urlretrieve", _fake_download(calls))
    voices.fetch(tmp_path, say=lambda _msg: None)
    assert len(calls) == 2 * len(voices.VOICES)
    assert all(voices.VOICES_REV in url for url in calls)
    assert voices.missing(tmp_path) == []
    assert not list(tmp_path.rglob("*.part"))  # finished files only, under their final name


def test_fetch_skips_what_is_there(tmp_path, monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(voices.urllib.request, "urlretrieve", _fake_download(calls))
    voices.fetch(tmp_path, say=lambda _msg: None)
    calls.clear()
    voices.fetch(tmp_path, say=lambda _msg: None)
    assert calls == []


def test_missing_lists_absent_voices(tmp_path):
    assert sorted(voices.missing(tmp_path)) == sorted(voices.VOICES.values())


@pytest.mark.parametrize(
    ("platform", "env", "expected_tail"),
    [
        ("linux", {"XDG_DATA_HOME": "/data"}, Path("/data/poesia/piper")),
        ("win32", {"LOCALAPPDATA": "C:/Users/a/AppData/Local"}, Path("poesia/piper")),
    ],
)
def test_user_voice_dir(monkeypatch, platform, env, expected_tail):
    monkeypatch.setattr(voices.sys, "platform", platform)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    assert voices.user_voice_dir().as_posix().endswith(expected_tail.as_posix())
