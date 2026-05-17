import pytest


@pytest.mark.asyncio
async def test_writing_assist_improve(client):
    r = await client.post(
        "/api/writing/assist",
        json={"action": "improve", "text": "Anterior approach was used."},
    )
    assert r.status_code == 200
    body = r.json()
    # FakeAIProvider returns '[improve] Anterior approach was used.'
    assert "[improve]" in body["revised"]
    assert "Anterior approach was used." in body["revised"]


@pytest.mark.asyncio
async def test_writing_assist_preserves_cite_tokens(client):
    r = await client.post(
        "/api/writing/assist",
        json={
            "action": "shorten",
            "text": "Anterior was faster [CITE_a1] and easier [CITE_a2].",
        },
    )
    assert r.status_code == 200
    revised = r.json()["revised"]
    # Both CITE tokens must round-trip
    assert "[CITE_a1]" in revised
    assert "[CITE_a2]" in revised


@pytest.mark.asyncio
async def test_writing_assist_empty_text_422(client):
    r = await client.post(
        "/api/writing/assist", json={"action": "improve", "text": ""}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_writing_assist_invalid_action_422(client):
    r = await client.post(
        "/api/writing/assist", json={"action": "rewriteEverything", "text": "Some text."}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["improve", "shorten", "formalise", "add_transition"])
async def test_writing_assist_all_four_actions(client, action):
    r = await client.post(
        "/api/writing/assist", json={"action": action, "text": "Patients improved over time."}
    )
    assert r.status_code == 200
    assert f"[{action}]" in r.json()["revised"]
