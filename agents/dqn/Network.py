import torch
import torch.nn as nn


class Network(nn.Module):
    def __init__(self, state_size=2, action_size=5, hidden_size=32):
        super(Network, self).__init__()
        self.layer1 = nn.Linear(state_size, hidden_size)
        self.layer2 = nn.Linear(hidden_size, hidden_size)
        self.layer3 = nn.Linear(hidden_size, action_size)

        # Initialise weights with small values
        self._initialiseWeights()

    def _initialiseWeights(self):
        for layer in [self.layer1, self.layer2, self.layer3]:
            nn.init.xavier_uniform_(layer.weight)
            nn.init.zeros_(layer.bias)

    def forward(self, state):
        x = torch.relu(self.layer1(state))
        x = torch.relu(self.layer2(x))
        return self.layer3(x)
