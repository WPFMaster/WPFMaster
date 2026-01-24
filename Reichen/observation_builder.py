import numpy as np
import networkx as nx
from config import GameConfig, PlayerId
from game_logic import AbstractMap

class ObservationBuilder:
    """
    Translates the raw Game State (AbstractMap) into a format suitable for 
    Deep Neural Networks (PyTorch/TensorFlow).
    
    The output is a dictionary of tensors representing the graph structure 
    and the features of each node relative to the current player.
    """
    
    def __init__(self):
        self.config = GameConfig()

    def get_observation(self, game_map: AbstractMap, current_player_id: int) -> dict:
        """
        Generates the observation dictionary for a specific player.
        
        Args:
            game_map (AbstractMap): The current game state.
            current_player_id (int): The ID of the player "viewing" the board.
            
        Returns:
            dict: {
                "node_features": np.array (N, 4),
                "adjacency": np.array (N, N),
                "global_features": np.array (2, 2)
            }
        """
        num_nodes = self.config.MAX_NODES
        
        # 1. PREPARE ADJACENCY MATRIX
        # We use a dense matrix (N x N). For very large maps, sparse matrices are better,
        # but for N=20, dense is faster and easier for standard CNNs/GNNs.
        adjacency = nx.to_numpy_array(game_map.graph, nodelist=range(num_nodes))
        
        # 2. PREPARE NODE FEATURES
        # Shape: (N, 4)
        # Matrix to hold: [Ownership, Normalized Army, Threat Level, Is Border]
        node_features = np.zeros((num_nodes, 4), dtype=np.float32)
        
        # Extract raw state data once for speed
        # state[:, 0] is Owners, state[:, 1] is Army Counts
        owners = game_map.state[:, 0]
        armies = game_map.state[:, 1]
        
        # -- Global Feature Accumulators --
        my_nodes_count = 0
        my_total_army = 0
        enemy_nodes_count = 0
        enemy_total_army = 0

        for node_id in range(num_nodes):
            owner = owners[node_id]
            army_count = armies[node_id]
            
            # --- Feature 0: Ownership ---
            # 1.0 if Self, -1.0 if Enemy, 0.0 if Neutral
            if owner == current_player_id:
                node_features[node_id, 0] = 1.0
                my_nodes_count += 1
                my_total_army += army_count
            elif owner == PlayerId.NEUTRAL:
                node_features[node_id, 0] = 0.0
            else:
                node_features[node_id, 0] = -1.0
                enemy_nodes_count += 1
                enemy_total_army += army_count

            # --- Feature 1: Normalized Army Count ---
            # Scales army size between 0.0 and 1.0 based on MAX_ARMIES_CAP
            # This helps the Neural Network converge faster.
            node_features[node_id, 1] = min(army_count / self.config.MAX_ARMIES_CAP, 1.0)
            
            # --- Feature 2: Threat Level Calculation ---
            # Logic: Sum of armies in all neighboring nodes belonging to enemies.
            # This gives the AI "local vision" of danger.
            threat_sum = 0
            neighbors = list(game_map.graph.neighbors(node_id))
            
            for neighbor_id in neighbors:
                neighbor_owner = owners[neighbor_id]
                neighbor_army = armies[neighbor_id]
                
                # If neighbor is NOT me and NOT neutral, it's a threat
                if neighbor_owner != PlayerId.NEUTRAL and neighbor_owner != current_player_id:
                    threat_sum += neighbor_army
            
            # Normalize threat level similarly to army count
            node_features[node_id, 2] = min(threat_sum / self.config.MAX_ARMIES_CAP, 1.0)

            # --- Feature 3: Is Border? ---
            # 1.0 if this node is connected to at least one hostile node.
            # This helps the AI identify frontlines vs safe backlines.
            is_border = 0.0
            if owner == current_player_id:
                for neighbor_id in neighbors:
                    neighbor_owner = owners[neighbor_id]
                    if neighbor_owner != current_player_id: # Enemy or Neutral implies border
                        is_border = 1.0
                        break
            node_features[node_id, 3] = is_border

        # 3. PREPARE GLOBAL FEATURES
        # Shape: (2, 2)
        # Row 0: Self [Node Count, Total Army (norm)]
        # Row 1: Enemy [Node Count, Total Army (norm)]
        global_features = np.zeros((2, 2), dtype=np.float32)
        
        # Normalize node counts by total map size
        global_features[0, 0] = my_nodes_count / num_nodes
        # Normalize total army by an arbitrary large number (e.g., Map Size * Cap)
        max_possible_army = num_nodes * self.config.MAX_ARMIES_CAP
        global_features[0, 1] = my_total_army / max_possible_army
        
        global_features[1, 0] = enemy_nodes_count / num_nodes
        global_features[1, 1] = enemy_total_army / max_possible_army

        return {
            "node_features": node_features,
            "adjacency": adjacency.astype(np.float32),
            "global_features": global_features
        }