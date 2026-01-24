import numpy as np
import random
from config import Action, PlayerId

class SimpleBot:
    def __init__(self, player_id: int):
        self.player_id = player_id

    def get_move(self, game_map) -> Action:
        """
        Base method. Returns None if no move is decided.
        """
        pass

class RandomBot(SimpleBot):
    """
    Just picks a random valid move.
    """
    def get_move(self, game_map) -> Action:
        if random.random() < 0.5:
            return None  # 50% chance to skip move

        # Get all nodes owned by this bot
        my_nodes = [i for i, x in enumerate(game_map.state[:, 0]) if x == self.player_id]
        
        if not my_nodes:
            return None

        # Shuffle to pick a random starter
        random.shuffle(my_nodes)
        
        for source in my_nodes:
            # Check army count (need >1 to move)
            if game_map.state[source, 1] <= 1:
                continue
                
            # Get neighbors
            neighbors = list(game_map.graph.neighbors(source))
            if not neighbors:
                continue
                
            target = random.choice(neighbors)
            
            # Send 50% of army
            return Action(source, target, 0.5)
            
        return None

class GreedyBot(SimpleBot):
    """
    Aggressive bot:
    1. Finds its biggest army.
    2. Attacks the weakest enemy neighbor.
    """
    def get_move(self, game_map) -> Action:
        my_nodes = [i for i, x in enumerate(game_map.state[:, 0]) if x == self.player_id]
        
        # Sort my nodes by army strength (strongest first)
        my_nodes.sort(key=lambda i: game_map.state[i, 1], reverse=True)
        
        for source in my_nodes:
            if game_map.state[source, 1] <= 1:
                continue
                
            neighbors = list(game_map.graph.neighbors(source))
            
            # Find weakest neighbor
            best_target = None
            min_strength = 99999
            
            for target in neighbors:
                target_owner = game_map.state[target, 0]
                target_army = game_map.state[target, 1]
                
                # Prioritize attacking Enemy/Neutral over reinforcing Self
                score = target_army
                if target_owner == self.player_id:
                    score += 1000 # Discourage reinforcing unless necessary
                
                if score < min_strength:
                    min_strength = score
                    best_target = target
            
            if best_target is not None:
                return Action(source, best_target, 1.0) # Full attack
                
        return None
class AggressiveBot:
    def __init__(self, player_id):
        self.player_id = player_id

    def get_move(self, game_map):
        """
        Scans the map and executes the single most valuable move available.
        """
        best_score = -9999
        best_action = None

        # 1. Get all nodes owned by this bot
        my_nodes = np.where(game_map.state[:, 0] == self.player_id)[0]
        
        # If dead, do nothing
        if len(my_nodes) == 0:
            return None

        # 2. Evaluate every possible move from every node
        for source_id in my_nodes:
            source_army = game_map.state[source_id, 1]
            
            # If army is too small to do anything useful, skip
            if source_army < 2:
                continue

            # Check all neighbors
            neighbors = list(game_map.graph.neighbors(source_id))
            for target_id in neighbors:
                target_owner = game_map.state[target_id, 0]
                target_army = game_map.state[target_id, 1]
                
                score = 0
                
                # --- STRATEGY SCORING ---
                
                if target_owner != self.player_id:
                    # CASE A: ATTACK (Enemy or Neutral)
                    if source_army > target_army + 1:
                        # We can win!
                        if target_owner == 0: # Neutral
                            score = 50 + (source_army - target_army) # Good
                        else: # Enemy (The Player)
                            # Killing the player is VERY GOOD
                            score = 200 + (source_army - target_army) * 2 
                    else:
                        # Suicide attack - bad idea
                        score = -100
                else:
                    # CASE B: REINFORCE (Move to own node)
                    # Only move if the source is safe and target is threatened
                    # (This is a simplified check for speed)
                    score = 10 

                # --- SELECTION ---
                if score > best_score:
                    best_score = score
                    # Send 100% of forces if attacking, 50% if reinforcing
                    pct = 1.0 if target_owner != self.player_id else 0.5
                    best_action = Action(source_id, target_id, pct)

        return best_action