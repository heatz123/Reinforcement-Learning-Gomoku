from __future__ import annotations
import asyncio
import dataclasses
import json
import re
from json import JSONDecodeError

from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from container import GameState, Event, Move, ArenaState

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

    def attach_arena(self, arena: Arena):
        self.arena = arena

    def put_event(self, type: str, data: any = None):
        self.arena.put_event(Event(self, type, data))

    def start_game(self, color: int):
        self.color = color

    async def update_arena_state(self, state: ArenaState):
        pass

    async def update_game_state(self, state: GameState):
        pass

    async def request_move(self, state: GameState):
        raise NotImplementedError()

    def __str__(self):
        return f'{self.__class__.__name__} {name_of(self.color)}'


class PlayerAgent(Agent):
    def __init__(self, websocket, connection_id, spectator=False):
        super(PlayerAgent, self).__init__()
        self.websocket = websocket
        self.connection_id = connection_id
        self.spectator = spectator
        if spectator:
            self.color = 0

    def start_receive_message(self):
        return self._receive_message()

    async def _receive_message(self):
        from arena import Arena
        try:
            async for message in self.websocket:
                if self.spectator:
                    print('Ignore message from spectator')
                    continue
                try:
                    message = json.loads(message)
                except JSONDecodeError:
                    print(f'nonJSON Message received, ignore it: {message}')
                    continue
                print(f'AGENT[{self.connection_id[:6]}] Received: {message}')
                if message['type'] == 'MOVE':
                    self.put_event(Arena.MOVE, Move(
                        message['data']['i'],
                        message['data']['j'],
                        self.color,
                    ))
                elif message['type'] == 'PASS':
                    self.put_event(Arena.PASS)
        except (ConnectionClosedOK, ConnectionClosedError):
            if not self.spectator:
                self.put_event(Arena.GIVE_UP)
                self.arena.detach_agent(self)
            else:
                self.arena.detach_spectator(self)
        print(f'AGENT[{self.connection_id[:6]}] Disconnected')

    async def _send_message(self, type: str, data: any = None, message: any = None):
        try:
            await self.websocket.send(json.dumps(dict(type=type, data=data, message=message), cls=EnhancedJSONEncoder))
        except (ConnectionClosedOK, ConnectionClosedError):
            pass

    def start_game(self, color: int):
        super().start_game(color)
        asyncio.create_task(self._send_message('START_GAME', dict(color=color)))

    async def update_arena_state(self, state: ArenaState):
        await self._send_message('ARENA_STATE', state)

    async def update_game_state(self, state: GameState):
        await self._send_message('GAME_STATE', state)

    async def request_move(self, state: GameState):
        await self._send_message('REQUEST_MOVE', state)


class AIAgent(Agent):
    def __init__(self):
        super(AIAgent, self).__init__()

    async def request_move(self, state: GameState):
        from arena import Arena
        await asyncio.sleep(0.5)
        for i in range(len(state.board)):
            for j in range(len(state.board[i])):
                move = Move(i, j, self.color)
                if self.arena.game.rule.is_legal_move(state.board, move):
                    self.put_event(Arena.MOVE, move)
                    return
        self.put_event(Arena.PASS)
