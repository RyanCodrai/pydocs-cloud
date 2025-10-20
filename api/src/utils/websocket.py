import json
from typing import AsyncIterable, Union

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, TypeAdapter


class ManagedWebSocket:
    def __init__(self, websocket: WebSocket, parsers: list[BaseModel]):
        self.websocket = websocket
        self.parsers = parsers
        # Create a TypeAdapter for the Union of the parsers
        self.WebSocketMessageAdapter = TypeAdapter(Union[tuple(parsers)])

    async def __aenter__(self):
        await self.websocket.accept()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.websocket.close()

    async def receive(self) -> BaseModel:
        try:
            raw_data = await self.websocket.receive_text()
            json_data = json.loads(raw_data)
            return self.WebSocketMessageAdapter.validate_python(json_data)
        except WebSocketDisconnect:
            pass
        except json.JSONDecodeError:
            # Handle JSON parsing errors
            raise ValueError("Invalid JSON received")
        except Exception as e:
            # Handle Pydantic validation errors
            raise ValueError(f"Invalid message format: {str(e)}")

    async def receive_all(self) -> AsyncIterable[BaseModel]:
        while True:
            obj = await self.receive()
            if obj is None:
                break
            yield obj

    async def send(self, message: BaseModel):
        try:
            await self.websocket.send_json(message.model_dump())
        except WebSocketDisconnect:
            pass
