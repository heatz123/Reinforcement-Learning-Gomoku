import asyncio
import dataclasses
import json
import uuid
from json import JSONDecodeError

import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from websockets.legacy.server import WebSocketServerProtocol

from agent import PlayerAgent
from arena import Arena
from container import ArenaState

arenas: dict[Arena] = dict()
remove_task = dict()


def remove_arena_on_closed(arena):
    if remove_task.get(arena.arena_id) is not None:
        return

    async def remove_arena():
        await arena.game_task
        del arenas[arena.arena_id]
        del remove_task[arena.arena.id]
    remove_task[arena.arena_id] = asyncio.create_task(remove_arena())


async def attach_agent_to_arena(websocket, connection_id, arena):
    agent = PlayerAgent(websocket, connection_id)
    arena.attach_agent(agent)
    if arena.is_game_started:
        remove_arena_on_closed(arena)
    return await agent.start_receive_message()


async def attach_spectator_to_arena(websocket, connection_id, arena):
    spectator = PlayerAgent(websocket, connection_id, spectator=True)
    arena.attach_spectator(spectator)
    if arena.is_game_started:
        remove_arena_on_closed(arena)
    return await spectator.start_receive_message()


def new_arena(title, player_num, allow_spectator):
    arena = Arena(title, player_num, allow_spectator)
    if not arena.title:
        arena.title = f'Arena_{arena.arena_id[:6]}'
    arenas[arena.arena_id] = arena
    return arena


async def accept(websocket: WebSocketServerProtocol, path):
    connection_id = str(uuid.uuid4())

    def send_arena_list():
        _arenas = [dataclasses.asdict(ArenaState(_arena)) for _arena in arenas.values()]
        print(f'SERVER{connection_id[:6]} Send arena list {_arenas}')
        return websocket.send(json.dumps(dict(type='ARENA_LIST', data=dict(arenas=_arenas))))

    await send_arena_list()

    while True:
        try:
            print(f'SERVER[{connection_id[:6]}] Waiting...')
            message = await websocket.recv()
        except (ConnectionClosedOK, ConnectionClosedError):
            print(f'SERVER[{connection_id[:6]}] Closed')
            return
        try:
            message = json.loads(message)
        except JSONDecodeError:
            continue
        print(f'SERVER[{connection_id[:6]}] Received: {message["type"]} {message["data"]}')
        if message['type'] == 'CREATE_ARENA':
            title = message['data']['title']
            player_num = int(message['data']['players'])
            allow_spectator = bool(message['data']['spectator'])
            arena = new_arena(title, player_num, allow_spectator)
            print(f'Arena[{arena.arena_id[:6]}] Created')
            if not arena.is_game_started:
                return await attach_agent_to_arena(websocket, connection_id, arena)
            else:
                return await attach_spectator_to_arena(websocket, connection_id, arena)
        elif message['type'] == 'ENTER_ARENA':
            arena_id = message['data']['id']
            arena = arenas.get(arena_id)
            if arena is None:
                await send_arena_list()
                continue
            try:
                return await attach_agent_to_arena(websocket, connection_id, arena)
            except ValueError:
                await send_arena_list()
            print(f'Entered to Arena[{arena.arena_id[:6]}]')
        elif message['type'] == 'SPECTATE_ARENA':
            arena_id = message['data']['id']
            arena = arenas.get(arena_id)
            if arena is None:
                await send_arena_list()
                continue
            try:
                return await attach_spectator_to_arena(websocket, connection_id, arena)
            except ValueError:
                await send_arena_list()
            print(f'Spectate Arena[{arena.arena_id[:6]}]')
        else:
            await send_arena_list()


async def serve():
    async with websockets.serve(accept, '0.0.0.0', 5000):
        print('Server started.')
        await asyncio.Future()

if __name__ == '__main__':
    asyncio.run(serve())
