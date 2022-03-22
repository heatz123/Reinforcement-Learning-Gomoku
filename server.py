import asyncio

import websockets

from agent import PlayerAgent
from arena import PVAIArena

arenas = []


def new_arena(websocket):
    print('new_arena Player vs. AI')
    arena = PVAIArena(PlayerAgent(websocket))
    arenas.append(arena)
    return arena.start_game()


async def accept(websocket, path):
    await new_arena(websocket)


async def serve():
    async with websockets.serve(accept, '0.0.0.0', 5000):
        print('Server started.')
        await asyncio.Future()

if __name__ == '__main__':
    asyncio.run(serve())
