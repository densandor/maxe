import collections
import random
import numpy as np
import torch


class ReplayMemory:
    """
    Experience replay memory for storing and sampling transitions.

    The replay memory stores (state, action, reward, next_state, done) tuples and provides random sampling for training. This decorrelates training samples and improves learning stability.

    Args:
        capacity (int): Maximum number of transitions to store. Default: 60
        device (torch.device): Device for tensor allocation. Default: CPU
    """

    def __init__(self, capacity=60, device=None):
        self.capacity = capacity
        self.memory = collections.deque(maxlen=capacity)
        self.device = device or torch.device("cpu")

    def add(self, state, action, reward, next_state, done):
        """
        Store a transition in the memory.
        
        This method is called after each environment step to record the
        experience for later training.
        
        Args:
            state (np.ndarray): Current state, shape (state_size,)
            action (int): Action index (0 to action_size-1)
            reward (float): Scalar reward value
            next_state (np.ndarray): Resulting state, shape (state_size,)
            done (bool): Episode termination flag
        """
        self.memory.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        """
        Sample a random batch of transitions.
        
        Samples uniformly without replacement from the memory. Returns None
        if the memory contains fewer than batch_size transitions.
        
        Args:
            batch_size (int): Number of transitions to sample
            
        Returns:
            Tuple[torch.Tensor, ...] or None: If sufficient data available:
                (states, actions, rewards, next_states, dones)
                Each tensor is on self.device and has shape (batch_size, ...)
            
            Returns None if memory size < batch_size
        """
        if len(self.memory) < batch_size:
            return None
        
        # Sample random transitions
        batch = random.sample(list(self.memory), batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        
        # Convert to PyTorch tensors on specified device
        states = torch.FloatTensor(np.array(states)).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        next_states = torch.FloatTensor(np.array(next_states)).to(self.device)
        dones = torch.FloatTensor(dones).to(self.device)
        
        return states, actions, rewards, next_states, dones
    
    def __len__(self):
        """Return number of transitions currently in memory."""
        return len(self.memory)
    
    def clear(self):
        """Clear all transitions from memory."""
        self.memory.clear()
