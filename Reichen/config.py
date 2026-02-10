"""
config.py
Central configuration and data structures for the Strategy Game.
"""

from dataclasses import dataclass
from enum import IntEnum

class PlayerId(IntEnum):
    """Identifies the owner of a node."""
    NEUTRAL = 0
    PLAYER_1 = 1
    PLAYER_2 = 2

@dataclass(frozen=True)
class Action:
    """
    Represents a single move by a player.
    
    Attributes:
        source_id (int): The ID of the node sending the army.
        target_id (int): The ID of the node receiving/being attacked.
        amount_pct (float): The percentage of the source army to send (0.0 to 1.0).
    """
    source_id: int
    target_id: int
    amount_pct: float

@dataclass(frozen=True)
class GameConfig:
    """Global constants and rules for the game engine."""
    
    # Map Generation
    MAX_NODES: int = 20
    CONNECTION_PROBABILITY: float = 0.3  # Chance of edge between two nodes
    
    # Game Loop / Time
    CYCLE_LENGTH: int = 8       # Total ticks in one cycle (0-7)
    
    # Tick Indices (0-indexed)
    # Ticks 0, 1, 2 are standard action ticks
    FILLING_TICK: int = 3       # Tick where "Big" countries get a bonus
    # Ticks 4, 5, 6 are standard action ticks
    GROWTH_TICK: int = 7        # Tick where EVERY country grows
    
    # Army Mechanics
    BIG_COUNTRY_THRESHOLD: int = 50  # Army count needed to qualify as "Big"
    
    # Growth Amounts
    SMALL_GROWTH: int = 1       # Base growth for standard nodes
    BIG_GROWTH: int = 5         # Bonus growth for big nodes or during filling phase

    PLAYER_ARMY: int = 10
    ADVANTAGE: int = 5
    
    # Limits to prevent infinite numbers in training
    MAX_ARMIES_CAP: int = 1000
    MAX_MOVES_PER_TICK: int = 3

    # Visualization / Debug
    RENDER_FPS: int = 30

    MAX_TIMEOUT_TICKS: int = 100  # Max ticks before auto-termination