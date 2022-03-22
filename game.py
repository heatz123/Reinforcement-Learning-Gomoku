from container import Placement
from rule import GomokuRule, InvalidPlacementError


class Game:
    BLACK = False
    WHITE = True
    BOARD_SIZE = 15

    def __init__(self):
        self.winner = None
        self.board: list[list[bool | None]] = [[None for _ in range(Game.BOARD_SIZE)] for _ in range(Game.BOARD_SIZE)]
        self.placements = []
        self.next_turn = Game.BLACK
        self.is_game_over = False
        self.rule = GomokuRule()

    @property
    def last_placement(self):
        if not self.placements:
            return None
        return self.placements[-1]

    def place_stone(self, placement: Placement):
        if self.next_turn != placement.color:
            raise InvalidPlacementError('It\'s not valid turn.')
        self.is_game_over = self.rule.will_win(self.board, placement)
        self.board[placement.i][placement.j] = placement.color
        self.placements.append(placement)
        if self.is_game_over:
            self.next_turn = None
            self.winner = placement.color
        else:
            self.next_turn = not self.next_turn

    def game_over(self, winner: bool):
        self.is_game_over = True
        self.next_turn = None
        self.winner = winner

