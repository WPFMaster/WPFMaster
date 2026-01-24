import numpy as np
import networkx as nx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

from gym_env import StrategyGameEnv
from stable_baselines3 import PPO

# --- CONFIGURATION ---
MODEL_PATH = "ppo_strategy_game"  # Path to the trained .zip file

# --- DATA MODELS ---
class ActionPayload(BaseModel):
    source_id: int
    target_id: int
    split_index: int  # 0-9 representing 10%-100%

# --- GAME SESSION MANAGER ---
class GameSession:
    def __init__(self):
        self.env = StrategyGameEnv()
        self.model = None
        self.obs = None
        self._load_model()

    def _load_model(self):
        try:
            self.model = PPO.load(MODEL_PATH)
            print("✅ AI Model loaded successfully.")
        except Exception as e:
            print(f"⚠️ Warning: Could not load AI model at {MODEL_PATH}. Auto-step will fail. Error: {e}")

    def reset(self):
        self.obs, _ = self.env.reset()
        return self._get_full_state()

    def step(self, action_vector):
        """
        Executes a step in the environment.
        action_vector: [source, target, split_idx]
        """
        self.obs, reward, terminated, truncated, info = self.env.step(action_vector)
        
        state = self._get_full_state()
        state["reward"] = float(reward)
        state["game_over"] = terminated or truncated
        state["winner"] = info.get("winner", 0)
        return state

    def auto_step(self):
        if self.model is None:
            raise HTTPException(status_code=500, detail="AI Model not loaded. Train the model first.")
        
        # Predict action
        action, _ = self.model.predict(self.obs, deterministic=True)
        return self.step(action)

    def _get_full_state(self) -> Dict[str, Any]:
        """
        Extracts serializable data for the frontend.
        """
        # Graph Structure (Nodes & Edges)
        # We send positions to help frontend render a consistent graph
        # Using a spring layout for nice visualization
        pos = nx.spring_layout(self.env.game_map.graph, seed=42) 
        
        nodes = []
        for node_id in range(self.env.config.MAX_NODES):
            owner = int(self.env.game_map.state[node_id, 0])
            army = int(self.env.game_map.state[node_id, 1])
            x, y = pos[node_id]
            
            nodes.append({
                "id": node_id,
                "owner": owner,
                "army": army,
                "x": float(x), # -1 to 1
                "y": float(y)  # -1 to 1
            })

        edges = []
        for u, v in self.env.game_map.graph.edges():
            edges.append([int(u), int(v)])

        return {
            "tick": self.env.current_tick,
            "nodes": nodes,
            "edges": edges
        }

# --- API SETUP ---
app = FastAPI()

# Enable CORS (Cross-Origin Resource Sharing)
# This allows your JS file (running on file:// or localhost:3000) to talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Session Instance
session = GameSession()

@app.get("/")
def read_root():
    return {"status": "Strategy Game Server Running"}

@app.get("/start")
def start_game():
    """Resets the game and returns initial state."""
    return session.reset()

@app.post("/step")
def player_step(payload: ActionPayload):
    """Executes a manual move provided by the frontend."""
    # Convert payload to numpy array format expected by gym
    action = np.array([payload.source_id, payload.target_id, payload.split_index])
    return session.step(action)

@app.get("/auto_step")
def ai_step():
    """Asks the loaded AI model to make a move."""
    return session.auto_step()

if __name__ == "__main__":
    import uvicorn
    # Run server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)