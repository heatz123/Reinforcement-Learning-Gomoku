from container import Direction, Move, Row

BLACK = 1
WHITE = -1
BLANK = 0
BOARD_SIZE = 9

directions = [
    Direction(1, 0),
    Direction(0, 1),
    Direction(1, 1),
    Direction(1, -1),
]


def name_of(color: int):
    if color is None:
        return None
    return ['BLANK', 'BLACK', 'WHITE'][color]


class IllegalMoveError(ValueError):
    def __init__(self, message):
        self.message = message
        super(IllegalMoveError, self).__init__(message)

    def __str__(self):
        return f'IllegalMoveError: {self.message}'


class Rule:
    @staticmethod
    def is_valid_position(board: list[list], i: int, j: int):
        return 0 <= i < len(board) and 0 <= j < len(board[i])

    def is_legal_move(self, board: list[list[int]], move: Move, raise_exception=False):
        if not self.is_valid_position(board, move.i, move.j):
            if raise_exception:
                raise IllegalMoveError('Out of range of board.')
            return False
        if board[move.i][move.j] != BLANK:
            if raise_exception:
                raise IllegalMoveError('A stone exists already.')
            return False
        return True

    def count_succession(self, board: list[list[int]], move: Move, direction: Direction):
        cnt = 1
        pos = direction.front_of(move.i, move.j)
        while self.is_valid_position(board, *pos):
            if move.color != board[pos[0]][pos[1]]:
                break
            cnt += 1
            pos = direction.front_of(*pos)
        pos = direction.rear_of(move.i, move.j)
        while self.is_valid_position(board, *pos):
            if move.color != board[pos[0]][pos[1]]:
                break
            cnt += 1
            pos = direction.rear_of(*pos)
        return cnt

    def is_win(self, board: list[list[int]], move: Move):
        raise NotImplementedError()


class GomokuRule(Rule):
    def _five_in_a_row(self, board: list[list[int]], move: Move):
        return any(self.count_succession(board, move, d) >= 5 for d in directions)

    def is_win(self, board: list[list[int]], move: Move):
        return self._five_in_a_row(board, move)


