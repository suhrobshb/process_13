"""
Adaptive AI Decisioning - Reinforcement Learning Optimizer
=========================================================

This module implements a sophisticated reinforcement learning (RL) agent that
dynamically optimizes decision-making logic within workflows. It learns from the
outcomes of past workflow executions to make smarter choices at decision nodes,
adapting to changing patterns and improving efficiency over time.

Key Features:
-   **Q-Learning Algorithm**: Utilizes a classic, effective reinforcement learning
    algorithm to learn the value of taking specific actions in different states.
-   **Dynamic State Representation**: Converts the complex context of a live
    workflow into a simplified, hashable state representation for the learning model.
-   **Epsilon-Greedy Exploration**: Balances exploiting known good decision paths
    with exploring new ones, ensuring continuous learning and adaptation.
-   **Configurable Reward Function**: The learning process is guided by a flexible
    reward system that can be tuned to prioritize success, speed, or cost-efficiency.
-   **Persistent Learning**: The learned knowledge (the Q-table) is periodically
    saved to disk, ensuring that the agent's intelligence persists across
    application restarts.
-   **Thread-Safe Operations**: Designed to be safely used in a multi-threaded
    environment with multiple concurrent workflow executions.

This optimizer is a core component of the "Adaptive AI Decisioning" feature,
transforming static workflows into dynamic, self-improving processes.
"""

import os
import json
import logging
import random
import threading
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# --- RL Constants ---
DEFAULT_LEARNING_RATE = 0.1  # Alpha: How much to update Q-values based on new info.
DEFAULT_DISCOUNT_FACTOR = 0.95 # Gamma: How much to value future rewards.
DEFAULT_EXPLORATION_RATE = 0.1 # Epsilon: The probability of choosing a random action.

Q_TABLE_PERSISTENCE_PATH = "storage/adaptive_decisioning/q_table.json"


class RLOptimizer:
    """
    A Reinforcement Learning agent that uses Q-learning to optimize workflow decisions.
    """

    def __init__(
        self,
        learning_rate: float = DEFAULT_LEARNING_RATE,
        discount_factor: float = DEFAULT_DISCOUNT_FACTOR,
        exploration_rate: float = DEFAULT_EXPLORATION_RATE,
        persistence_path: str = Q_TABLE_PERSISTENCE_PATH,
    ):
        """
        Initializes the RL Optimizer.

        Args:
            learning_rate: The alpha value for the Q-learning algorithm.
            discount_factor: The gamma value, discounting future rewards.
            exploration_rate: The epsilon value for the epsilon-greedy strategy.
            persistence_path: The file path to save and load the Q-table.
        """
        self.alpha = learning_rate
        self.gamma = discount_factor
        self.epsilon = exploration_rate
        self.persistence_path = persistence_path
        
        # The Q-table stores the learned values.
        # Format: { state_string: { action_id: q_value, ... }, ... }
        self.q_table: Dict[str, Dict[str, float]] = {}
        self._lock = threading.Lock()  # For thread-safe updates to the Q-table
        
        self._load_q_table()

    def _get_state_representation(self, context: Dict[str, Any]) -> str:
        """
        Converts the current workflow context into a simplified, hashable state string.
        
        This is a crucial step. A good state representation captures the essential
        information needed to make a decision without being overly complex.
        
        Args:
            context: The current workflow context dictionary.

        Returns:
            A string representation of the state.
        """
        # For this implementation, we'll create a state based on the keys
        # of the context and the types of their values. A more advanced version
        # could use hashing or feature extraction.
        state_keys = sorted(context.keys())
        state_parts = [f"{key}:{type(context[key]).__name__}" for key in state_keys]
        return "|".join(state_parts)

    def _load_q_table(self):
        """Loads the Q-table from the persistence file if it exists."""
        with self._lock:
            if os.path.exists(self.persistence_path):
                try:
                    with open(self.persistence_path, 'r') as f:
                        self.q_table = json.load(f)
                    logger.info(f"Successfully loaded Q-table from {self.persistence_path}")
                except (json.JSONDecodeError, IOError) as e:
                    logger.error(f"Failed to load Q-table: {e}. Starting with an empty table.")
                    self.q_table = {}
            else:
                logger.info("No existing Q-table found. Starting with a new one.")
                self.q_table = {}

    def _save_q_table(self):
        """Saves the current Q-table to the persistence file."""
        with self._lock:
            try:
                # Ensure the directory exists
                os.makedirs(os.path.dirname(self.persistence_path), exist_ok=True)
                with open(self.persistence_path, 'w') as f:
                    json.dump(self.q_table, f, indent=2)
                logger.debug(f"Successfully saved Q-table to {self.persistence_path}")
            except IOError as e:
                logger.error(f"Failed to save Q-table: {e}")

    def choose_action(self, context: Dict[str, Any], possible_actions: List[str]) -> str:
        """
        Chooses the best action for a given state using an epsilon-greedy strategy.

        Args:
            context: The current workflow context.
            possible_actions: A list of action IDs representing the possible branches.

        Returns:
            The ID of the chosen action.
        """
        state = self._get_state_representation(context)
        
        # Ensure the state exists in the Q-table
        self.q_table.setdefault(state, {action: 0.0 for action in possible_actions})

        # Epsilon-greedy strategy
        if random.uniform(0, 1) < self.epsilon:
            # Exploration: choose a random action
            chosen_action = random.choice(possible_actions)
            logger.info(f"RL Optimizer exploring: chose random action '{chosen_action}' for state '{state}'.")
        else:
            # Exploitation: choose the best-known action
            state_actions = self.q_table[state]
            # Filter for only possible actions to handle cases where the Q-table has stale entries
            valid_actions = {act: val for act, val in state_actions.items() if act in possible_actions}
            if not valid_actions: # Fallback if no valid actions have Q-values
                 chosen_action = random.choice(possible_actions)
            else:
                chosen_action = max(valid_actions, key=valid_actions.get)
            logger.info(f"RL Optimizer exploiting: chose best action '{chosen_action}' for state '{state}'.")
            
        return chosen_action

    def update_policy(self, execution_history: List[Tuple[str, str]], reward: float):
        """
        Updates the Q-table based on the outcome of a completed workflow execution.

        Args:
            execution_history: A list of (state, action) tuples from the workflow run.
            reward: The final reward received at the end of the workflow.
        """
        logger.info(f"Updating RL policy with a final reward of {reward}.")
        with self._lock:
            # Iterate backward through the history to propagate the reward
            for i in range(len(execution_history) - 1, -1, -1):
                state, action = execution_history[i]
                
                # Get the old Q-value
                old_q_value = self.q_table.get(state, {}).get(action, 0.0)
                
                # Determine the maximum Q-value for the *next* state
                if i == len(execution_history) - 1:
                    # This is the last step, so there is no next state
                    max_future_q = 0.0
                else:
                    next_state, _ = execution_history[i+1]
                    future_rewards = self.q_table.get(next_state, {}).values()
                    max_future_q = max(future_rewards) if future_rewards else 0.0

                # Q-learning formula
                new_q_value = old_q_value + self.alpha * (reward + self.gamma * max_future_q - old_q_value)
                
                # Update the Q-table
                self.q_table.setdefault(state, {})[action] = new_q_value
                
                # The reward is only applied to the last step, subsequent steps in the
                # backward pass learn from the updated Q-values of their successors.
                reward = 0 

        # Persist the updated knowledge
        self._save_q_table()

