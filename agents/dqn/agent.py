"""
Manual Deep Q-Learning agent with explicit training control.

This module implements the core DQN training logic with explicit control over:
- Double DQN for reduced overestimation
- Target network synchronization
- Custom loss functions
- Epsilon-greedy exploration
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from .networks import DQN as QNetwork
from .replay_buffer import ReplayMemory as ReplayBuffer


class ManualDQLAgent:
    """
    Manual Deep Q-Learning agent with transparent training mechanics.
    
    This agent implements Double DQN with explicit control over all components.
    Unlike high-level RL libraries, each step (network updates, target sync,
    exploration) is visible and modifiable.
    
    Architecture:
        - Primary Q-Network: Selects and trains on actions
        - Target Q-Network: Provides stable target Q-values
        - Replay Buffer: Stores and samples experiences
        - Optimizer: Adam optimizer for gradient descent
    
    Reference: Van Hasselt et al. (2016). Deep Reinforcement Learning with 
               Double Q-learning. AAAI 2016.
    
    Args:
        state_size (int): Dimension of state space. Default: 4
        action_size (int): Number of discrete actions. Default: 3
        learning_rate (float): Adam optimizer learning rate. Default: 0.001
        gamma (float): Discount factor for future rewards. Default: 0.99
        batch_size (int): Batch size for training. Default: 32
        buffer_capacity (int): Max experiences in replay buffer. Default: 60
    """
    
    def __init__(self, state_size=4, action_size=3, learning_rate=0.001, gamma=0.99, batch_size=32, buffer_capacity=60):
        
        # Agent configuration
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.batch_size = batch_size
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Initialize networks
        self.q_network = QNetwork(state_size, action_size).to(self.device)
        self.target_network = QNetwork(state_size, action_size).to(self.device)
        # Initialize target with same weights as Q-network
        self.target_network.load_state_dict(self.q_network.state_dict())
        self.target_network.eval()  # Target network never trains
        
        # Initialize optimizer and loss
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=learning_rate)
        self.loss_fn = nn.MSELoss()
        
        # Initialize replay buffer
        self.replay_buffer = ReplayBuffer(capacity=buffer_capacity, device=self.device)
        
        # Exploration parameters (epsilon-greedy)
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        
        # Training tracking
        self.total_steps = 0
        self.training_steps = 0
    
    def select_action(self, state, training=True):
        """
        Select action using epsilon-greedy exploration (training) or greedy (evaluation).
        
        During training: With probability epsilon, select random action (explore).
                        Otherwise, select argmax Q-value (exploit).
        
        During evaluation: Always select greedy action.
        
        Args:
            state (np.ndarray): Current state, shape (state_size,)
            training (bool): If True, apply epsilon-greedy. If False, act greedily.
            
        Returns:
            int: Action index (0 to action_size-1)
        """
        if training and np.random.random() < self.epsilon:
            # Explore: random action
            return np.random.randint(0, self.action_size)
        
        # Exploit: greedy action from Q-network
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            q_values = self.q_network(state_tensor)
            action = q_values.argmax(dim=1).item()
        return action
    
    def compute_target_q_values(self, states, actions, rewards, next_states, dones):
        """
        Compute target Q-values using Double DQN.
        
        Double DQN mitigates overestimation bias by decoupling action selection
        and evaluation:
        
        1. Select best actions using PRIMARY network: argmax Q(s', a)
        2. Evaluate with TARGET network: Q_target(s', best_action)
        
        Target formula:
            y = r + γ * Q_target(s', argmax_a' Q(s', a')) * (1 - done)
        
        The (1 - done) term zeros targets for terminal states.
        
        Args:
            states (torch.Tensor): Current states, shape (batch_size, state_size)
            actions (torch.Tensor): Actions taken, shape (batch_size,)
            rewards (torch.Tensor): Rewards received, shape (batch_size,)
            next_states (torch.Tensor): Resulting states, shape (batch_size, state_size)
            dones (torch.Tensor): Terminal flags, shape (batch_size,)
            
        Returns:
            torch.Tensor: Target Q-values, shape (batch_size,)
        """
        with torch.no_grad():
            # Step 1: Select best actions using PRIMARY network
            best_actions = self.q_network(next_states).argmax(dim=1)
            
            # Step 2: Evaluate selected actions using TARGET network
            target_q_values = self.target_network(next_states)
            target_q_next = target_q_values.gather(1, best_actions.unsqueeze(1)).squeeze(1)
            
            # Step 3: Compute target Q-values with Bellman backup
            target_q = rewards + self.gamma * target_q_next * (1 - dones)
        
        return target_q
    
    def train_step(self):
        """
        Perform one training step on a batch from replay buffer.
        
        Training process:
        1. Sample random batch from replay buffer
        2. Compute Q-values for actions taken: Q(s, a)
        3. Compute target Q-values using Double DQN: y
        4. Compute loss: MSE(Q(s, a), y)
        5. Backpropagation and optimizer step
        
        Gradient clipping is applied to prevent exploding gradients.
        
        Returns:
            float or None: MSE loss for this batch, or None if insufficient data
        """
        # Check if we have enough data
        if len(self.replay_buffer) < self.batch_size:
            return None
        
        # Sample batch
        batch = self.replay_buffer.sample(self.batch_size)
        if batch is None:
            return None
        
        states, actions, rewards, next_states, dones = batch
        
        # ---- Forward Pass ----
        # Compute Q-values for sampled actions
        q_values = self.q_network(states)
        q_values_taken = q_values.gather(1, actions.unsqueeze(1)).squeeze(1)
        
        # Compute target Q-values (detached from computation graph)
        target_q = self.compute_target_q_values(states, actions, rewards, 
                                               next_states, dones)
        
        # ---- Loss Computation ----
        loss = self.loss_fn(q_values_taken, target_q)
        
        # ---- Backward Pass ----
        self.optimizer.zero_grad()
        loss.backward()
        
        # Gradient clipping to prevent exploding gradients
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), max_norm=1.0)
        
        self.optimizer.step()
        
        self.training_steps += 1
        self.total_steps += 1
        
        return loss.item()
    
    def update_target_network(self):
        """
        Synchronize target network with primary network weights.
        
        The target network is held fixed for several training steps to stabilize
        learning. Periodic synchronization prevents the target from diverging
        too far from the primary network while maintaining stability.
        
        Best practice: Update every 1000-2000 training steps depending on
        environment and network size.
        """
        self.target_network.load_state_dict(self.q_network.state_dict())
    
    def decay_epsilon(self):
        """
        Decay exploration rate over time.
        
        As training progresses, the agent gradually shifts from exploration
        (random actions) to exploitation (learned policy). Epsilon decays
        multiplicatively each call: epsilon *= epsilon_decay
        
        Bottoms out at epsilon_min (usually 1-5%) to maintain some exploration.
        """
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
    
    def save_checkpoint(self, filepath):
        """
        Save agent state for resuming training.
        
        Args:
            filepath (str): Path where to save the checkpoint
        """
        checkpoint = {
            'q_network_state': self.q_network.state_dict(),
            'target_network_state': self.target_network.state_dict(),
            'optimizer_state': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'total_steps': self.total_steps,
            'training_steps': self.training_steps,
        }
        torch.save(checkpoint, filepath)
    
    def load_checkpoint(self, filepath):
        """
        Load agent state from checkpoint.
        
        Args:
            filepath (str): Path to load checkpoint from
        """
        checkpoint = torch.load(filepath, map_location=self.device)
        self.q_network.load_state_dict(checkpoint['q_network_state'])
        self.target_network.load_state_dict(checkpoint['target_network_state'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state'])
        self.epsilon = checkpoint['epsilon']
        self.total_steps = checkpoint['total_steps']
        self.training_steps = checkpoint['training_steps']
