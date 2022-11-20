import numpy as np
from .dataset import Dataset
from rule import RenjuRule, BOARD_SIZE, BLANK
from container import Move
from copy import deepcopy

def get_valid_moves(color, rule, board):
    possible_moves = []

    min_i, min_j, max_i, max_j = BOARD_SIZE, BOARD_SIZE, -1, -1

    for i in range(len(board)):
        for j in range(len(board[i])):
            if board[i][j] != BLANK:
                min_i = min(i, min_i)
                min_j = min(j, min_j)
                max_i = max(i, max_i)
                max_j = max(j, max_j)

    for i in range(max(0, min_i-2), min(BOARD_SIZE, max_i+1+2)):
        for j in range(max(0, min_j-2), min(BOARD_SIZE, max_j+1+2)):
            move = Move(i, j, color)
            if not rule.is_legal_move(board, move):
                continue
            possible_moves.append(move)
    # possible_moves = [
    #     Move(i, j, color) for i in range(BOARD_SIZE) for j in range(BOARD_SIZE)
    # ]
    # possible_moves = list(filter(lambda move: rule.is_legal_move(board, move), possible_moves))
    return possible_moves

def get_mcts_v(color, rule, board):
    valid_moves = get_valid_moves(color, rule, board)
    valid_actions = np.array(list(map(lambda move: move.i * len(board) + move.j, valid_moves)), dtype=np.int32)
    v = np.zeros(BOARD_SIZE ** 2, dtype=np.bool)
    # v = np.random.rand(BOARD_SIZE ** 2) < 0.5
    v[valid_actions] = 1
    return v


class MCTS:
    def __init__(self, net, c_puct, rule=RenjuRule()):
        self.net = net
        self._dev = next(self.net.parameters()).device
        self.c_puct = c_puct
        self.rule = rule

        self.P = {}
        self.N = {}
        self.Q = {}
        self.W = {}  # total action value
        self.V = {}  # valid actions
        self.E = {}  # game ended

    def search(self, state, player, verbose=False):
        s = str(state)
        # if (s, player) not in self.E:
        #     self.E[(s, player)] = Rule.get_ended(state, player)

        # if (s, player) in self.E[(s, player)]:
        #     return -self.E[(s, player)]

        if (s, player) not in self.P:
            # leaf node
            valids = np.array(get_mcts_v(player, self.rule, state), dtype=np.float32)
            self.V[(s, player)] = valids
            if len(valids) == 0:
                self.E[(s, player)] = 1e-4
                return -1e-4

            p, v = self.net(Dataset.pack_to_tensor((state, player))[None, :, :, :].to(self._dev))

            p, v = p.cpu().detach().numpy()[0], v.cpu().detach().item()
            self.P[(s, player)] = p * self.V[(s, player)]
            self.P[(s, player)] /= np.sum(self.P[(s, player)])  # renormalize probabilities

            self.Q[(s, player)] = np.zeros(BOARD_SIZE ** 2, dtype=np.float32)
            self.N[(s, player)] = np.zeros(BOARD_SIZE ** 2, dtype=np.float32)
            self.W[(s, player)] = np.zeros(BOARD_SIZE ** 2, dtype=np.float32)

            return -v

        # valids = self.V[(s, player)]

        Q = self.Q[(s, player)]
        U = self.c_puct * self.P[(s, player)] * np.sqrt(np.sum(self.N[(s, player)])) / (1 + self.N[(s, player)])
        # print(Q+U)
        seq_action_to_action = self.V[(s, player)].nonzero()[0]
        # print(seq_action_to_action)

        seq_action = np.argmax((Q + U)[self.V[(s, player)].nonzero()[0]])  # if V is boolean, just indexing is possible
        action = seq_action_to_action[seq_action]
        # print(seq_action)
        # print(action)
        # print((Q+U)[self.V[(s, player)]])

        i, j = action // BOARD_SIZE, action % BOARD_SIZE
        next_state = deepcopy(state)
        next_state[i][j] = player
        next_player = -player
        next_s = str(next_state)
        if (next_s, next_player) not in self.E:
            self.E[(next_s, next_player)] = -1 if self.rule.is_win(state, Move(i, j, player)) else 0
        v = self.search(next_state, next_player) if not self.E[(next_s, next_player)] else -self.E[(next_s, next_player)]
        self.W[(s, player)][action] += v
        self.N[(s, player)][action] += 1
        self.Q[(s, player)][action] = self.W[(s, player)][action] / self.N[(s, player)][action]

        return -v