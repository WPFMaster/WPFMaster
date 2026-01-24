import numpy as np
from stable_baselines3.common.callbacks import BaseCallback

class GameStatsCallback(BaseCallback):
    """
    Custom callback for plotting additional game metrics in TensorBoard.
    """
    def __init__(self, verbose=0):
        super(GameStatsCallback, self).__init__(verbose)
        # Initialize counters
        self.moves_active = 0   # AI chose to move (do_move=1)
        self.moves_passive = 0  # AI chose to wait (do_move=0)
        self.invalid_moves = 0  # AI tried to move but failed
        self.wins = 0           # Number of wins by AI

    def _on_step(self) -> bool:
        # 1. Access the 'info' from the environment
        # SB3 vectorizes environments, so 'infos' is a list. We take [0].
        infos = self.locals['infos']
        
        # Loop through all parallel envs (usually just 1)
        for info in infos:
            if 'action_do_move' in info:
                if info['action_do_move'] == 1:
                    self.moves_active += 1
                else:
                    self.moves_passive += 1
            
            if 'is_success' in info and not info['is_success'] and info.get('action_do_move') == 1:
                self.invalid_moves += 1

            if 'winner' in info and info['winner'] != 0:
                if info['winner'] == 1:  # AI is Player 1
                    self.wins += 1

        return True

    def _on_rollout_end(self) -> None:
        # This triggers before every PPO update (usually every 2048 steps)
        
        total_steps = self.moves_active + self.moves_passive
        
        if total_steps > 0:
            # Calculate percentages
            active_ratio = self.moves_active / total_steps
            invalid_ratio = self.invalid_moves / self.moves_active if self.moves_active > 0 else 0
            
            # --- LOGGING TO TENSORBOARD ---
            # These will appear under a new tag "custom_strategy" in TensorBoard
            self.logger.record("game/active_move_ratio", active_ratio)
            self.logger.record("game/invalid_move_ratio", invalid_ratio)
            self.logger.record("game/total_wins", self.wins)
            
        # Reset counters for the next rollout
        self.moves_active = 0
        self.moves_passive = 0
        self.invalid_moves = 0