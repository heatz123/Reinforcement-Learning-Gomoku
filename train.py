import os
import pickle
import itertools
from copy import deepcopy
import numpy as np
import torch

from game import Game
from rule import BOARD_SIZE
from container import Move

from ai.mcts import MCTS, get_valid_moves
from ai.model import PVNet
from ai.dataset import Dataset
from ai.utils import load_model_from_path, Config, Logger


def get_train_examples(net, num_MCTS, eps, dirichlet_alpha, c_puct, temp_depth=6):
    net.eval()

    train_examples = []
    mcts = MCTS(net, c_puct)
    game = Game()
    game.play_move(Move(BOARD_SIZE // 2, BOARD_SIZE // 2, game.next_turn))

    while not game.is_game_over:
        depth = len(game.moves)
        print(depth)

        root = game.board
        player = game.next_turn
        s = str(root)

        if not get_valid_moves(player, game.rule, game.board):
            game.winner = 1e-4
            break

        mcts.search(root, player)
        dirichlet = np.random.dirichlet((dirichlet_alpha) * np.ones(BOARD_SIZE ** 2, dtype=np.float32))
        mcts.P[(s, player)] = (1 - eps) * mcts.P[(s, player)] + eps * dirichlet

        for i in range(num_MCTS):
            mcts.search(root, player)

        temp = (1 if depth < temp_depth else 0)
        if temp == 1:
            pi = mcts.N[(s, player)] / np.sum(mcts.N[(s, player)])
        elif temp == 0:
            pi = np.eye(BOARD_SIZE ** 2, dtype=np.float32)[np.argmax(mcts.N[(s, player)])]

        train_examples.append((root, player, pi))

        action = np.random.choice(list(range(BOARD_SIZE ** 2)), p=pi / np.sum(pi))
        i, j = action // BOARD_SIZE, action % BOARD_SIZE

        game.play_move(Move(i, j, player))

    return [((state, p), pi, (-1) ** (game.winner != p)) for (state, p, pi) in train_examples]

def train_and_get_loss(num_iter, dataset, num_batch, net, optimizer, verbose=False):
    net.train()

    dev = next(net.parameters()).device
    sum_of_loss = 0
    for n_iter in range(num_iter):
        optimizer.zero_grad()

        batch = dataset.get_batch(num_batch)
        x, pi, z = batch
        x = x.to(dev)
        pi = pi.to(dev)
        z = z.to(dev)
        p, v = net(x)

        loss = ((z - v) ** 2 - pi[:, None, :] @ torch.log(p + 1e-9)[:, :, None]).sum() / num_batch
        loss.backward()
        # torch.nn.utils.clip_grad_norm_(net.parameters(), max_norm=15, norm_type=2.0)
        torch.nn.utils.clip_grad_value_(net.parameters(), clip_value=15)
        optimizer.step()

        sum_of_loss += loss.item()
        if verbose and n_iter % 5 == 4:
            print(f"iteration {n_iter}: loss: {sum_of_loss / (n_iter + 1)}")

    return sum_of_loss / num_iter

def fill_dataset_for_a_game(dataset, selfplay_parameters):
    net, num_MCTS, eps, dirichlet_alpha, c_puct, temp_depth = selfplay_parameters
    result = get_train_examples(net, num_MCTS, eps, dirichlet_alpha, c_puct, temp_depth)

    for data in result:
        augmented_data_list = Dataset.augment_data(data)
        for augmented_data in augmented_data_list:
            dataset.append(augmented_data)

def save_iter(PATH, n_iter, net, dataset, optimizer):
    torch.save(optimizer.state_dict(), f"{PATH}/optimizer_{n_iter}.weights")
    with open(f'{PATH}/dataset_{n_iter}.pkl', 'wb') as f:
        pickle.dump(dataset, f)
    torch.save(net.state_dict(), f"{PATH}/net_{n_iter}.weights")


if __name__ == '__main__':
    print('Learning mode')

    # Train Settings
    num_batch = 32
    num_MCTS = 400
    num_iter = 16
    dataset_maxlen = 10000

    # Net
    N_BLOCKS = 1
    IN_PLANES = 3  # history * 2 + 1
    OUT_PLANES = 64
    BOARD_SIZE = 9

    # Optimizer
    lr = 0.0001
    momentum = 0.9
    weight_decay = 0

    eps = 0.25
    dirichlet_alpha = 10 / BOARD_SIZE ** 2
    c_puct = 5
    temp_depth = 5

    cfg_dict = {
        "model_cfg": {
            "N_BLOCKS": N_BLOCKS,
            "IN_PLANES": IN_PLANES,  # history * 2 + 1
            "OUT_PLANES": OUT_PLANES,
            "BOARD_SIZE": BOARD_SIZE,
        },
        "train_cfg": {
            "num_batch": num_batch,
            "num_MCTS": num_MCTS,
            "num_iter": num_iter,
            "dataset_maxlen": dataset_maxlen,
            "eps": eps,
            "dirichlet_alpha": dirichlet_alpha,
            "c_puct": c_puct,
            "temp_depth": temp_depth,
        },
        "optim_cfg": {
            "lr": lr,
            "momentum": momentum,
            "weight_decay": weight_decay
        }
    }

    PATH = "./models/base/"  # model save path

    resume = False
    iter_to_resume_from = 149  # needs if resume == True

    # train
    # self_play & evaluation

    if not os.path.exists(PATH):
        os.makedirs(PATH)

    if not resume:
        iter_to_resume_from = -1

    config = Config(cfg_dict, PATH)
    config.save_cfg()

    net = PVNet(N_BLOCKS,
                IN_PLANES,
                OUT_PLANES,
                BOARD_SIZE).float()

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f'using {dev}')
    net.to(dev)

    optimizer = torch.optim.SGD(net.parameters(), lr=lr, momentum=momentum, weight_decay=weight_decay)

    logger = Logger(PATH)

    # train
    # self_play & evaluation

    if resume:
        net, dataset, optimizer = load_model_from_path(PATH, iter_to_resume_from, config)
        logger.load_loss()
        best_net = deepcopy(net)
    else:
        best_net = deepcopy(net)
        dataset = Dataset(maxlen=dataset_maxlen)  # expect to be 320*

    # create base dataset
    for i in itertools.count():
        if len(dataset) >= dataset_maxlen:
            break
        fill_dataset_for_a_game(dataset, selfplay_parameters=(net, num_MCTS, eps, dirichlet_alpha, c_puct, temp_depth,))
        print(f"dataset has now {len(dataset)} examples")

        if i % 1 == 0:
            save_iter(PATH, "first", net, dataset, optimizer)

    # start training
    print("starting training...")
    for n_iter in range(iter_to_resume_from + 1, 1000000):
        fill_dataset_for_a_game(dataset, selfplay_parameters=(net, num_MCTS, eps, dirichlet_alpha, c_puct, temp_depth,))
        loss = train_and_get_loss(num_iter, dataset, num_batch, net, optimizer)
        print(f"{n_iter}th iter loss: {loss}")
        logger.log_loss(loss, n_iter)

        if n_iter % 50 == 49:
            # save
            print(f"  {n_iter}th iter: saving files...")
            save_iter(PATH, n_iter, net, dataset, optimizer)
