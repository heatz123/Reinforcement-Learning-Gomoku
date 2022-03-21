import numpy as np
class Game:
    def __init__(self):
        """state: positions(black stones, white stones), cur_player(0 or 1), is_game_ended(0 or 1)"""
        self.state = (np.zeros((2, 6*6)), 0, 0)
        
    def get_state(self):
        return self.state
    def get_legal_moves(self):
        positions, cur_player, _ = self.get_state()
        both_positions = np.logical_or(positions[0], positions[1])
        for i in range(0, 6):
            for j in range(0, 6):
                ### first find 33 
                pass
                
            
    def get_next_state(self, action):
        return np.zeros((2, 6*6)), 0, 0
    def play(self, players):
        positions, cur_player, is_game_ended = self.get_state()
        
        while not is_game_ended:
            action = players[cur_player].get_action(positions)
            positions, cur_player, is_game_ended = self.get_next_state(action)
            print(positions)
        print('black' if is_game_ended == 1 else 'white', 'win!')
    
class Player:
    def __init__(self):
        pass
    def get_action(self, positions):
        pass
    
import pygame
from pygame.locals import *
import sys

class HumanPlayer:
    def __init__(self):
        pygame.init()
        self.display = pygame.display.set_mode((300, 300))
        self.FPS_CLOCK = pygame.time.Clock()
    def get_action(self, positions):
        while True:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    return 
                self.FPS_CLOCK.tick(30)
                pygame.display.update()
                continue

game = Game()
game.play([HumanPlayer(), Player()])
