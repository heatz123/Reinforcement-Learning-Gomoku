from __future__ import annotations
import copy
from dataclasses import dataclass

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from agent import Agent
    from game import Game


@dataclass
class Event:
    dispatcher: Agent
    type: str
    data: any


@dataclass
class GameState:
    next_turn: bool
    last_placement: Placement
    winner: [bool | None]
    board: list[list[bool | None]]

    def __init__(self, game: Game):
        self.next_turn = game.next_turn
        self.last_placement = game.last_placement
        self.winner = game.winner
        self.board = copy.deepcopy(game.board)


@dataclass
class Placement:
    i: int
    j: int
    color: bool


@dataclass
class Direction:
    i: int
    j: int
