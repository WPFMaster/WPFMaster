import os
import argparse
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.vec_env import DummyVecEnv

from gym_env import StrategyGameEnv
from callbacks import GameStatsCallback

def validate_environment():
    """
    Checks if the custom environment follows the Gymnasium interface.
    This is critical before trying to train.
    """
    print("--- Starting Environment Validation ---")
    env = StrategyGameEnv()
    
    # It will throw an error/warning if something is wrong
    check_env(env, warn=True)
    
    # Also do a quick manual test
    obs, _ = env.reset()
    print("Observation Space Sample:", obs.keys())
    print("Action Space Sample:", env.action_space.sample())
    
    print("\n✅ Environment Verification Passed! The Env is ready for AI.")

def train_agent(total_timesteps=100000):
    """
    Trains a PPO agent on the environment.
    """
    print(f"--- Starting Training ({total_timesteps} timesteps) ---")
    
    # Vectorized environments allow for faster training
    env = DummyVecEnv([lambda: StrategyGameEnv()])
    
    # Initialize the PPO agent
    # MlpPolicy is used because our input is a set of vectors/matrices, not images
    model = PPO("MultiInputPolicy", env, tensorboard_log="./ppo_strategy_tensorboard/")
    
    my_callback = GameStatsCallback()


    # Train
    model.learn(total_timesteps=total_timesteps, callback=my_callback)
    
    # Save
    model_path = "ppo_strategy_game"
    model.save(model_path)
    print(f"✅ Model saved to {model_path}.zip")

def watch_agent():
    """
    Loads a trained model and plays one game, rendering the output.
    """
    model_path = "ppo_strategy_game.zip"
    if not os.path.exists(model_path):
        print(f"❌ Error: Model file '{model_path}' not found. Train first!")
        return

    print("--- Watching Trained Agent ---")
    
    # Create env with render capability
    env = StrategyGameEnv(render_mode="file")
    model = PPO.load("ppo_strategy_game")
    
    obs, _ = env.reset()
    terminated = False
    truncated = False
    total_reward = 0
    
    while not terminated and not truncated:
        # Predict the action (deterministic=True makes the AI play its 'best' move)
        action, _ = model.predict(obs, deterministic=True)
        
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        
        env.render()
        
    print(f"Game Over! Total Reward: {total_reward}")

if __name__ == "__main__":
    print("Select Mode:")
    print("1. Validate Environment")
    print("2. Train Agent")
    print("3. Watch Agent Play")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        validate_environment()
    elif choice == "2":
        steps = input("Enter timesteps (default 100000): ").strip()
        steps = int(steps) if steps.isdigit() else 100000
        train_agent(steps)
    elif choice == "3":
        watch_agent()
    else:
        print("Invalid choice.")