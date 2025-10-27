# api/routers/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
clients = []

@router.websocket("/ws/payments")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep alive
    except WebSocketDisconnect:
        clients.remove(websocket)

async def broadcast_payment_status(data: dict):
    for client in clients:
        await client.send_json(data)
