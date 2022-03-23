from container import Direction, Move

BLACK = False
WHITE = True
BOARD_SIZE = 15

directions = [
    Direction(1, 0),
    Direction(0, 1),
    Direction(1, 1),
    Direction(1, -1),
]


class IllegalMoveError(ValueError):
    def __init__(self, message):
        self.message = message
        super(IllegalMoveError, self).__init__(message)

    def __str__(self):
        return f'IllegalMoveError: {self.message}'


class Rule:
    @staticmethod
    def check_valid_move(board: list[list[bool | None]], move: Move):
        if not (0 <= move.i < len(board) and 0 <= move.j < len(board[move.i])):
            raise IllegalMoveError('Out of range of board.')
        if board[move.i][move.j] is not None:
            raise IllegalMoveError('A stone exists already.')

    @staticmethod
    def will_win(board: list[list[bool | None]], move: Move):
        raise NotImplementedError()


class GomokuRule(Rule):
    @staticmethod
    def five_in_a_row(board: list[list[bool | None]], move: Move):
        i = move.i
        j = move.j
        color = move.color
        board[i][j] = color
        try:
            for d in directions:
                cnt = 0
                for k in range(-5, 6):
                    ii = i + d.i * k
                    jj = j + d.j * k
                    if not (0 <= ii < len(board) and 0 <= jj < len(board[ii])):
                        continue
                    if board[ii][jj] == color:
                        cnt += 1
                        if cnt == 5:
                            return True
                    else:
                        cnt = 0
            return False
        finally:
            board[i][j] = None

    @staticmethod
    def will_win(board: list[list[bool | None]], move: Move):
        GomokuRule.check_valid_move(board, move)
        return GomokuRule.five_in_a_row(board, move)


class RenjuRule(Rule):
    @staticmethod
    def will_win(board: list[list[bool | None]], move: Move):
        raise NotImplementedError()
