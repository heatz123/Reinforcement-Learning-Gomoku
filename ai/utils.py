import os
import pickle
import torch

from .model import PVNet

def load_model_from_path(path, n_iter, cfg):
  net = PVNet(*cfg.get_model_cfg()).float()
  net.load_state_dict(torch.load(f"{path}/net_{n_iter}.weights", map_location=torch.device('cpu')))
  dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
  net.to(dev)

  with open(f'{path}/dataset_{n_iter}.pkl', 'rb') as f:
    dataset = pickle.load(f)
  optimizer = torch.optim.SGD(net.parameters(), *cfg.get_optim_cfg())
  optimizer.load_state_dict(torch.load(f"{path}/optimizer_{n_iter}.weights", map_location=torch.device('cpu')))

  return net, dataset, optimizer


class Config:
  def __init__(self, cfg_dict, path):
    self.cfg_dict = cfg_dict
    self.path = path

  def get_model_cfg(self):
    model_cfg = self.cfg_dict["model_cfg"]
    return tuple(map(lambda param: model_cfg[param],
                     ["N_BLOCKS",
                      "IN_PLANES",
                      "OUT_PLANES",
                      "BOARD_SIZE",
                      ]))

  def get_agent_cfg(self):
    train_cfg = self.cfg_dict["train_cfg"]
    return tuple(map(lambda param: train_cfg[param],
                     ["c_puct",
                      "num_MCTS",
                      ]))

  def get_optim_cfg(self):
    train_cfg = self.cfg_dict["optim_cfg"]
    return tuple(map(lambda param: train_cfg[param],
                     ["lr",
                      "momentum",
                      "weight_decay",
                      ]))

  def save_cfg(self):
    with open(f'{self.path}/cfg.pkl', 'wb') as f:
      pickle.dump(self.cfg_dict, f)

  def load_cfg(self):
    import pickle
    with open(f'{self.path}/cfg.pkl', 'rb') as f:
      self.cfg_dict = pickle.load(f)


class Logger:
  log_cnt = 0

  def __init__(self, path, log_interval=10):
    self.path = path
    self.losses = {}
    self.log_interval = log_interval

  def log_loss(self, loss, num_iter):
    self.losses[num_iter] = loss

    self.log_cnt += 1
    if self.log_cnt % self.log_interval == self.log_interval - 1:
      self.save_loss()

  @staticmethod
  def board_to_str(state):
    place_to_str = {0: '.', 1: 'O', -1: 'X'}

    str_board = [[place_to_str[place] for place in row] for row in state]
    for (i, row) in enumerate(str_board):
      row.insert(0, str(i))
      str_board.append(['*'] + [str(i) for i in range(len(state))])

    board_str = ""
    for row in str_board:
      board_str += ' '.join(row)
      board_str += "\n"

    return board_str

  def log_game(self, states, n_iter, desc=""):
    with open(f"{self.path}/games_{n_iter}.txt", 'a') as f:
      f.write(desc + "\n")
      for state in states:
        f.write(self.board_to_str(state))

  def save_loss(self):
    with open(f'{self.path}/losses.pkl', 'wb') as f:
      pickle.dump(self.losses, f)

  def load_loss(self):
    if os.exists(f'{self.path}/losses.pkl'):
      with open(f'{self.path}/losses.pkl', 'rb') as f:
        self.losses = pickle.load(f)

