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

    def __str__(self):
        return f'Event[{self.type}] from {self.dispatcher}{": " + str(self.data) if self.data else ""}'


@dataclass
class GameState:
    next_turn: int
    last_move: Move
    game_is_over: bool
    winner: int
    moves: list[Move]
    board: list[list[int]]

    def __init__(self, game: Game):
        self.next_turn = game.next_turn
        self.last_move = game.last_move
        self.game_is_over = game.is_game_over
        self.winner = game.winner
        self.moves = game.moves
        self.board = copy.deepcopy(game.board)


@dataclass
class Move:
    i: int
    j: int
    color: int


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
    inner_blank: tuple[int, int]
    direction: Direction

    @property
    def front_blank(self):
        return self.direction.front_of(*self.move_list[0])

    @property
    def rear_blank(self):
        return self.direction.rear_of(*self.move_list[-1])
