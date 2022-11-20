from collections import deque
import random
import torch
import numpy as np

class Dataset:
  def __init__(self, maxlen):
    self.deque = deque(maxlen=maxlen)

  @staticmethod
  def pack_to_tensor(state_and_player):
    state, player = state_and_player
    state = np.array(state, dtype=np.float32)
    state_p1 = (state == player)
    state_p2 = (state == -player)
    state_player = np.ones_like(state_p1) * player
    state_tensor = torch.from_numpy(np.stack((state_p1, state_p2, state_player), axis=0).astype(np.float32))
    return state_tensor

  @staticmethod
  def augment_data(data):
    x, pi, r = data
    state, player = x
    pi_xy = pi.reshape(int(np.sqrt(len(pi))), -1)
    states = []
    pi_xys = []

    for _ in range(4):
      state = np.rot90(np.copy(state))
      pi_xy = np.rot90(np.copy(pi_xy))
      states.append(state)
      pi_xys.append(pi_xy)

    for i in range(4):
      state = states[i]
      states.append(np.fliplr(np.copy(state)))
      pi_xy = pi_xys[i]
      pi_xys.append(np.fliplr(np.copy(pi_xy)))

    pis = [pi_xy.flatten() for pi_xy in pi_xys]

    return [((s, player), pi, r) for s, pi in zip(states, pis)]

  def get_batch(self, batch_num):
    batch = random.sample(self.deque, batch_num)

    x, pi, r = list(zip(*batch))
    x = list(map(Dataset.pack_to_tensor, x))
    x = torch.tensor(np.stack(x, axis=0), dtype=torch.float32)
    pi = torch.tensor(np.stack(pi, axis=0), dtype=torch.float32)
    r = torch.tensor(np.stack(r, axis=0), dtype=torch.float32)

    return (x, pi, r)

  def append(self, data):
    assert len(data) == 3
    self.deque.append(data)

  def __len__(self):
    return len(self.deque)