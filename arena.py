import asyncio
import uuid
from asyncio import Queue
from random import shuffle

from agent import AIAgent, Agent, PlayerAgent
from container import GameState, Placement, Event
from game import Game
from rule import InvalidPlacementError


class Arena:
    PLACE_STONE = 'PLACE_STONE'
    GIVE_UP = 'GIVE_UP'

    def __init__(self):
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
            if event.type == Arena.PLACE_STONE:
                placement: Placement = event.data
                try:
                    self.game.place_stone(placement)
                    for agent in self.agents:
                        if self.game.is_game_over or agent.color != self.game.next_turn:
                            asyncio.create_task(agent.update_state(self.game_state))
                except InvalidPlacementError as e:
                    print(e)
                if self.game.is_game_over:
                    break
                asyncio.create_task(self.agents[self.game.next_turn].request_placement(self.game_state))
            elif event.type == Arena.GIVE_UP:
                # TODO
                self.game.game_over(event.dispatcher.color)
                break
            else:
                pass
            self._event_queue.task_done()

    def _init_event_loop(self):
        self._event_queue = Queue()
        self.game_task = asyncio.create_task(self.process_events())

    def put_event(self, event: Event):
        self._event_queue.put_nowait(event)

    def populate_agents(self):
        raise NotImplementedError()

    def start_game(self):
        self.populate_agents()
        shuffle(self.agents)
        for index, agent in enumerate(self.agents):
            agent.attach_arena(self, bool(index))
        self._init_event_loop()
        for agent in self.agents:
            asyncio.create_task(agent.update_state(self.game_state))
        asyncio.create_task(self.agents[self.game.next_turn].request_placement(self.game_state))


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