# --- Global Singleton Instance ---
# This ensures that the entire application shares a single, stateful optimizer.
rl_optimizer = RLOptimizer()

# --- Example Usage ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    print("--- Reinforcement Learning Optimizer Demo ---")

    # Simulate a decision point in a workflow
    decision_context_1 = {"user_role": "analyst", "document_type": "invoice"}
    possible_branches_1 = ["send_to_finance", "send_to_manager_for_approval"]

    # --- Run 1: Initial decision (likely random) ---
    print("\n--- Run 1 ---")
    chosen_branch = rl_optimizer.choose_action(decision_context_1, possible_branches_1)
    print(f"Decision made: {chosen_branch}")

    # Simulate a successful workflow outcome
    history_1 = [
        (rl_optimizer._get_state_representation(decision_context_1), chosen_branch)
    ]
    # A positive reward for success
    final_reward_1 = 100.0
    rl_optimizer.update_policy(history_1, final_reward_1)
    print("Policy updated with a positive reward.")
    print("Q-Table state:", json.dumps(rl_optimizer.q_table, indent=2))

    # --- Run 2: Another decision, should now be influenced by learning ---
    print("\n--- Run 2 ---")
    # Set exploration rate to 0 to force exploitation of learned knowledge
    rl_optimizer.epsilon = 0.0
    chosen_branch_2 = rl_optimizer.choose_action(decision_context_1, possible_branches_1)
    print(f"Decision made: {chosen_branch_2}")
    print("Note: The chosen action should now be the one that was rewarded in Run 1.")

    # --- Run 3: Simulate a different context and a failure ---
    print("\n--- Run 3 ---")
    rl_optimizer.epsilon = DEFAULT_EXPLORATION_RATE # Reset epsilon
    decision_context_2 = {"user_role": "manager", "document_type": "report"}
    possible_branches_2 = ["archive_report", "publish_report"]
    
    chosen_branch_3 = rl_optimizer.choose_action(decision_context_2, possible_branches_2)
    print(f"Decision made: {chosen_branch_3}")
    
    # Simulate a failed workflow outcome
    history_2 = [
        (rl_optimizer._get_state_representation(decision_context_2), chosen_branch_3)
    ]
    # A negative reward for failure
    final_reward_2 = -50.0
    rl_optimizer.update_policy(history_2, final_reward_2)
    print("Policy updated with a negative reward.")
    print("Q-Table state:", json.dumps(rl_optimizer.q_table, indent=2))
    print("\nNote how the Q-value for the failed action is now negative.")
