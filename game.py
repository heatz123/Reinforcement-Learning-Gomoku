from container import Move
from rule import IllegalMoveError, BOARD_SIZE, BLACK, BLANK, Rule, GomokuRule, RenjuRule, WHITE


class Game:
    def __init__(self):
        self.winner = None
        self.board: list[list[int]] = [[BLANK for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.moves = []
        self.next_turn = BLACK
        self.is_game_over = False
        self.rule: Rule = RenjuRule()

    @property
    def last_move(self):
        if not self.moves:
            return None
        return self.moves[-1]

    def play_move(self, move: Move):
        if self.next_turn != move.color:
            raise IllegalMoveError('It\'s not valid turn.')
        self.rule.is_legal_move(self.board, move, raise_exception=True)
        self.board[move.i][move.j] = move.color
        self.moves.append(move)
        self.is_game_over = self.rule.is_win(self.board, move)
        if self.is_game_over:
            self.next_turn = None
            self.winner = move.color
        else:
            self.next_turn = -self.next_turn

    def pass_move(self, color: int):
        if self.next_turn != color:
            raise IllegalMoveError('It\'s not valid turn.')
        if (self.last_move and self.last_move.color == self.next_turn) or (not self.last_move and self.next_turn == WHITE):
            self.is_game_over = True
        else:
            self.next_turn = -self.next_turn

    def force_win(self, winner: int):
        self.is_game_over = True
        self.next_turn = None
        self.winner = winner
