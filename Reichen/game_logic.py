import numpy as np
import networkx as nx
from typing import List, Tuple, Dict, Optional
from config import GameConfig, PlayerId, Action

class AbstractMap:
    """
    Represents the game state on a graph.
    Handles map generation, move execution (battles), and growth phases.
    """
    def __init__(self, seed: Optional[int] = None):
        """
        Initializes the game map with random connections and starting states.
        
        Args:
            seed (int, optional): Random seed for reproducibility.
        """
        self.config = GameConfig()
        if seed is not None:
            np.random.seed(seed)
        
        # 1. Generate a connected graph
        # We ensure the graph is fully connected so all nodes are reachable
        while True:
            self.graph = nx.gnp_random_graph(
                self.config.MAX_NODES, 
                self.config.CONNECTION_PROBABILITY, 
                seed=seed,
                directed=False
            )
            if nx.is_connected(self.graph):
                break
        
        # 2. Initialize State Matrix
        # Shape: (MAX_NODES, 2)
        # Column 0: Owner ID (PlayerId)
        # Column 1: Army Count (int)
        self.state = np.zeros((self.config.MAX_NODES, 2), dtype=np.int32)
        
        self._initialize_armies()

    def _initialize_armies(self):
        """Sets up the initial board state with neutral armies and player starts."""
        # Set all to Neutral with small random armies (1-5)
        self.state[:, 0] = PlayerId.NEUTRAL
        self.state[:, 1] = np.random.randint(1, 5, size=self.config.MAX_NODES)
        
        # Pick 2 distinct nodes for Player 1 and Player 2
        start_nodes = np.random.choice(self.config.MAX_NODES, size=2, replace=False)
        
        # Player 1 setup
        p1_node = start_nodes[0]
        self.state[p1_node, 0] = PlayerId.PLAYER_1
        self.state[p1_node, 1] = 20  # Stronger starting army
        
        # Player 2 setup
        p2_node = start_nodes[1]
        self.state[p2_node, 0] = PlayerId.PLAYER_2
        self.state[p2_node, 1] = 20  # Stronger starting army

    def get_valid_moves(self, player_id: int) -> List[Action]:
        """
        Returns a list of theoretical legal moves (useful for simple bots/debugging).
        Note: The RL agent will predict moves directly, so this is helper logic.
        """
        valid_moves = []
        
        # Find indices of all nodes owned by this player
        owned_nodes = np.where(self.state[:, 0] == player_id)[0]
        
        for source in owned_nodes:
            army_count = self.state[source, 1]
            # Must have > 1 army to move (leave 1 behind)
            if army_count <= 1: 
                continue 
                
            neighbors = list(self.graph.neighbors(source))
            for target in neighbors:
                # Add examples of moves
                valid_moves.append(Action(source, target, 0.5))
                valid_moves.append(Action(source, target, 1.0))
                
        return valid_moves

    def execute_move(self, action: Action, player_id: int) -> bool:
        """
        Executes a single move/attack.
        
        Args:
            action (Action): The move details.
            player_id (int): The player attempting the move.
            
        Returns:
            bool: True if the move was valid and executed, False otherwise.
        """
        source = action.source_id
        target = action.target_id
        
        # --- VALIDATION CHECKS ---
        
        # 1. Check Index Bounds
        if not (0 <= source < self.config.MAX_NODES) or not (0 <= target < self.config.MAX_NODES):
            return False

        # 2. Check Ownership (Can only move your own units)
        if self.state[source, 0] != player_id:
            return False
            
        # 3. Check Adjacency (Must be connected)
        if not self.graph.has_edge(source, target):
            return False
            
        # 4. Check Army Count (Need at least 2 to move 1 and leave 1)
        source_armies = self.state[source, 1]
        if source_armies <= 1:
            return False
            
        # --- EXECUTION LOGIC ---
        
        # Calculate absolute amount to move
        move_amount = int(source_armies * action.amount_pct)
        
        # Clamp amount: Must move at least 1, must leave at least 1
        if move_amount < 1:
            move_amount = 1
        if move_amount >= source_armies:
            move_amount = source_armies - 1 
            
        # Remove armies from source
        self.state[source, 1] -= move_amount
        
        target_owner = self.state[target, 0]
        target_armies = self.state[target, 1]
        
        # Case A: Friendly Move (Reinforcement)
        if target_owner == player_id:
            self.state[target, 1] += move_amount
            # Enforce global cap
            if self.state[target, 1] > self.config.MAX_ARMIES_CAP:
                self.state[target, 1] = self.config.MAX_ARMIES_CAP
                
        # Case B: Attack (Combat)
        else:
            # Deterministic Combat: Simple Subtraction
            remaining_defenders = target_armies - move_amount
            
            if remaining_defenders < 0:
                # Attacker Wins
                self.state[target, 0] = player_id
                self.state[target, 1] = abs(remaining_defenders)
            else:
                # Defender Holds
                self.state[target, 1] = remaining_defenders
                # If 0 defenders remain, owner keeps it with 0 armies (standard Risk rules)

        return True

    def apply_growth(self, mode: str):
        """
        Applies army growth based on the game phase rules.
        
        Args:
            mode (str): 'FILLING' or 'FULL'.
        """
        # Boolean mask for nodes owned by active players (ignoring Neutrals)
        player_mask = (self.state[:, 0] == PlayerId.PLAYER_1) | (self.state[:, 0] == PlayerId.PLAYER_2)
        
        if mode == 'FULL':
            # Add SMALL_GROWTH to ALL player-owned nodes
            self.state[player_mask, 1] += self.config.SMALL_GROWTH
            
        elif mode == 'FILLING':
            # Add BIG_GROWTH only to "Big" countries
            # Criteria: Player owned AND Army count > Threshold
            big_country_mask = player_mask & (self.state[:, 1] > self.config.BIG_COUNTRY_THRESHOLD)
            self.state[big_country_mask, 1] += self.config.BIG_GROWTH
            
        # Clamp values to prevent numerical instability during long training sessions
        self.state[:, 1] = np.clip(self.state[:, 1], 0, self.config.MAX_ARMIES_CAP)

    def is_game_over(self) -> int:
        """
        Checks if the game has ended.
        Returns:
            int: PlayerId of winner (1 or 2), or 0 if game continues.
        """
        owners = self.state[:, 0]
        has_p1 = PlayerId.PLAYER_1 in owners
        has_p2 = PlayerId.PLAYER_2 in owners
        
        if has_p1 and not has_p2:
            return PlayerId.PLAYER_1
        if has_p2 and not has_p1:
            return PlayerId.PLAYER_2
        
        return 0 # Game continues