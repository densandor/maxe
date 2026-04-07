import numpy as np
import matplotlib.pyplot as plt

# Parameters
limitOrderLambda = 5  # typical value from FundamentalAgent
scale = 1.0 / limitOrderLambda  # scale = 0.2
midPrice = 100  # example mid-price

# Generate samples
num_samples = 10000
exp_samples = np.random.exponential(scale=scale, size=num_samples)

# Create prices (randomly placed above/below mid-price)
signs = np.random.choice([-1, 1], size=num_samples)
prices = midPrice + signs * exp_samples

# Plot the distribution
fig, ax = plt.subplots(figsize=(10, 6))

# Exponential samples distribution
ax.hist(exp_samples, bins=50, edgecolor='black', alpha=0.7, color='blue')
ax.set_xlabel('Distance from Mid-Price', fontsize=12)
ax.set_ylabel('Frequency', fontsize=12)
ax.set_title(f'Exponential Distribution (scale={scale}, lambda={limitOrderLambda})', fontsize=14)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('exponential_distribution.png', dpi=150, bbox_inches='tight')
plt.show()

# Print statistics
print(f"Exponential Distribution Statistics (scale={scale}):")
print(f"  Mean distance: {np.mean(exp_samples):.4f}")
print(f"  Median distance: {np.median(exp_samples):.4f}")
print(f"  Std dev: {np.std(exp_samples):.4f}")
print(f"\nOrder Price Statistics (mid={midPrice}):")
print(f"  Mean: {np.mean(prices):.4f}")
print(f"  Median: {np.median(prices):.4f}")
print(f"  Min: {np.min(prices):.4f}")
print(f"  Max: {np.max(prices):.4f}")
print(f"  % within 1 unit: {100 * np.mean(np.abs(prices - midPrice) <= 1):.1f}%")
print(f"  % within 5 units: {100 * np.mean(np.abs(prices - midPrice) <= 5):.1f}%")
