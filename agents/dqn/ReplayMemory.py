import collections
import random
import numpy as np
import torch


class ReplayMemory:
    def __init__(self, capacity):
        self.memory = collections.deque(maxlen=capacity)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def add(self, state, action, reward, next_state):
        self.memory.append((state, action, reward, next_state))

    def sample(self, batchSize):
        if len(self.memory) < batchSize:
            return None
        
        # Sample random transitions
        batch = random.sample(list(self.memory), batchSize)
        states, actions, rewards, nextStates = zip(*batch)
        
        # Convert to PyTorch tensors on specified device
        states = torch.FloatTensor(np.array(states)).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        nextStates = torch.FloatTensor(np.array(nextStates)).to(self.device)
        
        return states, actions, rewards, nextStates
    
    def __len__(self):
        return len(self.memory)
