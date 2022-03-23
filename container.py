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
    last_move: Move
    winner: [bool | None]
    moves: list[Move]
    board: list[list[bool | None]]

    def __init__(self, game: Game):
        self.next_turn = game.next_turn
        self.last_move = game.last_move
        self.winner = game.winner
        self.moves = game.moves
        self.board = copy.deepcopy(game.board)


@dataclass
class Move:
    i: int
    j: int
    color: bool


@dataclass
class Direction:
    i: int
    j: int
