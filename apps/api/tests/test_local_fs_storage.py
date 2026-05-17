from pathlib import Path

import pytest

from research_api.services.storage import LocalFsStorage, StorageRef


@pytest.mark.asyncio
async def test_save_returns_storage_ref_with_user_scoped_key(tmp_path: Path):
    s = LocalFsStorage(root=tmp_path, signing_secret="x")
    ref = await s.save("user-a", "articles", "paper.pdf", b"hello")
    assert ref.backend == "local"
    assert ref.key.startswith("user-a/articles/")
    assert ref.key.endswith("/paper.pdf")
    on_disk = tmp_path / "files" / ref.key
    assert on_disk.exists()
    assert on_disk.read_bytes() == b"hello"


@pytest.mark.asyncio
async def test_save_normalises_filename_blocks_traversal(tmp_path: Path):
    s = LocalFsStorage(root=tmp_path, signing_secret="x")
    ref = await s.save("user-a", "articles", "../../etc/passwd", b"x")
    # Filename is just the basename, no traversal escapes
    assert "passwd" in ref.key
    assert ".." not in ref.key
    # File is under root/files
    on_disk = tmp_path / "files" / ref.key
    assert on_disk.exists()


@pytest.mark.asyncio
async def test_save_scoped_per_user(tmp_path: Path):
    s = LocalFsStorage(root=tmp_path, signing_secret="x")
    r1 = await s.save("user-a", "articles", "x.pdf", b"a")
    r2 = await s.save("user-b", "articles", "x.pdf", b"b")
    assert r1.key.split("/")[0] == "user-a"
    assert r2.key.split("/")[0] == "user-b"
    assert await s.read(r1) == b"a"
    assert await s.read(r2) == b"b"


@pytest.mark.asyncio
async def test_read_and_delete_roundtrip(tmp_path: Path):
    s = LocalFsStorage(root=tmp_path, signing_secret="x")
    ref = await s.save("u", "a", "f.pdf", b"data")
    assert await s.read(ref) == b"data"
    await s.delete(ref)
    on_disk = tmp_path / "files" / ref.key
    assert not on_disk.exists()
    # Delete on missing file is silent
    await s.delete(ref)


@pytest.mark.asyncio
async def test_signed_url_includes_url_prefix(tmp_path: Path):
    s = LocalFsStorage(root=tmp_path, signing_secret="secret", url_prefix="/files")
    ref = StorageRef(backend="local", key="u/a/123/x.pdf")
    url = await s.signed_url(ref, expires_in=60)
    assert url.startswith("/files/")
    assert len(url) > len("/files/")  # token attached


@pytest.mark.asyncio
async def test_read_rejects_path_traversal_in_key(tmp_path: Path):
    s = LocalFsStorage(root=tmp_path, signing_secret="x")
    bad = StorageRef(backend="local", key="../escape.txt")
    with pytest.raises(ValueError, match="traversal"):
        await s.read(bad)
