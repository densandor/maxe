import numpy as np
import matplotlib.pyplot as plt


def plot_exponential_pdf(scale=1.0, samples=10000):
    
    # Generate samples
    data = np.random.exponential(scale=scale, size=samples)
    
    # Create figure
    plt.figure(figsize=(10, 6))
    
    # Plot histogram of samples
    plt.hist(data, bins=50, density=True, alpha=0.7, label='Samples', color='blue', edgecolor='black')
    
    # Plot theoretical PDF
    x = np.linspace(0, np.max(data) * 0.95, 1000)
    pdf = (1.0 / scale) * np.exp(-x / scale)
    plt.plot(x, pdf, 'r-', linewidth=2, label=f'Theoretical PDF (scale={scale})')
    
    plt.xlabel('Value')
    plt.ylabel('Probability Density')
    plt.title(f'Exponential Distribution PDF (scale={scale})')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()


def plot_symmetric_exponential_pdf(center=0.0, scale=1.0, samples=10000):
    
    # Generate samples: Laplace distribution
    # Sample: center + exponential(scale) with prob 0.5, center - exponential(scale) with prob 0.5
    exp_samples = np.random.exponential(scale=scale, size=samples)
    signs = np.random.choice([-1, 1], size=samples)
    data = center + signs * exp_samples
    
    # Create figure
    plt.figure(figsize=(10, 6))
    
    # Plot histogram of samples
    plt.hist(data, bins=50, density=True, alpha=0.7, label='Samples', color='blue', edgecolor='black')
    
    # Plot theoretical PDF
    x_range = np.max(np.abs(data - center))
    x = np.linspace(center - x_range * 0.95, center + x_range * 0.95, 1000)
    pdf = (1.0 / (2.0 * scale)) * np.exp(-np.abs(x - center) / scale)
    plt.plot(x, pdf, 'r-', linewidth=2, label=f'Theoretical PDF (center={center}, scale={scale})')
    
    plt.axvline(center, color='green', linestyle='--', linewidth=2, label=f'Center c={center}')
    plt.xlabel('Value')
    plt.ylabel('Probability Density')
    plt.title(f'Symmetric Exponential (Laplace) Distribution PDF')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Plot exponential distribution PDF')
    parser.add_argument('--mode', type=str, default='asymmetric', choices=['asymmetric', 'symmetric'], help='Distribution type (default: asymmetric)')
    parser.add_argument('--center', type=float, default=0.0, help='Center point c for symmetric distribution (default: 0.0)')
    parser.add_argument('--scale', type=float, default=1.0, help='Scale parameter (default: 1.0)')
    parser.add_argument('--samples', type=int, default=10000, help='Number of samples (default: 10000)')
    
    args = parser.parse_args()
    
    if args.mode == 'symmetric':
        plot_symmetric_exponential_pdf(center=args.center, scale=args.scale, samples=args.samples)
    else:
        plot_exponential_pdf(scale=args.scale, samples=args.samples)
