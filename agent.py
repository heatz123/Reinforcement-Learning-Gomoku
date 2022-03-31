from __future__ import annotations
import asyncio
import dataclasses
import json
import re
from concurrent.futures import ThreadPoolExecutor
from json import JSONDecodeError

from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from container import GameState, Event, Move, ArenaState, Row

from typing import TYPE_CHECKING

from rule import name_of, BLACK, BLANK

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
        if state.last_move is None:
            self.put_event(Arena.MOVE, Move(len(state.board) // 2, len(state.board[len(state.board) // 2]) // 2, self.color))
            return
        with ThreadPoolExecutor() as pool:
            loop = asyncio.get_running_loop()
            type, data = await loop.run_in_executor(pool, self._calc_best_move, state.board, self.arena.game.rule)
        self.put_event(type, data)

    def _calc_best_move(self, board, rule, max_depth=4):
        score_length = 6

        def initial_score():
            return [0] * score_length

        def extended_initial_score():
            return [0] * max_depth + initial_score()

        extended_zero_score = tuple(extended_initial_score())

        def max_score(depth=max_depth):
            score = extended_initial_score()
            for i in range(max_depth-depth, len(score)):
                score[i] = 1
            return tuple(score)

        def min_score(depth=max_depth):
            score = extended_initial_score()
            for i in range(max_depth-depth, len(score)):
                score[i] = -1
            return tuple(score)

        def get_score(board, last_move):
            """
            score(BLACK) - score(WHITE)
            """

            if last_move is None:
                return tuple(initial_score())
            color = last_move.color

            def get_rows(color):
                twos: dict[tuple, Row] = dict()
                threes: dict[tuple, Row] = dict()
                fours: dict[tuple, Row] = dict()
                for i in range(len(board)):
                    for j in range(len(board[i])):
                        if board[i][j] != color:
                            continue
                        move = Move(i, j, color)
                        _twos, _threes, _fours = rule.get_rows(board, move)
                        for row in _twos:
                            key = tuple(row.move_list)
                            twos[key] = row
                        for row in _threes:
                            key = tuple(row.move_list)
                            threes[key] = row
                        for row in _fours:
                            key = tuple(row.move_list)
                            fours[key] = row
                return twos, threes, fours

            def get_this_score(color):
                if rule.is_win(board, last_move):
                    return (1,) * score_length
                this_score = initial_score()
                this_twos, this_threes, this_fours = get_rows(color)
                for row in this_twos.values():
                    this_score[-1] += 1
                cnt_open_three = 0
                for row in this_threes.values():
                    if not rule.is_explicitly_closed_three(board, row, color) and rule.is_open_three(board, row, color):
                        this_score[-1] += 100
                        cnt_open_three += 1
                    elif rule.is_half_open_three(board, row, color):
                        this_score[-1] += 10
                cnt_four = 0
                cnt_open_four = 0
                for row in this_fours.values():
                    if rule.is_four(board, row, color):
                        this_score[-1] += 150
                        cnt_four += 1
                        if rule.is_open_four(board, row, color):
                            cnt_open_four += 1
                if color == BLACK:
                    if cnt_open_four >= 1:
                        this_score[2] = 1
                    if cnt_open_three == 1 and cnt_four == 1:
                        this_score[4] = 1
                else:
                    if cnt_open_four >= 1 or cnt_open_three + cnt_four >= 2:
                        if cnt_open_four >= 1 or cnt_four >= 2:
                            this_score[2] = 1
                        else:
                            this_score[4] = 1
                return tuple(this_score)

            def get_next_score(color):
                next_score = initial_score()
                next_twos, next_threes, next_fours = get_rows(color)
                next_score[-1] += len(next_twos)
                cnt_open_three = 0
                for row in next_threes.values():
                    if rule.is_half_open_three(board, row, color):
                        next_score[-1] += 100
                    if not rule.is_explicitly_closed_three(board, row, color) and rule.is_open_three(board, row, color):
                        cnt_open_three += 1
                cnt_four = 0
                for row in next_fours.values():
                    if rule.is_four(board, row, -color):
                        cnt_four += 1
                if cnt_open_three >= 1:
                    next_score[3] = 1
                if cnt_four >= 1:
                    next_score[1] = 1
                return tuple(next_score)

            score = tuple(map(lambda x: color * (x[0] - x[1]), zip(get_this_score(color), get_next_score(-color))))
            return score

        memo = dict()

        def alphabeta(board: list[list[int]], depth, a, b, turn: int, last_move: Move):
            nonlocal max_depth
            board_string = ''.join(''.join(str(c) for c in row) for row in board)
            if board_string in memo:
                return memo[board_string]
            if last_move is not None and rule.is_win(board, last_move):
                memo[board_string] = None, max_score(depth) if last_move.color == BLACK else min_score(depth)
                return memo[board_string]
            if depth == 0:
                memo[board_string] = None, (0,) * max_depth + get_score(board, last_move)
                return memo[board_string]

            pos_list = []
            for i in range(len(board)):
                for j in range(len(board[i])):
                    move = Move(i, j, turn)
                    if not rule.is_legal_move(board, move):
                        continue
                    min_dst = 9999
                    for ii in range(len(board)):
                        for jj in range(len(board[ii])):
                            if board[ii][jj] != BLANK:
                                min_dst = min(min_dst, max(abs(i - ii), abs(j - jj)))
                                if min_dst <= 1:
                                    break
                        if min_dst <= 1:
                            break
                    if min_dst > 2:
                        continue
                    board[i][j] = turn
                    score = get_score(board, move)
                    board[i][j] = BLANK
                    pos_list.append((i, j, (score, -turn * min_dst)))

            if depth != 0:
                pos_list.sort(key=lambda p: p[2], reverse=turn == BLACK)
            if depth == max_depth:
                print(pos_list)

            original_index = None
            pos = None
            expected = None
            v = min_score() if turn == BLACK else max_score()
            index = 0

            while index < len(pos_list):
                i, j , _ = pos_list[index]
                move = Move(i, j, turn)

                board[i][j] = turn
                e, sv = alphabeta(board, depth - 1, a, b, -turn, move)
                if depth == max_depth:
                    print(i, j, f'{index+1}/{len(pos_list)}', sv)
                board[i][j] = BLANK

                if (v < sv) if turn == BLACK else (v > sv):
                    original_index = index
                    expected = e
                    pos = (i, j)
                    v = sv

                # pruning
                if turn == BLACK:
                    a = max(a, v)
                else:
                    b = min(b, v)
                if b <= a:
                    break

                # search more if it will lose
                index += 1
                if index >= 10 and (depth != max_depth or ((v[:-1] >= extended_zero_score[:-1]) if turn == BLACK else (v[:-1] <= extended_zero_score[:-1]))):
                    break

            if depth == max_depth:
                print(f'Rank {original_index}/{len(pos_list)}', original_index / len(pos_list))
                print(f'Best {pos}, expect {expected}: {v}')
            memo[board_string] = pos, v
            return memo[board_string]

        pos, v = alphabeta(board, max_depth, min_score(), max_score(), self.color, None)
        from arena import Arena
        if pos is not None:
            return Arena.MOVE, Move(*pos, self.color)
        else:
            return Arena.PASS, None
