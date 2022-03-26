import asyncio
import uuid
from asyncio import Queue
from random import shuffle

from agent import AIAgent, Agent, PlayerAgent
from container import GameState, Move, Event
from game import Game
from rule import IllegalMoveError, BLACK, WHITE


class Arena:
    MOVE = 'MOVE'
    PASS = 'PASS'
    GIVE_UP = 'GIVE_UP'

    def __init__(self):
        self._event_queue = None
        self.game = Game()
        self.arena_id = uuid.uuid4()
        self.agents: list[Agent] = []

    @property
    def game_state(self):
        return GameState(self.game)

    async def process_events(self):
        while True:
            event: Event = await self._event_queue.get()
            print(f'Process {event}')
            if event.type == Arena.MOVE:
                move: Move = event.data
                try:
                    self.game.play_move(move)
                    for agent in self.agents:
                        if self.game.is_game_over or agent.color != self.game.next_turn:
                            asyncio.create_task(agent.update_state(self.game_state))
                except IllegalMoveError as e:
                    print(e)
                if self.game.is_game_over:
                    break
                asyncio.create_task(self.get_next_agent().request_move(self.game_state))
            elif event.type == Arena.PASS:
                try:
                    self.game.pass_move(event.dispatcher.color)
                    for agent in self.agents:
                        if self.game.is_game_over:
                            asyncio.create_task(agent.update_state(self.game_state))
                except IllegalMoveError as e:
                    print(e)
                if self.game.is_game_over:
                    break
                asyncio.create_task(self.get_next_agent().request_move(self.game_state))
            elif event.type == Arena.GIVE_UP:
                # TODO
                self.game.force_win(not event.dispatcher.color)
                break
            else:
                pass
            self._event_queue.task_done()

    def get_next_agent(self):
        return next(agent for agent in self.agents if agent.color == self.game.next_turn)

    def put_event(self, event: Event):
        self._event_queue.put_nowait(event)

    def populate_agents(self):
        raise NotImplementedError()

    def start_game(self):
        self.populate_agents()
        shuffle(self.agents)
        colors = [BLACK, WHITE]
        for agent, color in zip(self.agents, colors):
            agent.attach_arena(self, color)
        self._event_queue = Queue()
        for agent in self.agents:
            asyncio.create_task(agent.update_state(self.game_state))
        asyncio.create_task(self.get_next_agent().request_move(self.game_state))
        return asyncio.create_task(self.process_events())


class PVAIArena(Arena):
    def __init__(self, player_agent: PlayerAgent):
        super().__init__()
        self.player_agent = player_agent

    def populate_agents(self):
        self.agents.append(self.player_agent)
        self.agents.append(AIAgent())


class AIVAIArena(Arena):
    def __init__(self):
        super().__init__()

    def populate_agents(self):
        self.agents.append(AIAgent())
        self.agents.append(AIAgent())
