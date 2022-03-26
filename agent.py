from __future__ import annotations
import asyncio
import dataclasses
import json
import re
from json import JSONDecodeError

from websockets.exceptions import ConnectionClosedError

from container import GameState, Event, Move

from typing import TYPE_CHECKING

from rule import name_of

if TYPE_CHECKING:
    from arena import Arena


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            new_dict = dict()
            for key, value in dataclasses.asdict(o).items():
                new_key = re.sub('_([a-z|0-9])', lambda pat: pat.group(1).upper(), key)
                new_dict[new_key] = value
            return new_dict
        return super().default(o)


class Agent:
    def __init__(self):
        self.arena = None
        self.color = None

    def attach_arena(self, arena: Arena, color: int):
        self.arena = arena
        self.color = color

    def put_event(self, type: str, data: any = None):
        self.arena.put_event(Event(self, type, data))

    async def update_state(self, state: GameState):
        raise NotImplementedError()

    async def request_move(self, state: GameState):
        raise NotImplementedError()

    def __str__(self):
        return f'{self.__class__.__name__} {name_of(self.color)}'


class PlayerAgent(Agent):
    def __init__(self, websocket):
        super(PlayerAgent, self).__init__()
        self.websocket = websocket
        asyncio.create_task(self._receive_message())

    async def _receive_message(self):
        from arena import Arena
        try:
            async for message in self.websocket:
                try:
                    message = json.loads(message)
                except JSONDecodeError:
                    print(f'nonJSON Message received, ignore it: {message}')
                    continue
                # print(f'receive: {message}')
                if message['type'] == 'MOVE':
                    self.put_event(Arena.MOVE, Move(
                        message['data']['i'],
                        message['data']['j'],
                        self.color,
                    ))
                elif message['type'] == 'PASS':
                    self.put_event(Arena.PASS)
        except ConnectionClosedError:
            self.put_event(Arena.GIVE_UP)

    async def _send_message(self, type: str, data: any = None, message: any = None):
        await self.websocket.send(json.dumps(dict(type=type, data=data, message=message), cls=EnhancedJSONEncoder))

    def attach_arena(self, arena: Arena, color: int):
        super(PlayerAgent, self).attach_arena(arena, color)
        asyncio.create_task(self._send_message('NEW_GAME', dict(color=color)))

    async def update_state(self, state: GameState):
        await self._send_message('UPDATE_STATE', state)

    async def request_move(self, state: GameState):
        await self._send_message('REQUEST_MOVE', state)


class AIAgent(Agent):
    def __init__(self):
        super(AIAgent, self).__init__()

    async def update_state(self, state: GameState):
        pass

    async def request_move(self, state: GameState):
        from arena import Arena
        self.put_event(Arena.PASS)
