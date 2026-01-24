from config import GameConfig, PlayerId, Action
from game_logic import AbstractMap

class GameSession:
    def __init__(self, players, fps=GameConfig.RENDER_FPS):
        self.idealFps = fps
        if fps != None:
            self.tickTime = 1_000 / fps
        else:
            self.tickTime = 0
        self.actualFps = 0
        self.players = players
        self.currentTick = 0

    def tick(self):
        for player in self.players:
            player.getActions()
            Action()