from app.envelope import envelope, unavailable


def test_envelope_marks_measured_prometheus():
    body = envelope(source="prometheus", value_kind="measured", data={"series": []})
    assert body["source"] == "prometheus"
    assert body["value_kind"] == "measured"
    assert body["error"] is None
    assert body["data"]["series"] == []


def test_unavailable_does_not_invent_values():
    body = unavailable("prometheus", "connection refused", data={"series": []})
    assert body["value_kind"] == "unavailable"
    assert body["data"]["series"] == []
    assert "0.745" not in str(body)
