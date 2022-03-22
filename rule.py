from container import Direction, Placement

directions = [
    Direction(1, 0),
    Direction(0, 1),
    Direction(1, 1),
    Direction(1, -1),
]


class InvalidPlacementError(ValueError):
    def __init__(self, message):
        self.message = message
        super(InvalidPlacementError, self).__init__(message)

    def __str__(self):
        return f'InvalidPlacementError: {self.message}'


class Rule:
    @staticmethod
    def five_in_a_row(board: list[list[bool | None]], placement: Placement):
        i = placement.i
        j = placement.j
        color = placement.color
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
    def _check_valid_placement(board: list[list[bool | None]], placement: Placement):
        if not (0 <= placement.i < len(board)):
            raise InvalidPlacementError('Out of range of board.')
        if not (0 <= placement.j < len(board[placement.i])):
            raise InvalidPlacementError('Out of range of board.')
        if board[placement.i][placement.j] is not None:
            raise InvalidPlacementError('A stone exists already.')

    @staticmethod
    def will_win(board: list[list[bool | None]], placement: Placement):
        raise NotImplementedError()


class GomokuRule(Rule):
    @staticmethod
    def will_win(board: list[list[bool | None]], placement: Placement):
        GomokuRule._check_valid_placement(board, placement)
        return GomokuRule.five_in_a_row(board, placement)


class RenjuRule(Rule):
    @staticmethod
    def will_win(board: list[list[bool | None]], placement: Placement):
        raise NotImplementedError()
