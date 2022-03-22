from __future__ import annotations
import asyncio
import dataclasses
import json
from json import JSONDecodeError
from random import shuffle

from websockets.exceptions import ConnectionClosedError

from container import GameState, Event, Placement

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from arena import Arena


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


class Agent:
    def __init__(self):
        self.arena = None
        self.color = None

    def attach_arena(self, arena: Arena, color: bool):
        self.arena = arena
        self.color = color

    def put_event(self, type: str, data: any = None):
        self.arena.put_event(Event(self, type, data))

    async def update_state(self, state: GameState):
        raise NotImplementedError()

    async def request_placement(self, state: GameState):
        raise NotImplementedError()


class PlayerAgent(Agent):
    def __init__(self, websocket):
        super(PlayerAgent, self).__init__()
        self.websocket = websocket
        asyncio.create_task(self._receive_message())

    async def _receive_message(self):
        try:
            async for message in self.websocket:
                try:
                    message = json.loads(message)
                except JSONDecodeError:
                    print(f'nonJSON Message received, ignore it: {message}')
                    continue
                # print(f'receive: {message}')
                if message['type'] == 'PLACE_STONE':
                    from arena import Arena
                    self.put_event(Arena.PLACE_STONE, Placement(
                        message['data']['i'],
                        message['data']['j'],
                        self.color,
                    ))
        except ConnectionClosedError:
            from arena import Arena
            self.put_event(Arena.GIVE_UP)

    async def _send_message(self, type: str, data: any = None, message: any = None):
        await self.websocket.send(json.dumps(dict(type=type, data=data, message=message), cls=EnhancedJSONEncoder))

    def attach_arena(self, arena: Arena, color: bool):
        super(PlayerAgent, self).attach_arena(arena, color)
        asyncio.create_task(self._send_message('NEW_GAME', dict(color=color)))

    async def update_state(self, state: GameState):
        await self._send_message('UPDATE_STATE', state)

    async def request_placement(self, state: GameState):
        await self._send_message('REQUEST_PLACEMENT', state)


class AIAgent(Agent):
    def __init__(self):
        super(AIAgent, self).__init__()

    async def update_state(self, state: GameState):
        pass

    async def request_placement(self, state: GameState):
        # TODO

        from arena import Arena
        rule = self.arena.game.rule
        max_depth = 3

        def best_placement(board: list[list[bool | None]], color: bool, depth: int):
            for i in range(len(board)):
                for j in range(len(board)):
                    p = Placement(i, j, color)
                    try:
                        if rule.will_win(board, p):
                            return p
                    except:
                        pass
            if depth == max_depth:
                return None
            _, neighbored = get_placements(board, color)
            for p in neighbored:
                i = p.i
                j = p.j
                board[i][j] = color
                if best_placement(board, not color, depth + 1) is None:
                    board[i][j] = None
                    return p
                board[i][j] = None
            return None

        def get_placements(board, color):
            available = []
            neighbored = []
            for i in range(len(board)):
                for j in range(len(board[i])):
                    try:
                        rule.will_win(board, Placement(i, j, color))
                    except:
                        continue
                    available.append(Placement(i, j, color))
                    for di, dj in ((0,1), (1,0), (0,-1), (-1,0), (1,1), (-1,1), (-1,-1), (1,-1)):
                        ii = i + di
                        jj = j + dj
                        if not (0 <= ii < len(board) and 0 <= jj < len(board[ii])):
                            continue
                        if board[ii][jj] is not None:
                            neighbored.append(Placement(i, j, color))
                            break
            return available, neighbored

        bp = best_placement(state.board, self.color, 0)
        if bp is not None:
            self.put_event(Arena.PLACE_STONE, bp)
            return

        available, neighbored = get_placements(state.board, self.color)
        if neighbored:
            shuffle(neighbored)
            self.put_event(Arena.PLACE_STONE, Placement(neighbored[0].i, neighbored[0].j, self.color))
        elif available:
            shuffle(available)
            self.put_event(Arena.PLACE_STONE, Placement(available[0].i, available[0].j, self.color))
        else:
            raise ValueError("Cannot place onto any position.")
