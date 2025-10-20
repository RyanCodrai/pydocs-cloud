from fastapi.testclient import TestClient

from src.main import application

client = TestClient(application)


def test_async_task():
    response = client.post(
        "/api/v1/async_task",
        json={"request_id": "bf1b20f3-8108-4b26-a09e-81bbee110c23"},
    )
    assert response.status_code == 201
    assert response.json() == {"request_id": "bf1b20f3-8108-4b26-a09e-81bbee110c23"}


def test_sync_task():
    response = client.post(
        "/api/v1/sync_task", json={"request_id": "bf1b20f3-8108-4b26-a09e-81bbee110c23"}
    )
    assert response.status_code == 200
    assert response.json() == {
        "request_id": "bf1b20f3-8108-4b26-a09e-81bbee110c23",
        "data": "Dummy Endpoint.",
    }


def test_websocket_endpoint():
    with client.websocket_connect("/api/v1/ws") as websocket:
        # Test sending and receiving a message
        test_message = {"event_type": "init_conneciton", "content": "Hello, WebSocket!"}
        websocket.send_json(test_message)
        response = websocket.receive_json()
        test_message = {"event_type": "action", "data": "Hello, WebSocket!"}
        websocket.send_json(test_message)
        response = websocket.receive_json()
        assert response == test_message
