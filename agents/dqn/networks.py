import torch
import torch.nn as nn


class DQN(nn.Module):
    """
    Neural network for Q-value approximation in discrete action spaces.

    Architecture: Input (state_size) → ReLU → ReLU → Output (action_size)

    This network maps states to Q-values for each action. Used as both the primary network and target network in DQN training.

    Args:
        state_size (int): Dimension of state space. Default: 4
        action_size (int): Number of discrete actions. Default: 3
        hidden_size (int): Number of units in hidden layers. Default: 128
    """
    
    def __init__(self, state_size=4, action_size=3, hidden_size=128):
        super(DQN, self).__init__()
        self.layer1 = nn.Linear(state_size, hidden_size)
        self.layer2 = nn.Linear(hidden_size, hidden_size)
        self.layer3 = nn.Linear(hidden_size, action_size)

        # Optional: Initialize weights with small values for stability
        self._initialize_weights()

    def _initialize_weights(self):
        """Initialize network weights using Xavier uniform initialization."""
        for layer in [self.layer1, self.layer2, self.layer3]:
            nn.init.xavier_uniform_(layer.weight)
            nn.init.zeros_(layer.bias)
    
    def forward(self, state):
        """
        Forward pass through the network.
        
        Args:
            state: Input state tensor of shape (batch_size, state_size)
            
        Returns:
            Q-values for each action, shape (batch_size, action_size)
        """
        x = torch.relu(self.layer1(state))
        x = torch.relu(self.layer2(x))
        return self.layer3(x)