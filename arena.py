import asyncio
import uuid
from asyncio import Queue
from random import shuffle

from agent import AIAgent, Agent
from container import GameState, Move, Event, ArenaState
from game import Game
from rule import IllegalMoveError, BLACK, WHITE, BLANK


class Arena:
    MOVE = 'MOVE'
    PASS = 'PASS'
    GIVE_UP = 'GIVE_UP'

    def __init__(self, title: str, player_num: int, allow_spectator: bool):
        self.arena_id = str(uuid.uuid4())
        self.title = title
        self.allow_spectator = allow_spectator
        self.player_num = player_num

        self.agents: list[Agent] = []
        self.spectators: list[Agent] = []

        self._event_queue = None
        self.game = Game()
        self.game_task = None

        self._try_start_game()

    @property
    def is_game_started(self):
        return self.game_task is not None

    @property
    def game_state(self):
        return GameState(self.game)

    async def _process_events(self):
        while True:
            event: Event = await self._event_queue.get()
            print(f'Process {event}')
            if event.type == Arena.MOVE:
                move: Move = event.data
                try:
                    self.game.play_move(move)
                    for agent in self.agents:
                        if self.game.is_game_over or agent.color != self.game.next_turn:
                            asyncio.create_task(agent.update_game_state(self.game_state))
                    for spectator in self.spectators:
                        asyncio.create_task(spectator.update_game_state(self.game_state))
                except IllegalMoveError as e:
                    print(e)
                if self.game.is_game_over:
                    break
                asyncio.create_task(self._get_next_agent().request_move(self.game_state))
            elif event.type == Arena.PASS:
                try:
                    self.game.pass_move(event.dispatcher.color)
                    for agent in self.agents:
                        if self.game.is_game_over or agent.color != self.game.next_turn:
                            asyncio.create_task(agent.update_game_state(self.game_state))
                    for spectator in self.spectators:
                        asyncio.create_task(spectator.update_game_state(self.game_state))
                except IllegalMoveError as e:
                    print(e)
                if self.game.is_game_over:
                    break
                asyncio.create_task(self._get_next_agent().request_move(self.game_state))
            elif event.type == Arena.GIVE_UP:
                self.game.force_win(-event.dispatcher.color)
                for spectator in self.agents + self.spectators:
                    asyncio.create_task(spectator.update_game_state(self.game_state))
                break
            else:
                pass
            self._event_queue.task_done()
        print(f'Arena[{self.arena_id}] Closed')
        self.game_task = None

    def _try_start_game(self):
        if len(self.agents) == self.player_num:
            for _ in range(2 - self.player_num):
                self._attach_agent(AIAgent())
            self._update_arena_state()
            self._start_game()

    def _get_next_agent(self):
        return next(agent for agent in self.agents if agent.color == self.game.next_turn)

    def put_event(self, event: Event):
        if self._event_queue:
            self._event_queue.put_nowait(event)

    def _attach_agent(self, agent: Agent):
        if len(self.agents) >= 2:
            raise ValueError('2 agents are attached to the arena already')
        self.agents.append(agent)
        agent.attach_arena(self)

    def attach_agent(self, agent: Agent):
        self._attach_agent(agent)
        self._try_start_game()
        self._update_arena_state()

    def detach_agent(self, agent: Agent):
        if agent.color and self.is_game_started and not self.game.is_game_over:
            self.game.force_win(-agent.color)
        self.agents.remove(agent)
        self._update_arena_state()

    def attach_spectator(self, spectator: Agent):
        if not self.allow_spectator:
            return
        self.spectators.append(spectator)
        spectator.attach_arena(self)
        if self.game_task:
            spectator.start_game(BLANK)
            asyncio.create_task(spectator.update_game_state(self.game_state))
        self._update_arena_state()

    def detach_spectator(self, spectator: Agent):
        self.spectators.remove(spectator)
        self._update_arena_state()

    def _update_arena_state(self):
        state = ArenaState(self)
        for agent in self.agents + self.spectators:
            asyncio.create_task(agent.update_arena_state(state))

    def _start_game(self):
        self._event_queue = Queue()
        shuffle(self.agents)
        colors = [BLACK, WHITE]
        for agent, color in zip(self.agents, colors):
            agent.start_game(color)
        for spectator in self.spectators:
            spectator.start_game(BLANK)
        next_agent = self._get_next_agent()
        for agent in self.agents:
            if next_agent is not agent:
                asyncio.create_task(agent.update_game_state(self.game_state))
        for spectator in self.spectators:
            asyncio.create_task(spectator.update_game_state(self.game_state))
        asyncio.create_task(next_agent.request_move(self.game_state))
        self.game_task = asyncio.create_task(self._process_events())