class RenjuRule(Rule):
    def __init__(self):
        self.legal_memo = dict()

    def is_win(self, board: list[list[int]], move: Move):
        for direction in directions:
            succession = self.count_succession(board, move, direction)
            if succession == 5 or (move.color == WHITE and succession >= 6):
                return True
        return False

    def is_legal_move(self, board: list[list[int]], move: Move, raise_exception=False):
        board_move_string = ''.join(''.join(str(c) for c in row) for row in board)+f'|{move.i},{move.j},{move.color}'
        if not raise_exception:
            if board_move_string in self.legal_memo:
                return self.legal_memo[board_move_string]
        if not super(RenjuRule, self).is_legal_move(board, move, raise_exception=raise_exception):
            self.legal_memo[board_move_string] = False
            return False
        if move.color == WHITE:
            # self.legal_memo[board_move_string] = True
            return True
        try:
            board[move.i][move.j] = move.color
            if any(self.is_overline(board, move, d) for d in directions):
                if raise_exception:
                    raise IllegalMoveError('Overline not allowed for Black.')
                # self.legal_memo[board_move_string] = False
                return False
            _, threes, fours = self.get_rows(board, move)
            if len(fours) >= 2:
                cnt_four = 0
                for row in fours:
                    if self.is_four(board, row, move.color):
                        cnt_four += 1
                        if cnt_four >= 2:
                            if raise_exception:
                                raise IllegalMoveError(f'more than two fours not allowed for Black.')
                            self.legal_memo[board_move_string] = False
                            return False
            if len(threes) >= 2:
                maybe_open_threes = [row for row in threes if not self.is_explicitly_closed_three(board, row, move.color)]
                if len(maybe_open_threes) >= 2:
                    cnt_open_three = 0
                    for row in maybe_open_threes:
                        if self.is_open_three(board, row, move.color):
                            cnt_open_three += 1
                            if cnt_open_three >= 2:
                                if raise_exception:
                                    raise IllegalMoveError(f'more than two open threes not allowed for Black.')
                                self.legal_memo[board_move_string] = False
                                return False
            self.legal_memo[board_move_string] = True
            return True
        finally:
            board[move.i][move.j] = BLANK

    def get_rows(self, board: list[list[int]], move: Move):
        twos = []
        threes = []
        fours = []
        for d in directions:
            def get_end(_center_succession, step):
                end = step
                center_end = None
                end_blank = None
                _end_succession = []
                _succession = _center_succession
                while True:
                    ei, ej = move.i + end * d.i, move.j + end * d.j
                    if not self.is_valid_position(board, ei, ej) or board[ei][ej] == -move.color:
                        if center_end is None:
                            center_end = end - step
                        break
                    if board[ei][ej] == BLANK:
                        if _succession is _end_succession:
                            break
                        center_end = end - step
                        end_blank = (ei, ej)
                        _succession = _end_succession
                    else:
                        _succession.append((ei, ej))
                    end += step
                end -= step
                if abs(end) > 4:
                    return center_end, None, []
                return end, end_blank, _end_succession

            center_succession = [(move.i, move.j)]
            front, front_blank, front_succession = get_end(center_succession, -1)
            front_succession = front_succession[::-1]
            center_succession = center_succession[::-1]
            rear, rear_blank, rear_succession = get_end(center_succession, 1)

            if len(center_succession) == 2:
                twos.append(Row(center_succession, None, d))
            if len(center_succession) == 3:
                threes.append(Row(center_succession, None, d))
            if len(center_succession) == 4:
                fours.append(Row(center_succession, None, d))
            if front_succession:
                if len(center_succession) + len(front_succession) == 2:
                    twos.append(Row(front_succession + center_succession, front_blank, d))
                if len(center_succession) + len(front_succession) == 3:
                    threes.append(Row(front_succession + center_succession, front_blank, d))
                if len(center_succession) + len(front_succession) == 4:
                    fours.append(Row(front_succession + center_succession, front_blank, d))
            if rear_succession:
                if len(center_succession) + len(rear_succession) == 2:
                    twos.append(Row(center_succession + rear_succession, rear_blank, d))
                if len(center_succession) + len(rear_succession) == 3:
                    threes.append(Row(center_succession + rear_succession, rear_blank, d))
                if len(center_succession) + len(rear_succession) == 4:
                    fours.append(Row(center_succession + rear_succession, rear_blank, d))
        return twos, threes, fours

    def is_five_in_a_row(self, board: list[list[int]], move: Move, direction: Direction):
        return self.count_succession(board, move, direction) == 5

    def is_overline(self, board: list[list[int]], move: Move, direction: Direction):
        return self.count_succession(board, move, direction) >= 6

    def is_explicitly_closed_three(self, board: list[list[int]], row: Row, color: int):
        def is_invalid(blank: tuple[int, int]):
            return not self.is_valid_position(board, *blank) or board[blank[0]][blank[1]] == -color

        def is_occupied(blank: tuple[int, int]):
            return self.is_valid_position(board, *blank) and board[blank[0]][blank[1]] == color

        if len(row.move_list) != 3:
            return False

        front_blank = row.front_blank
        rear_blank = row.rear_blank
        if is_invalid(front_blank) or is_invalid(rear_blank):
            return True

        front_blank = row.direction.front_of(*front_blank)
        rear_blank = row.direction.rear_of(*rear_blank)
        if is_occupied(front_blank) or is_occupied(rear_blank):
            return True
        if row.inner_blank is None:
            if is_invalid(front_blank) and is_invalid(rear_blank):
                return True
        return False

    def is_four(self, board: list[list[int]], row: Row, color: int):
        if row.inner_blank is not None:
            return self.is_legal_move(board, Move(*row.inner_blank, color))
        else:
            if self.is_legal_move(board, Move(*row.front_blank, color)):
                return True
            if self.is_legal_move(board, Move(*row.rear_blank, color)):
                return True
            return False

    def is_open_three(self, board: list[list[int]], row: Row, color: int):
        if row.inner_blank is not None:
            if not self.is_legal_move(board, Move(*row.inner_blank, color)):
                return False
            try:
                board[row.inner_blank[0]][row.inner_blank[1]] = color
                if not self.is_legal_move(board, Move(*row.front_blank, color)):
                    return False
                if not self.is_legal_move(board, Move(*row.rear_blank, color)):
                    return False
            finally:
                board[row.inner_blank[0]][row.inner_blank[1]] = BLANK
            return True
        else:
            if self.is_legal_move(board, Move(*row.front_blank, color)):
                try:
                    board[row.front_blank[0]][row.front_blank[1]] = color
                    if self.is_legal_move(board, Move(*row.direction.front_of(*row.front_blank), color)) and self.is_legal_move(board, Move(*row.rear_blank, color)):
                        return True
                finally:
                    board[row.front_blank[0]][row.front_blank[1]] = BLANK

            if self.is_legal_move(board, Move(*row.rear_blank, color)):
                try:
                    board[row.rear_blank[0]][row.rear_blank[1]] = color
                    if self.is_legal_move(board, Move(*row.direction.rear_of(*row.rear_blank), color)) and self.is_legal_move(board, Move(*row.front_blank, color)):
                        return True
                finally:
                    board[row.rear_blank[0]][row.rear_blank[1]] = BLANK
            return False

    def is_half_open_three(self, board: list[list[int]], row: Row, color: int):
        if row.inner_blank is not None:
            if not self.is_legal_move(board, Move(*row.inner_blank, color)):
                return False
            try:
                board[row.inner_blank[0]][row.inner_blank[1]] = color
                return self.is_legal_move(board, Move(*row.front_blank, color)) or self.is_legal_move(board, Move(*row.rear_blank, color))
            finally:
                board[row.inner_blank[0]][row.inner_blank[1]] = BLANK
        else:
            if self.is_legal_move(board, Move(*row.front_blank, color)):
                try:
                    board[row.front_blank[0]][row.front_blank[1]] = color
                    return self.is_legal_move(board, Move(*row.direction.front_of(*row.front_blank), color)) or self.is_legal_move(board, Move(*row.rear_blank, color))
                finally:
                    board[row.front_blank[0]][row.front_blank[1]] = BLANK
            if self.is_legal_move(board, Move(*row.rear_blank, color)):
                try:
                    board[row.rear_blank[0]][row.rear_blank[1]] = color
                    return self.is_legal_move(board, Move(*row.direction.rear_of(*row.rear_blank), color)) or self.is_legal_move(board, Move(*row.front_blank, color))
                finally:
                    board[row.rear_blank[0]][row.rear_blank[1]] = BLANK
            return False

    def is_open_four(self, board: list[list[int]], row: Row, color: int):
        if row.inner_blank is not None:
            return False
        return self.is_legal_move(board, Move(*row.front_blank, color)) and self.is_legal_move(board, Move(*row.rear_blank, color))
