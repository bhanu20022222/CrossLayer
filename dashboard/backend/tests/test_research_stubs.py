from auth_test_utils import authenticated_test_client

client = authenticated_test_client()


def test_decision_stub_is_empty():
    res = client.get("/api/v1/decisions")
    assert res.status_code == 200
    body = res.json()
    assert body["value_kind"] == "unavailable"
    assert body["data"]["recommendations"] == []


def test_twin_stub_is_empty():
    res = client.get("/api/v1/twin/state")
    assert res.status_code == 200
    body = res.json()
    assert body["data"]["nodes"] == []
    assert body["value_kind"] == "unavailable"
