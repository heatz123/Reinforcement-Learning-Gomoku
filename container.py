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

    def front_of(self, i, j):
        return i - self.i, j - self.j

    def rear_of(self, i, j):
        return i + self.i, j + self.j


@dataclass
class Row:
    move_list: list[tuple[int, int]]
    inner_blank: None | tuple[int, int]
    direction: Direction

    @property
    def front_blank(self):
        return self.direction.front_of(*self.move_list[0])

    @property
    def rear_blank(self):
        return self.direction.rear_of(*self.move_list[-1])
