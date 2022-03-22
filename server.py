import asyncio
import sys

import websockets

from agent import PlayerAgent
from arena import PVAIArena, AIVAIArena

arenas = []


def new_arena_PVAI(websocket):
    print('new_arena PVAI')
    arena = PVAIArena(PlayerAgent(websocket))
    arena.start_game()
    return arena


async def new_arena_AIVAI():
    print('new_arena AIVAI')
    arena = AIVAIArena()
    arena.start_game()
    await arena.game_task


async def accept(websocket, path):
    arena = new_arena_PVAI(websocket)
    await arena.game_task


async def serve():
    async with websockets.serve(accept, '0.0.0.0', 5000):
        print('Server started.')
        await asyncio.Future()

if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == 'AIVAI':
        asyncio.run(new_arena_AIVAI())
    else:
        asyncio.run(serve())
