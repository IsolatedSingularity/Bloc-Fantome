"""
VQE Optimization Visualizations

This script creates visualizations for the Variational Quantum Eigensolver (VQE) algorithm:
1. VQE optimization process with energy convergence and quantum state evolution
2. VQE algorithm steps explanation
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import os

def generate_synthetic_data():
    """
    Generate synthetic data for H2 dissociation curve
    """
    distances = np.linspace(0.3, 1.9, 35)
    
    # Generate simulated energy values
    electronic_energies = -1.1 - 0.8*np.exp(-(distances-0.74)**2/0.2)
    nuclear_energies = 1.0 / distances
    total_energies = electronic_energies + nuclear_energies
    
    return distances, electronic_energies, nuclear_energies, total_energies


def animate_vqe_optimization(save_path):
    """
    Create an animation of the VQE optimization process
    """
    print("Creating VQE optimization animation...")
    
    try:
        # Load or generate data
        distances, electronic_energies, nuclear_energies, total_energies = generate_synthetic_data()
        
        # Choose a specific bond distance to visualize VQE
        bond_distance_idx = 8  # Choose a distance near equilibrium
        bond_distance = distances[bond_distance_idx]
        ground_state_energy = total_energies[bond_distance_idx]
        
        # Set up the figure with two subplots
        fig = plt.figure(figsize=(14, 6))
        grid = plt.GridSpec(1, 2)
        
        # First subplot: Energy convergence
        ax1 = fig.add_subplot(grid[0])
        ax1.set_title('VQE Energy Convergence', fontsize=14)
        ax1.set_xlabel('Iteration', fontsize=12)
        ax1.set_ylabel('Energy (Hartree)', fontsize=12)
        ax1.grid(True, alpha=0.3)
        
        # Second subplot: Quantum state evolution
        ax2 = fig.add_subplot(grid[1])
        ax2.set_title(f'Quantum State Evolution (d = {bond_distance:.2f} Å)', fontsize=14)
        ax2.set_xlim(-0.1, 1.1)
        ax2.set_ylim(-0.1, 1.1)
        ax2.set_xlabel('|0101⟩ Amplitude', fontsize=12)
        ax2.set_ylabel('|1010⟩ Amplitude', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # Generate simulated VQE optimization data
        num_iterations = 15
        
        # Simulated VQE parameters (theta) over iterations
        # Starting from a state close to |0101⟩ and converging to the optimal value
        thetas = np.array([0.1 + 0.6*(1-np.exp(-i/5)) for i in range(num_iterations)])
        
        # Corresponding energies (converging to ground state)
        # Start with higher energy and converge to ground state
        vqe_energies = []
        for theta in thetas:
            # Simple model: Energy depends on theta
            # At theta=0: mostly |0101⟩, at theta=π/4: equal superposition
            energy = -0.5 - 0.3 * np.sin(2*theta)**2
            # Add noise early in the optimization
            noise = 0.1 * np.exp(-len(vqe_energies)/3) * np.random.randn()
            vqe_energies.append(energy + noise)
        
        # Add reference line for true ground state energy
        ax1.axhline(y=ground_state_energy, color='g', linestyle='--', 
                   alpha=0.7, label='True Ground State')
        
        # Energy plot elements
        energy_line, = ax1.plot([], [], 'b-', linewidth=2, label='VQE Energy')
        energy_point, = ax1.plot([], [], 'bo', ms=8)
        ax1.set_xlim(-0.5, num_iterations-0.5)
        ax1.set_ylim(min(vqe_energies)-0.1, max(vqe_energies)+0.1)
        ax1.legend(loc='upper right')
        
        # Initial state point and optimization trajectory
        trajectory_line, = ax2.plot([], [], 'b-', alpha=0.5)
        state_point, = ax2.plot([], [], 'ro', ms=10)
        
        # Draw contour plot of energy landscape in 2D
        theta_values = np.linspace(0, np.pi/2, 100)
        x_values = np.cos(theta_values)**2  # |0101⟩ probability
        y_values = np.sin(theta_values)**2  # |1010⟩ probability
        
        # Create a grid for contour plot
        X, Y = np.meshgrid(np.linspace(0, 1, 100), np.linspace(0, 1, 100))
        Z = np.zeros_like(X)
        
        # Fill Z with energy values (simple model approximation)
        for i in range(Z.shape[0]):
            for j in range(Z.shape[1]):
                # Calculate corresponding theta
                if X[i,j] + Y[i,j] > 0:  # Avoid division by zero
                    theta_approx = np.arctan2(np.sqrt(Y[i,j]), np.sqrt(X[i,j]))
                    Z[i,j] = -0.5 - 0.3 * np.sin(2*theta_approx)**2
                else:
                    Z[i,j] = -0.5
        
        # Plot energy contours
        contour = ax2.contourf(X, Y, Z, 20, cmap='viridis', alpha=0.6)
        fig.colorbar(contour, ax=ax2, label='Energy (Ha)')
        
        # Add constraint line (normalization)
        norm_x = np.linspace(0, 1, 100)
        norm_y = 1 - norm_x
        ax2.plot(norm_x, norm_y, 'k--', alpha=0.5, label='|ψ|² = 1')
        ax2.legend(loc='upper right')
        
        # Add circuit information as a text box
        ax1.text(0.05, 0.05, 
                "Circuit:\n|0101⟩ → Ry(θ) → CNOT", 
                transform=ax1.transAxes,
                bbox=dict(facecolor='white', alpha=0.7),
                fontsize=10)
        
        # Add text for current information
        iter_text = ax1.text(0.5, 0.05, "", transform=ax1.transAxes,
                            bbox=dict(facecolor='white', alpha=0.8))
        state_text = ax2.text(0.05, 0.05, "", transform=ax2.transAxes,
                             bbox=dict(facecolor='white', alpha=0.8))
        
        def init():
            # Initialize plots
            energy_line.set_data([], [])
            energy_point.set_data([], [])
            trajectory_line.set_data([], [])
            state_point.set_data([], [])
            iter_text.set_text("")
            state_text.set_text("")
            return (energy_line, energy_point, trajectory_line, state_point, iter_text, state_text)
        
        def animate(i):
            if i < len(thetas):
                # Current parameter and energy
                theta = thetas[i]
                energy = vqe_energies[i]
                
                # Calculate state components
                prob_0101 = np.cos(theta)**2
                prob_1010 = np.sin(theta)**2
                
                # Update energy convergence plot
                energy_line.set_data(range(i+1), vqe_energies[:i+1])
                energy_point.set_data(i, energy)
                
                # Update quantum state plot
                if i > 0:
                    # Plot trajectory
                    traj_x = [np.cos(t)**2 for t in thetas[:i+1]]
                    traj_y = [np.sin(t)**2 for t in thetas[:i+1]]
                    trajectory_line.set_data(traj_x, traj_y)
                
                state_point.set_data([prob_0101], [prob_1010])
                
                # Update text information
                iter_text.set_text(f"Iteration: {i}\nEnergy: {energy:.6f} Ha\nθ: {theta:.4f}")
                
                # Update quantum state text
                amp_0101 = np.cos(theta)
                amp_1010 = np.sin(theta)
                state_text.set_text(f"|ψ⟩ = {amp_0101:.4f}|0101⟩ + {amp_1010:.4f}|1010⟩\n"
                                 f"P(|0101⟩) = {prob_0101:.4f}\n"
                                 f"P(|1010⟩) = {prob_1010:.4f}")
                
                # Highlight position on constraint curve
                ax2.plot([prob_0101], [prob_1010], 'ro', ms=10)
                
            return (energy_line, energy_point, trajectory_line, state_point, iter_text, state_text)
        
        # Create animation
        anim = animation.FuncAnimation(fig, animate, init_func=init,
                                      frames=num_iterations, interval=500, blit=False)
        
        # Save animation
        print(f"Saving VQE optimization animation to {save_path}")
        try:
            anim.save(save_path, writer='pillow', fps=5, dpi=100)
        except Exception as e:
            print(f"Error saving animation: {e}")
            # Save a static image instead
            print("Saving static image instead...")
            animate(num_iterations-1)
            plt.savefig(save_path.replace('.gif', '.png'), dpi=150)
        
        plt.close(fig)
        
    except Exception as e:
        print(f"Error in VQE optimization animation: {e}")
        # Create and save a simple static image instead
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_title('VQE Optimization Process', fontsize=16)
        ax.set_xlabel('Parameter (θ)', fontsize=14)
        ax.set_ylabel('Energy', fontsize=14)
        
        # Draw a simple energy curve
        theta_values = np.linspace(0, np.pi, 100)
        energies = -0.7 - 0.3 * np.sin(theta_values)**2
        ax.plot(theta_values, energies, 'b-', linewidth=2)
        
        # Mark the minimum
        min_idx = np.argmin(energies)
        min_theta = theta_values[min_idx]
        min_energy = energies[min_idx]
        ax.plot(min_theta, min_energy, 'ro', markersize=10)
        
        # Add text explanation
        ax.text(0.1, -0.85, 
               "VQE works by finding the parameter (θ) that\nminimizes the energy expectation value.",
               fontsize=12, bbox=dict(facecolor='white', alpha=0.8))
        
        # Save static image
        plt.tight_layout()
        plt.savefig(save_path.replace('.gif', '.png'), dpi=150)
        plt.close(fig)
    
    print("VQE optimization visualization completed")


def create_vqe_steps_visualization(save_path):
    """
    Create a static visualization explaining the VQE algorithm steps
    """
    print("Creating VQE steps visualization...")
    
    # Create a figure with multiple subplots arranged vertically
    fig, axes = plt.subplots(4, 1, figsize=(10, 14))
    
    # Step 1: Molecular Hamiltonian Mapping
    ax1 = axes[0]
    ax1.set_title("Step 1: Hamiltonian Mapping", fontsize=16)
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 6)
    ax1.axis('off')
    
    # Hamiltonian mapping illustration
    ax1.text(1, 5, "Molecular Hamiltonian (Electronic Structure):", fontsize=12, weight='bold')
    ax1.text(1, 4, r"$\hat{H}_{elec} = \sum_{pq} h_{pq} a_p^\dagger a_q + \frac{1}{2}\sum_{pqrs} h_{pqrs} a_p^\dagger a_q^\dagger a_r a_s$", fontsize=12)
    
    ax1.add_patch(plt.Arrow(5, 3.5, 0, -1, width=0.3, color='black'))
    ax1.text(5.5, 3, "Jordan-Wigner Transformation", fontsize=10, style='italic')
    
    ax1.text(1, 2, "Qubit Hamiltonian:", fontsize=12, weight='bold')
    ax1.text(1, 1, r"$\hat{H}_{qubit} = \sum_i c_i \hat{P}_i$ where $\hat{P}_i$ are Pauli strings", fontsize=12)
    ax1.text(1, 0.5, r"Example: $c_1 \hat{Z}_0\hat{Z}_1 + c_2 \hat{X}_0\hat{X}_1\hat{Z}_2 + c_3 \hat{I}_0\hat{Y}_1\hat{Y}_2 + ...$", fontsize=10)
    
    # Step 2: Parameterized Circuit
    ax2 = axes[1]
    ax2.set_title("Step 2: Parameterized Quantum Circuit", fontsize=16)
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 6)
    ax2.axis('off')
    
    # Circuit illustration
    circuit_text = """
    H₂ Ansatz Circuit:
    
    |0⟩ ─[X]─────[Ry(θ)]─■─────── 
                          │
    |0⟩ ───────[Ry(θ)]───■───────
    
    |0⟩ ─[X]─────[Ry(-θ)]───■───
                            │
    |0⟩ ───────[Ry(-θ)]─────■───
    """
    ax2.text(1, 4, circuit_text, fontsize=12, family='monospace')
    
    ax2.text(1, 1.5, "State Preparation:", fontsize=12, weight='bold')
    ax2.text(1, 0.8, r"$|\psi(\theta)\rangle = $ superposition of $|0101\rangle$ and $|1010\rangle$", fontsize=12)
    ax2.text(1, 0.3, r"Represents ground state of H₂ at various bond distances", fontsize=10, style='italic')
    
    # Step 3: Energy Estimation
    ax3 = axes[2]
    ax3.set_title("Step 3: Energy Estimation", fontsize=16)
    ax3.set_xlim(0, 10)
    ax3.set_ylim(0, 6)
    ax3.axis('off')
    
    # Energy estimation illustration
    ax3.text(1, 5, "Expectation Value Calculation:", fontsize=12, weight='bold')
    ax3.text(1, 4.3, r"$E(\theta) = \langle\psi(\theta)|\hat{H}_{qubit}|\psi(\theta)\rangle = \sum_i c_i \langle\psi(\theta)|\hat{P}_i|\psi(\theta)\rangle$", fontsize=12)
    
    # Create a small grid to show measurement process
    for i in range(5):
        for j in range(3):
            if j == 0:
                # First row: Pauli strings
                if i == 0:
                    pauli = "ZZ"
                elif i == 1:
                    pauli = "XX"
                elif i == 2:
                    pauli = "YY"
                elif i == 3:
                    pauli = "ZI"
                else:
                    pauli = "IZ"
                ax3.text(i+2, 3, pauli, ha='center', fontsize=10)
            elif j == 1:
                # Second row: Coefficients
                coef = f"c{i+1}"
                ax3.text(i+2, 2.5, coef, ha='center', fontsize=10)
            else:
                # Third row: Measured values
                val = f"⟨{pauli}⟩"
                ax3.text(i+2, 2, val, ha='center', fontsize=10)
    
    ax3.add_patch(plt.Rectangle((1.8, 1.8), 5.4, 1.5, fill=False))
    
    # Show explanation of measurement
    ax3.text(1, 1.3, "For each Pauli string:", fontsize=11)
    ax3.text(1.2, 0.9, "1. Apply basis rotations (H and S gates)", fontsize=10)
    ax3.text(1.2, 0.5, "2. Measure in Z basis multiple times", fontsize=10)
    ax3.text(1.2, 0.1, "3. Calculate expectation value from statistics", fontsize=10)
    
    # Step 4: Optimization
    ax4 = axes[3]
    ax4.set_title("Step 4: Classical Optimization", fontsize=16)
    ax4.set_xlim(0, 10)
    ax4.set_ylim(0, 6)
    ax4.axis('off')
    
    # Parameter optimization illustration
    ax4.text(1, 5, "Objective: Find θ that minimizes E(θ)", fontsize=12, weight='bold')
    
    # Draw optimization curve
    theta_vals = np.linspace(0, np.pi, 100)
    energy_vals = -0.7 - 0.4 * np.sin(theta_vals)**2
    ax4.plot(theta_vals/np.pi*6 + 2, energy_vals + 3, 'b-')
    
    # Mark minimum
    min_theta = np.pi/2
    min_energy = -0.7 - 0.4 * np.sin(min_theta)**2
    ax4.plot(min_theta/np.pi*6 + 2, min_energy + 3, 'ro')
    
    # Axis labels
    ax4.text(5, 1.8, "Parameter θ", fontsize=11)
    ax4.text(1.5, 3, "Energy E(θ)", fontsize=11)
    
    # Show optimization process
    ax4.text(1, 1.2, "Optimization Algorithm (SLSQP, SPSA, etc.):", fontsize=11)
    ax4.text(1.2, 0.8, "1. Start with initial guess for θ", fontsize=10)
    ax4.text(1.2, 0.5, "2. Evaluate energy using quantum processor", fontsize=10)
    ax4.text(1.2, 0.2, "3. Update θ to minimize energy and iterate", fontsize=10)
    
    # Add title to overall figure
    fig.suptitle("Variational Quantum Eigensolver (VQE) Algorithm Steps", fontsize=18)
    
    # Save figure
    plt.tight_layout(rect=[0, 0, 1, 0.97])  # Adjust layout to make room for suptitle
    print(f"Saving VQE steps visualization to {save_path}")
    plt.savefig(save_path, dpi=300)
    plt.close(fig)
    
    print("VQE steps visualization completed")


if __name__ == "__main__":
    print("Starting VQE visualization generation")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        # Generate the VQE optimization animation
        try:
            animate_vqe_optimization(os.path.join(output_dir, 'vqe_optimization.gif'))
            print("VQE optimization animation completed successfully")
        except Exception as e:
            print(f"Error in VQE optimization animation: {e}")
        
        # Generate VQE steps visualization
        try:
            create_vqe_steps_visualization(os.path.join(output_dir, 'vqe_steps.png'))
            print("VQE steps visualization completed successfully")
        except Exception as e:
            print(f"Error in VQE steps visualization: {e}")
        
        print("All VQE visualizations completed")
        
    except Exception as e:
        print(f"Error in visualization generation: {e}")
