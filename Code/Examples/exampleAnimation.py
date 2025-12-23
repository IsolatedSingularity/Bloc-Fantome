"""
Quantum Chemistry Animation

This script creates a GIF animation that visualizes H2 molecule separation (bond distance vs. energy).
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Circle, Ellipse
import os

def generate_synthetic_data():
    """
    Generate synthetic data for H2 dissociation curve
    """
    print("Generating synthetic H2 data")
    distances = np.linspace(0.3, 1.9, 35)
    
    # Generate simulated energy values
    electronic_energies = -1.1 - 0.8*np.exp(-(distances-0.74)**2/0.2)
    nuclear_energies = 1.0 / distances
    total_energies = electronic_energies + nuclear_energies
    
    return distances, electronic_energies, nuclear_energies, total_energies


def animate_h2_dissociation(save_path):
    """
    Create an animation of H2 molecule separation with energy curve
    """
    print("Creating H2 dissociation animation...")
    
    # Generate data
    distances, electronic_energies, nuclear_energies, total_energies = generate_synthetic_data()
    
    try:
        # Set up the figure with two subplots
        fig = plt.figure(figsize=(14, 7))
        grid = plt.GridSpec(1, 2, width_ratios=[1, 1.2])
        
        # First subplot: Molecule visualization (simplified 2D version to avoid 3D issues)
        ax1 = fig.add_subplot(grid[0])
        ax1.set_title('H₂ Molecule Separation', fontsize=14)
        ax1.set_xlim(-2, 2)
        ax1.set_ylim(-2, 2)
        ax1.set_aspect('equal')
        ax1.set_xlabel('X (Å)', fontsize=12)
        ax1.set_ylabel('Y (Å)', fontsize=12)
        ax1.grid(True, alpha=0.3)
        
        # Second subplot: Energy curve
        ax2 = fig.add_subplot(grid[1])
        ax2.set_title('Potential Energy Curve', fontsize=14)
        ax2.set_xlabel('Bond Distance (Å)', fontsize=12)
        ax2.set_ylabel('Energy (Hartree)', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # Plot the full energy curves
        ax2.plot(distances, electronic_energies, 'b--', alpha=0.5, label='Electronic Energy')
        ax2.plot(distances, nuclear_energies, 'r--', alpha=0.5, label='Nuclear Repulsion')
        ax2.plot(distances, total_energies, 'k-', alpha=0.5, label='Total Energy')
        ax2.legend(loc='upper right', fontsize=10)
        
        # Energy curve elements
        energy_point, = ax2.plot([], [], 'ko', ms=8)
        
        # Add text annotations
        distance_text = ax1.text(0.05, 1.9, "", fontsize=10)
        energy_text = ax2.text(0.05, 0.05, "", transform=ax2.transAxes)
        
        # Points for current distance vertical line
        vertical_line, = ax2.plot([], [], 'k-', alpha=0.7)
        
        def init():
            # Return all artists that must be redrawn
            energy_point.set_data([], [])
            vertical_line.set_data([], [])
            return (energy_point, vertical_line, distance_text, energy_text)
        
        def animate(i):
            ax1.clear()
            ax1.set_title('H₂ Molecule Separation', fontsize=14)
            ax1.set_xlim(-2, 2)
            ax1.set_ylim(-2, 2)
            ax1.set_aspect('equal')
            ax1.set_xlabel('X (Å)', fontsize=12)
            ax1.set_ylabel('Y (Å)', fontsize=12)
            ax1.grid(True, alpha=0.3)
            
            # Determine current distance (oscillate back and forth)
            if i < len(distances):
                idx = i
            else:
                idx = 2*len(distances) - i - 2
                
            if idx < 0:
                idx = 0
            if idx >= len(distances):
                idx = len(distances) - 1
                
            current_distance = distances[idx]
            
            # Draw the molecular visualization in 2D
            # The atoms are on the x-axis
            h1_x = -current_distance/2
            h2_x = current_distance/2
            
            # Draw atoms as circles
            h1_circle = Circle((h1_x, 0), 0.3, fc='lightblue', ec='blue', lw=1.5)
            h2_circle = Circle((h2_x, 0), 0.3, fc='lightblue', ec='blue', lw=1.5)
            ax1.add_patch(h1_circle)
            ax1.add_patch(h2_circle)
            
            # Add labels
            ax1.text(h1_x, 0.5, 'H', fontsize=14, ha='center')
            ax1.text(h2_x, 0.5, 'H', fontsize=14, ha='center')
            
            # Draw electron cloud (simplified 2D version)
            if current_distance < 0.9:  # Bonded state
                # Draw a shared electron cloud between atoms
                center_x = (h1_x + h2_x) / 2
                width = current_distance + 0.6
                height = 0.8
                
                electron_cloud = Ellipse((center_x, 0), width, height, fc='blue', alpha=0.2)
                ax1.add_patch(electron_cloud)
            else:  # Dissociated state
                # Draw separate electron clouds
                e1_cloud = Ellipse((h1_x, 0), 0.8, 0.8, fc='blue', alpha=0.2)
                e2_cloud = Ellipse((h2_x, 0), 0.8, 0.8, fc='blue', alpha=0.2)
                ax1.add_patch(e1_cloud)
                ax1.add_patch(e2_cloud)
            
            # Draw bond line (fades as atoms separate)
            if current_distance < 1.2:
                alpha = max(0, 1 - (current_distance/1.2))
                ax1.plot([h1_x, h2_x], [0, 0], 'k-', alpha=alpha, linewidth=2)
            
            # Update energy plot point and vertical line
            energy_point.set_data([current_distance], [total_energies[idx]])
            vertical_line.set_data([current_distance, current_distance], 
                                  [min(electronic_energies)-0.1, max(nuclear_energies)+0.1])
            
            # Update text information
            distance_text.set_text(f"Bond Distance: {current_distance:.2f} Å")
            distance_text.set_position((-1.9, 1.7))  # Set fixed position
            energy_value = total_energies[idx]
            energy_text.set_text(f"Energy: {energy_value:.4f} Ha")
            
            # Add indicator showing whether atoms are bonded, stretched, or dissociated
            if current_distance < 0.7:
                state_text = "Compressed State"
                color = 'orange'
            elif current_distance < 0.9:
                state_text = "Equilibrium State"
                color = 'green'
            elif current_distance < 1.3:
                state_text = "Stretched Bond"
                color = 'blue'
            else:
                state_text = "Dissociated"
                color = 'red'
                
            ax1.text(0, -1.7, state_text, fontsize=12, ha='center', color=color, weight='bold')
            
            # Add an explanation of the electron configuration
            if current_distance < 0.9:
                e_text = "Shared Electron Cloud"
            else:
                e_text = "Separated Electron Clouds"
            ax1.text(0, -1.4, e_text, fontsize=10, ha='center', style='italic')
            
            return (energy_point, vertical_line, distance_text, energy_text)
        
        # Create the animation
        anim = animation.FuncAnimation(fig, animate, init_func=init,
                                      frames=2*len(distances)-2, interval=100, blit=False)
        
        # Save animation
        print(f"Saving H2 dissociation animation to {save_path}")
        anim.save(save_path, writer='pillow', fps=10, dpi=100)
        plt.close(fig)
        
    except Exception as e:
        print(f"Error in H2 dissociation animation: {e}")
    
    print("H2 dissociation visualization completed")





if __name__ == "__main__":
    print("Starting H2 molecule animation generation")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Generate the H2 dissociation animation
    animate_h2_dissociation(os.path.join(output_dir, 'h2_dissociation.gif'))
    print("H2 animation completed")