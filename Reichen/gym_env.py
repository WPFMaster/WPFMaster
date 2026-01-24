import numpy as np
import gymnasium as gym
import networkx as nx
from gymnasium import spaces

from config import GameConfig, Action, PlayerId
from game_logic import AbstractMap
from observation_builder import ObservationBuilder
from bots import GreedyBot, RandomBot, AggressiveBot

class StrategyGameEnv(gym.Env):
    """
    Custom Environment that follows gymnasium interface.
    This connects the abstract game logic to RL training loops.
    """
    metadata = {'render_modes': ['human', 'console', 'file'], 'render_fps': 30}

    def __init__(self, render_mode=None):
        super(StrategyGameEnv, self).__init__()
        
        self.config = GameConfig()
        self.render_mode = render_mode
        
        # Initialize Core Components
        self.game_map = None # Created in reset
        self.obs_builder = ObservationBuilder()
        self.current_tick = 0
        
        # --- ACTION SPACE ---
        # MultiDiscrete allows us to output multiple discrete values at once.
        # [Source Node ID, Target Node ID, Split Percentage Index]
        # Split Percentage Index: 0 = 10%, 1 = 20% ... 9 = 100%
        self.action_space = spaces.MultiDiscrete([
            self.config.MAX_NODES,  # Which node moves
            self.config.MAX_NODES,  # Where it moves
            10,                     # How much (10 discrete steps)
            2                       # Whether to move (0 = No, 1 = Yes)
        ])

        # --- OBSERVATION SPACE ---
        # Matches the output of ObservationBuilder.get_observation()
        # We use float32 for Neural Network compatibility
        self.observation_space = spaces.Dict({
            "node_features": spaces.Box(
                low=-1.0, high=1.0, 
                shape=(self.config.MAX_NODES, 4), 
                dtype=np.float32
            ),
            "adjacency": spaces.Box(
                low=0.0, high=1.0, 
                shape=(self.config.MAX_NODES, self.config.MAX_NODES), 
                dtype=np.float32
            ),
            "global_features": spaces.Box(
                low=0.0, high=1000.0, # High upper bound just to be safe
                shape=(2, 2), 
                dtype=np.float32
            )
        })

        # Track internal stats for reward calculation
        self.prev_army_count = 0
        self.prev_node_count = 0
        self.prev_opponent_army = 0

        self.opponent = AggressiveBot(PlayerId.PLAYER_2)

        # PRE-CALCULATE DISTANCES
        # We need a matrix of distances from every node to every other node.
        # This allows us to instantly find the "nearest neighbor" without slow loops.
        self.dist_matrix = None

    def _get_nearest_valid_source(self, desired_node_id, player_id):
        """
        Finds the closest node to 'desired_node_id' that is owned by 'player_id'.
        """
        # 1. Check if the desired node is already valid
        if self.game_map.state[desired_node_id, 0] == player_id:
            return desired_node_id
            
        # 2. Search for the closest owned node
        min_dist = 999
        best_node = None
        
        # Get all owned nodes
        owned_nodes = [i for i, x in enumerate(self.game_map.state[:, 0]) if x == player_id]
        
        if not owned_nodes:
            return None # Player is dead
            
        for node in owned_nodes:
            # Get distance from desired node to this owned node
            # Default to 999 if disconnected (shouldn't happen in a connected graph)
            dist = self.dist_matrix[desired_node_id].get(node, 999)
            
            if dist < min_dist:
                min_dist = dist
                best_node = node
            elif dist == min_dist:
                # Tie-breaker: pick the one with more army? Or just lower ID.
                # Let's pick the one with more army to be helpful.
                if self.game_map.state[node, 1] > self.game_map.state[best_node, 1]:
                    best_node = node
                    
        return best_node
    
    def _get_nearest_valid_target(self, source_id, desired_target_id):
        """
        Finds the neighbor of 'source_id' that is closest to 'desired_target_id'.
        """
        neighbors = list(self.game_map.graph.neighbors(source_id))
        if not neighbors:
            return None
            
        # If the desired target is actually a neighbor, pick it.
        if desired_target_id in neighbors:
            return desired_target_id
            
        # Otherwise, pick the neighbor that is physically closest to the desired target
        # (This simulates 'moving towards' the target)
        min_dist = 999
        best_neighbor = neighbors[0]
        
        for neighbor in neighbors:
            dist = self.dist_matrix[desired_target_id].get(neighbor, 999)
            if dist < min_dist:
                min_dist = dist
                best_neighbor = neighbor
                
        return best_neighbor

    def reset(self, seed=None, options=None):
        """
        Resets the environment to an initial state and returns the initial observation.
        """
        super().reset(seed=seed)
        
        # Create a new random map
        # We pass the seed to AbstractMap for reproducibility
        self.game_map = AbstractMap(seed=seed)
        self.current_tick = 0
        
        self.dist_matrix = dict(nx.all_pairs_shortest_path_length(self.game_map.graph))
        
        # Reset tracking stats for Player 1 (The Agent)
        # # Reset tracking stats
        p1_mask = (self.game_map.state[:, 0] == PlayerId.PLAYER_1)
        p2_mask = (self.game_map.state[:, 0] == PlayerId.PLAYER_2)
        
        self.prev_node_count = np.sum(p1_mask)
        self.prev_army_count = np.sum(self.game_map.state[p1_mask, 1])

        # NEW: Track enemy army to reward killing
        self.prev_opponent_army = np.sum(self.game_map.state[p2_mask, 1])

        obs = self.obs_builder.get_observation(self.game_map, PlayerId.PLAYER_1)
        return obs, {}

    def step(self, action):
        """
        Execute one time step within the environment.
        """

        # 1. DECODE ACTION
        raw_source = int(action[0])
        raw_target = int(action[1])
        split_idx = int(action[2])
        do_move = int(action[3])
        
        
        move_success = False
        game_action = None
        
        if do_move:
            # Snap source to nearest owned node
            real_source = self._get_nearest_valid_source(raw_source, PlayerId.PLAYER_1)

            if real_source is not None:
                # 2. DECODE & SNAP TARGET
                # Snap target to the neighbor closest to where the AI wanted to click
                real_target = self._get_nearest_valid_target(real_source, raw_target)
                
                if real_target is not None:
                    amount_pct = (split_idx + 1) / 10.0
                    game_action = Action(real_source, real_target, amount_pct)
                    
                    # 3. EXECUTE
                    move_success = self.game_map.execute_move(game_action, PlayerId.PLAYER_1)

        # Opponent Move (Player 2)
        bot_action = self.opponent.get_move(self.game_map)
        if bot_action:
            self.game_map.execute_move(bot_action, PlayerId.PLAYER_2)
        
        # Simple Opponent:
        # In a real training scenario, you might want a smarter opponent here.
        # For now, Player 2 does nothing (or you can add a random mover here).
        
        # 3. TICK & GROWTH LOGIC
        cycle_pos = self.current_tick % self.config.CYCLE_LENGTH
        
        if cycle_pos == self.config.FILLING_TICK:
            self.game_map.apply_growth('FILLING')
        elif cycle_pos == self.config.GROWTH_TICK:
            self.game_map.apply_growth('FULL')
            
        self.current_tick += 1
        
        # 4. CALCULATE REWARD
        reward = -0.01

        # Penalty: Invalid Move
        if not move_success and do_move:
            reward -= 0.1

        # Penalty: Small step cost to encourage faster wins
        reward -= 0.1 * (self.current_tick / self.config.MAX_TIMEOUT_TICKS) ** 2
        
        # --- B. STATE TRACKING ---
        p1_mask = (self.game_map.state[:, 0] == PlayerId.PLAYER_1)
        p2_mask = (self.game_map.state[:, 0] == PlayerId.PLAYER_2)
        
        current_node_count = np.sum(p1_mask)
        current_p1_army = np.sum(self.game_map.state[p1_mask, 1])
        current_p2_army = np.sum(self.game_map.state[p2_mask, 1])

        # 3. ATTRITION (The "Killer" Reward)
        # Did we kill enemy units? (We infer this if enemy army dropped)
        # Note: This is a rough heuristic, but effective.
        # If enemy army went down, we likely killed them.
        enemy_loss = self.prev_opponent_army - current_p2_army
        if enemy_loss > 0:
             # Reward for killing units.
             # Small enough to not distract from objectives, big enough to encourage fighting.
             reward += enemy_loss * 0.05
        
        # 2. EXPANSION (The "Conqueror" Reward)
        node_diff = current_node_count - self.prev_node_count
        if node_diff > 0:
            reward += 2.0 * node_diff  # Big bonus for taking a node
        elif node_diff < 0:
            reward += 2.0 * node_diff  # Big penalty for losing a node


            
        # Reward: Winning
        winner = self.game_map.is_game_over()
        terminated = False
        if winner == PlayerId.PLAYER_1:
            print("Player 1 Wins!")
            reward += 100.0
            terminated = True
        elif winner == PlayerId.PLAYER_2:
            reward -= 100.0 # Penalty for losing
            terminated = True
            
        # Update tracking stats
        self.prev_node_count = current_node_count
        self.prev_army_count = current_p1_army
        self.prev_opponent_army = current_p2_army # Make sure to add this to __init__!

        # 5. GET OBSERVATION
        obs = self.obs_builder.get_observation(self.game_map, PlayerId.PLAYER_1)
        
        # Truncation: Stop if game drags on too long (e.g., 200 ticks)
        truncated = False
        if self.current_tick > self.config.MAX_TIMEOUT_TICKS:
            truncated = True
            
        info = {
            "valid_move": move_success if do_move else True,
            "winner": winner,

            # ADD THESE LINES FOR THE LOGGER:
            "action_do_move": do_move,     # 1 or 0
            "is_success": move_success     # True or False
        }
        
        return obs, reward, terminated, truncated, info

    def render(self):
        """
        File-based visualization.
        Logs the game state to 'game_log.txt'.
        """
        # Define the output file name
        log_filename = "game_logs/game_log.txt"

        if self.render_mode == "file":
            # Open in 'a' (append) mode so we don't delete previous ticks
            with open(log_filename, "a") as f:
                f.write(f"--- Tick {self.current_tick} ---\n")
                f.write(f"P1 Nodes: {self.prev_node_count} | P1 Army: {self.prev_army_count}\n")
                
                # Show top 5 nodes by army size
                sorted_indices = np.argsort(self.game_map.state[:, 1])[::-1]
                f.write("Top Strongholds:\n")
                
                for i in range(min(5, self.config.MAX_NODES)):
                    idx = sorted_indices[i]
                    owner = self.game_map.state[idx, 0]
                    army = self.game_map.state[idx, 1]
                    owner_str = "P1" if owner == 1 else "P2" if owner == 2 else "Neu"
                    f.write(f"  Node {idx}: {owner_str} ({army})\n")
                
                # Add an extra newline for separation between frames
                f.write("\n")
        elif self.render_mode == "console" or self.render_mode == "human":
            print(f"--- Tick {self.current_tick} ---")
            print(f"P1 Nodes: {self.prev_node_count} | P1 Army: {self.prev_army_count}")
            # Show top 5 nodes by army size
            sorted_indices = np.argsort(self.game_map.state[:, 1])[::-1]
            print("Top Strongholds:")
            for i in range(min(5, self.config.MAX_NODES)):
                idx = sorted_indices[i]
                owner = self.game_map.state[idx, 0]
                army = self.game_map.state[idx, 1]
                owner_str = "P1" if owner == 1 else "P2" if owner == 2 else "Neu"
                print(f"  Node {idx}: {owner_str} ({army})")