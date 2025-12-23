"""
Example Quantum Circuits - Compilation from LDPC Code Analysis

This file compiles all quantum circuit implementations from the LDPC code analysis project.
It includes both Qiskit circuit implementations and manual circuit visualizations for:
- Cavity-mediated quantum gates
- GHZ state preparation circuits
- Error correction circuits
- Syndrome extraction circuits

All circuits are extracted from the original analysis without modification.
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch
import matplotlib.patches as mpatches
import os

# Import Qiskit components (with fallback for manual drawing if not available)
try:
    from qiskit import QuantumCircuit, ClassicalRegister, QuantumRegister
    from qiskit.visualization import circuit_drawer
    from qiskit.circuit.library import TwoLocal, RealAmplitudes
    QISKIT_AVAILABLE = True
except ImportError:
    print("Qiskit not available. Using manual circuit visualizations only.")
    QISKIT_AVAILABLE = False

# Set up the color palettes
seqCmap = sns.color_palette("mako", as_cmap=True)
divCmap = sns.cubehelix_palette(start=.5, rot=-.5, as_cmap=True)
lightCmap = sns.cubehelix_palette(start=2, rot=0, dark=0, light=.95, reverse=True, as_cmap=True)

# ============================================================================
# CAVITY-MEDIATED QUANTUM GATES
# ============================================================================

def create_cavity_mediated_cnot():
    """
    Create Qiskit circuit for cavity-mediated CNOT gate
    """
    print("Creating cavity-mediated CNOT circuit...")
    
    if QISKIT_AVAILABLE:
        # Create quantum circuit with 2 atoms + 1 cavity mode
        qreg_atoms = QuantumRegister(2, 'atom')
        qreg_cavity = QuantumRegister(1, 'cavity')
        circuit = QuantumCircuit(qreg_atoms, qreg_cavity)
        
        # Cavity-mediated CNOT implementation
        # Step 1: Entangle control atom with cavity
        circuit.h(qreg_cavity[0])  # Put cavity in superposition
        circuit.cx(qreg_atoms[0], qreg_cavity[0])  # Control atom - cavity
        
        # Step 2: Controlled rotation on target
        circuit.cry(np.pi, qreg_cavity[0], qreg_atoms[1])  # Cavity controls target
        
        # Step 3: Disentangle cavity
        circuit.cx(qreg_atoms[0], qreg_cavity[0])
        circuit.h(qreg_cavity[0])
        
        # Add measurement (optional)
        creg = ClassicalRegister(2, 'result')
        circuit.add_register(creg)
        circuit.measure(qreg_atoms, creg)
        
        # Draw circuit
        circuit_fig = circuit_drawer(circuit, output='mpl', style='iqx', fold=100)
        
        # Save the circuit
        save_path = 'cavity_cnot_circuit.png'
        circuit_fig.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close(circuit_fig)
        
        print(f"Cavity-mediated CNOT circuit saved to {save_path}")
        return circuit
    
    else:
        return create_manual_circuit_cnot()


def create_manual_circuit_cnot():
    """
    Create manual circuit visualization for cavity-mediated CNOT
    """
    print("Creating manual cavity-mediated CNOT circuit...")
    
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))
    
    # Circuit parameters
    n_qubits = 3  # 2 atoms + 1 cavity
    n_steps = 8
    
    qubit_labels = ['Control Atom', 'Target Atom', 'Cavity Mode']
    colors = [seqCmap(0.8), seqCmap(0.6), lightCmap(0.3)]
    
    # Draw horizontal lines for qubits
    for i in range(n_qubits):
        ax.plot([0, n_steps], [i, i], color=colors[i], linewidth=3, alpha=0.8)
        ax.text(-0.5, i, qubit_labels[i], ha='right', va='center', fontsize=12, fontweight='bold')
    
    # Gate positions
    gates = [
        (1, 2, 'H'),      # Hadamard on cavity
        (2, [0, 2], 'CNOT'),  # Control-cavity CNOT
        (4, [2, 1], 'CRY'),   # Cavity-controlled rotation
        (6, [0, 2], 'CNOT'),  # Control-cavity CNOT
        (7, 2, 'H'),      # Hadamard on cavity
    ]
    
    for gate in gates:
        time, qubits, gate_type = gate
        
        if gate_type == 'H':
            # Hadamard gate
            rect = plt.Rectangle((time-0.15, qubits-0.15), 0.3, 0.3, 
                               facecolor=lightCmap(0.3), edgecolor='black', linewidth=2)
            ax.add_patch(rect)
            ax.text(time, qubits, 'H', ha='center', va='center', fontsize=12, fontweight='bold')
            
        elif gate_type == 'CNOT':
            # CNOT gate
            control, target = qubits
            # Control dot
            ax.add_patch(plt.Circle((time, control), 0.1, color='black'))
            # Target circle
            ax.add_patch(plt.Circle((time, target), 0.15, fill=False, edgecolor='black', linewidth=2))
            ax.plot([time-0.1, time+0.1], [target, target], 'k-', linewidth=2)
            ax.plot([time, time], [target-0.1, target+0.1], 'k-', linewidth=2)
            # Connection line
            ax.plot([time, time], [min(control, target)+0.1, max(control, target)-0.1], 'k-', linewidth=1)
            
        elif gate_type == 'CRY':
            # Controlled rotation
            control, target = qubits
            # Control dot
            ax.add_patch(plt.Circle((time, control), 0.1, color='black'))
            # Target rotation gate
            rect = plt.Rectangle((time-0.15, target-0.15), 0.3, 0.3, 
                               facecolor=divCmap(0.5), edgecolor='black', linewidth=2)
            ax.add_patch(rect)
            ax.text(time, target, 'RY', ha='center', va='center', fontsize=10, fontweight='bold')
            # Connection line
            ax.plot([time, time], [min(control, target)+0.1, max(control, target)-0.1], 'k-', linewidth=1)
    
    # Add step labels
    step_labels = ['Init', 'H', 'CNOT₁', '', 'CRY', '', 'CNOT₂', 'H']
    for i, label in enumerate(step_labels):
        if label:
            ax.text(i, -0.7, label, ha='center', va='center', fontsize=11, 
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
    
    # Formatting
    ax.set_xlim(-1, n_steps)
    ax.set_ylim(-1, n_qubits)
    ax.set_title('Cavity-Mediated CNOT Gate Implementation\n' +
                 'Non-Local Quantum Gate via Optical Cavity', fontsize=16)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Add explanation
    explanation = ("1. Initialize cavity in superposition (H)\n"
                  "2. Entangle control atom with cavity (CNOT₁)\n" 
                  "3. Cavity-controlled rotation on target (CRY)\n"
                  "4. Disentangle control from cavity (CNOT₂)\n"
                  "5. Return cavity to ground state (H)")
    
    ax.text(0.02, 0.02, explanation, transform=ax.transAxes, fontsize=11,
           bbox=dict(boxstyle='round', facecolor=lightCmap(0.1), alpha=0.8),
           verticalalignment='bottom')
    
    plt.tight_layout()
    
    # Save the plot
    save_path = 'cavity_cnot_circuit_manual.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Manual cavity-mediated CNOT circuit saved to {save_path}")
    return "Manual circuit visualization created"

# ============================================================================
# GHZ STATE PREPARATION CIRCUITS
# ============================================================================

def create_ghz_preparation_circuit():
    """
    Create quantum circuit for GHZ state preparation
    """
    print("Creating GHZ preparation circuit...")
    
    if QISKIT_AVAILABLE:
        n_qubits = 5
        qreg = QuantumRegister(n_qubits, 'q')
        creg = ClassicalRegister(n_qubits, 'c')
        circuit = QuantumCircuit(qreg, creg)
        
        # GHZ state preparation: |00000⟩ + |11111⟩
        circuit.h(qreg[0])  # Put first qubit in superposition
        
        # Entangle all other qubits with the first
        for i in range(1, n_qubits):
            circuit.cx(qreg[0], qreg[i])
        
        # Add measurement
        circuit.measure(qreg, creg)
        
        # Draw circuit
        circuit_fig = circuit_drawer(circuit, output='mpl', style='iqx', fold=100)
        
        # Save the circuit
        save_path = 'ghz_preparation_circuit.png'
        circuit_fig.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close(circuit_fig)
        
        print(f"GHZ preparation circuit saved to {save_path}")
        return circuit
    
    else:
        return create_manual_ghz_circuit()


def create_manual_ghz_circuit():
    """
    Create manual GHZ preparation circuit visualization
    """
    print("Creating manual GHZ preparation circuit...")
    
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))
    
    n_qubits = 5
    n_steps = 7
    
    # Draw qubit lines
    for i in range(n_qubits):
        ax.plot([0, n_steps], [i, i], color=seqCmap(0.8), linewidth=3, alpha=0.8)
        ax.text(-0.3, i, f'$|q_{i}\\rangle$', ha='right', va='center', fontsize=12, fontweight='bold')
    
    # Initial state labels
    for i in range(n_qubits):
        ax.text(0.5, i, '|0⟩', ha='center', va='center', fontsize=11,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Hadamard gate on first qubit
    h_rect = plt.Rectangle((1-0.15, 0-0.15), 0.3, 0.3, 
                          facecolor=lightCmap(0.3), edgecolor='black', linewidth=2)
    ax.add_patch(h_rect)
    ax.text(1, 0, 'H', ha='center', va='center', fontsize=12, fontweight='bold')
    
    # CNOT gates
    cnot_positions = [2, 3, 4, 5]
    for i, time in enumerate(cnot_positions):
        target_qubit = i + 1
        
        # Control dot on qubit 0
        ax.add_patch(plt.Circle((time, 0), 0.1, color='black'))
        
        # Target on other qubits
        ax.add_patch(plt.Circle((time, target_qubit), 0.15, fill=False, edgecolor='black', linewidth=2))
        ax.plot([time-0.1, time+0.1], [target_qubit, target_qubit], 'k-', linewidth=2)
        ax.plot([time, time], [target_qubit-0.1, target_qubit+0.1], 'k-', linewidth=2)
        
        # Connection line
        ax.plot([time, time], [0.1, target_qubit-0.1], 'k-', linewidth=1)
    
    # Final state annotation
    final_time = 6
    ax.text(final_time, n_qubits/2, r'$|\psi_{GHZ}\rangle = \frac{1}{\sqrt{2}}(|00000\rangle + |11111\rangle)$', 
           ha='center', va='center', fontsize=14, fontweight='bold',
           bbox=dict(boxstyle='round', facecolor=seqCmap(0.2), alpha=0.3))
    
    # Formatting
    ax.set_xlim(-0.5, n_steps)
    ax.set_ylim(-0.5, n_qubits + 0.5)
    ax.set_title('5-Qubit GHZ State Preparation Circuit\n' +
                 'Essential Building Block for Quantum LDPC Codes', fontsize=16)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Add step annotations
    steps = ['Init', 'H', 'CNOT₁', 'CNOT₂', 'CNOT₃', 'CNOT₄', 'GHZ']
    for i, step in enumerate(steps):
        ax.text(i, -0.8, step, ha='center', va='center', fontsize=11,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
    
    plt.tight_layout()
    
    # Save the plot
    save_path = 'ghz_preparation_circuit_manual.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Manual GHZ preparation circuit saved to {save_path}")
    return "Manual GHZ circuit visualization created"

# ============================================================================
# ERROR CORRECTION CIRCUITS
# ============================================================================

def create_error_correction_circuit():
    """
    Create quantum circuit for basic error correction
    """
    print("Creating error correction circuit...")
    
    if QISKIT_AVAILABLE:
        # 3-qubit bit flip code
        qreg_data = QuantumRegister(3, 'data')
        qreg_ancilla = QuantumRegister(2, 'ancilla')
        creg_syndrome = ClassicalRegister(2, 'syndrome')
        circuit = QuantumCircuit(qreg_data, qreg_ancilla, creg_syndrome)
        
        # Encode logical |0⟩ -> |000⟩
        # (Initial state is already |000⟩)
        
        # Syndrome extraction
        circuit.cx(qreg_data[0], qreg_ancilla[0])
        circuit.cx(qreg_data[1], qreg_ancilla[0])
        circuit.cx(qreg_data[1], qreg_ancilla[1])
        circuit.cx(qreg_data[2], qreg_ancilla[1])
        
        # Measure syndrome
        circuit.measure(qreg_ancilla, creg_syndrome)
        
        # Draw circuit
        circuit_fig = circuit_drawer(circuit, output='mpl', style='iqx', fold=100)
        
        # Save the circuit
        save_path = 'error_correction_circuit.png'
        circuit_fig.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close(circuit_fig)
        
        print(f"Error correction circuit saved to {save_path}")
        return circuit
    
    else:
        return create_manual_error_correction_circuit()


def create_manual_error_correction_circuit():
    """
    Create manual error correction circuit visualization
    """
    print("Creating manual error correction circuit...")
    
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))
    
    n_data_qubits = 3
    n_ancilla_qubits = 2
    n_steps = 6
    
    # Draw data qubit lines
    for i in range(n_data_qubits):
        ax.plot([0, n_steps], [i, i], color=seqCmap(0.8), linewidth=3, alpha=0.8)
        ax.text(-0.3, i, f'$d_{i}$', ha='right', va='center', fontsize=12, fontweight='bold')
    
    # Draw ancilla qubit lines
    for i in range(n_ancilla_qubits):
        y_pos = n_data_qubits + i
        ax.plot([0, n_steps], [y_pos, y_pos], color=divCmap(0.6), linewidth=3, alpha=0.8)
        ax.text(-0.3, y_pos, f'$a_{i}$', ha='right', va='center', fontsize=12, fontweight='bold')
    
    # Syndrome extraction gates
    # Parity check 1: d0 ⊕ d1
    time1 = 2
    ax.add_patch(plt.Circle((time1, 0), 0.1, color='black'))  # Control on d0
    ax.add_patch(plt.Circle((time1, 3), 0.15, fill=False, edgecolor='black', linewidth=2))  # Target on a0
    ax.plot([time1-0.1, time1+0.1], [3, 3], 'k-', linewidth=2)
    ax.plot([time1, time1], [2.9, 3.1], 'k-', linewidth=2)
    ax.plot([time1, time1], [0.1, 2.9], 'k-', linewidth=1)
    
    ax.add_patch(plt.Circle((time1+0.5, 1), 0.1, color='black'))  # Control on d1
    ax.add_patch(plt.Circle((time1+0.5, 3), 0.15, fill=False, edgecolor='black', linewidth=2))  # Target on a0
    ax.plot([time1+0.5-0.1, time1+0.5+0.1], [3, 3], 'k-', linewidth=2)
    ax.plot([time1+0.5, time1+0.5], [2.9, 3.1], 'k-', linewidth=2)
    ax.plot([time1+0.5, time1+0.5], [1.1, 2.9], 'k-', linewidth=1)
    
    # Parity check 2: d1 ⊕ d2
    time2 = 4
    ax.add_patch(plt.Circle((time2, 1), 0.1, color='black'))  # Control on d1
    ax.add_patch(plt.Circle((time2, 4), 0.15, fill=False, edgecolor='black', linewidth=2))  # Target on a1
    ax.plot([time2-0.1, time2+0.1], [4, 4], 'k-', linewidth=2)
    ax.plot([time2, time2], [3.9, 4.1], 'k-', linewidth=2)
    ax.plot([time2, time2], [1.1, 3.9], 'k-', linewidth=1)
    
    ax.add_patch(plt.Circle((time2+0.5, 2), 0.1, color='black'))  # Control on d2
    ax.add_patch(plt.Circle((time2+0.5, 4), 0.15, fill=False, edgecolor='black', linewidth=2))  # Target on a1
    ax.plot([time2+0.5-0.1, time2+0.5+0.1], [4, 4], 'k-', linewidth=2)
    ax.plot([time2+0.5, time2+0.5], [3.9, 4.1], 'k-', linewidth=2)
    ax.plot([time2+0.5, time2+0.5], [2.1, 3.9], 'k-', linewidth=1)
    
    # Measurements
    meas_time = 5.5
    for i in range(n_ancilla_qubits):
        y_pos = n_data_qubits + i
        meas_rect = plt.Rectangle((meas_time-0.15, y_pos-0.15), 0.3, 0.3, 
                                 facecolor=divCmap(0.5), edgecolor='black', linewidth=2)
        ax.add_patch(meas_rect)
        ax.text(meas_time, y_pos, 'M', ha='center', va='center', fontsize=10, fontweight='bold')
    
    # Formatting
    ax.set_xlim(-0.5, n_steps + 0.5)
    ax.set_ylim(-0.5, n_data_qubits + n_ancilla_qubits)
    ax.set_title('3-Qubit Error Correction Circuit\n' +
                 'Syndrome Extraction for Bit-Flip Code', fontsize=16)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Add syndrome lookup table
    syndrome_table = ("Syndrome Lookup:\n"
                     "00 → No error\n"
                     "10 → Error on d₀\n" 
                     "11 → Error on d₁\n"
                     "01 → Error on d₂")
    
    ax.text(0.02, 0.98, syndrome_table, transform=ax.transAxes, fontsize=11,
           bbox=dict(boxstyle='round', facecolor=lightCmap(0.1), alpha=0.8),
           verticalalignment='top')
    
    plt.tight_layout()
    
    # Save the plot
    save_path = 'error_correction_circuit_manual.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Manual error correction circuit saved to {save_path}")
    return "Manual error correction circuit visualization created"

# ============================================================================
# SYNDROME EXTRACTION CIRCUITS
# ============================================================================

def create_syndrome_extraction_circuit():
    """
    Create visualization of fault-tolerant syndrome extraction circuit
    """
    print("Creating syndrome extraction circuit visualization...")
    
    fig, ax = plt.subplots(1, 1, figsize=(16, 10))
    
    # Circuit parameters
    n_data_qubits = 7  # Example: 7-qubit code
    n_ancilla_qubits = 3  # Syndrome qubits
    n_time_steps = 8
    
    # Define qubit positions
    data_y_positions = np.arange(n_data_qubits)
    ancilla_y_positions = np.arange(n_data_qubits, n_data_qubits + n_ancilla_qubits)
    all_y_positions = np.concatenate([data_y_positions, ancilla_y_positions])
    
    # Draw horizontal qubit lines
    for i, y in enumerate(all_y_positions):
        ax.plot([0, n_time_steps], [y, y], 'k-', linewidth=2, alpha=0.8)
        
        # Label qubits
        if y < n_data_qubits:
            ax.text(-0.5, y, f'$|d_{i}\\rangle$', ha='right', va='center', fontsize=12)
        else:
            ax.text(-0.5, y, f'$|a_{y-n_data_qubits}\\rangle$', ha='right', va='center', fontsize=12)
    
    # Define parity check structure (example for 7-qubit Steane code)
    parity_checks = [
        [0, 2, 4, 6],  # X-type stabilizer 1
        [1, 3, 5, 6],  # X-type stabilizer 2  
        [0, 1, 4, 5]   # X-type stabilizer 3
    ]
    
    # Draw syndrome extraction gates
    gate_times = [1, 3, 5]  # Time steps for syndrome extraction
    
    for check_idx, (time, check_qubits) in enumerate(zip(gate_times, parity_checks)):
        ancilla_qubit = n_data_qubits + check_idx
        
        # Hadamard on ancilla (initialization)
        h_rect = FancyBboxPatch((time-0.15, ancilla_qubit-0.15), 0.3, 0.3,
                               boxstyle="round,pad=0.02", 
                               facecolor=lightCmap(0.3), edgecolor='black')
        ax.add_patch(h_rect)
        ax.text(time, ancilla_qubit, 'H', ha='center', va='center', fontsize=10, fontweight='bold')
        
        # CNOT gates to data qubits
        for data_qubit in check_qubits:
            # Control dot on ancilla
            control_circle = Circle((time, ancilla_qubit), 0.1, color='black')
            ax.add_patch(control_circle)
            
            # Target on data qubit
            target_circle = Circle((time, data_qubit), 0.15, fill=False, edgecolor='black', linewidth=2)
            ax.add_patch(target_circle)
            ax.plot([time-0.1, time+0.1], [data_qubit, data_qubit], 'k-', linewidth=2)
            ax.plot([time, time], [data_qubit-0.1, data_qubit+0.1], 'k-', linewidth=2)
            
            # Connection line
            ax.plot([time, time], [min(ancilla_qubit, data_qubit)+0.1, 
                    max(ancilla_qubit, data_qubit)-0.1], 'k-', linewidth=1)
    
    # Measurement operations
    meas_time = 7
    for i in range(n_ancilla_qubits):
        ancilla_qubit = n_data_qubits + i
        
        # Measurement box
        meas_rect = FancyBboxPatch((meas_time-0.2, ancilla_qubit-0.2), 0.4, 0.4,
                                  boxstyle="round,pad=0.02", 
                                  facecolor=divCmap(0.5), edgecolor='black')
        ax.add_patch(meas_rect)
        ax.text(meas_time, ancilla_qubit, 'M', ha='center', va='center', 
               fontsize=10, fontweight='bold')
        
        # Classical bit output
        ax.plot([meas_time+0.2, meas_time+0.8], [ancilla_qubit, ancilla_qubit], 
               'k-', linewidth=3)
        ax.text(meas_time+1, ancilla_qubit, f'$s_{i}$', ha='left', va='center', fontsize=12)
    
    # Add error detection indicators
    for i, check_qubits in enumerate(parity_checks):
        y_pos = n_data_qubits + i
        # Show which data qubits are involved in each check
        for q in check_qubits:
            ax.plot([gate_times[i], gate_times[i]], [q-0.05, q+0.05], 
                   color=seqCmap(0.8), linewidth=4, alpha=0.7)
    
    # Formatting
    ax.set_xlim(-1, n_time_steps + 1.5)
    ax.set_ylim(-0.5, len(all_y_positions) - 0.5)
    ax.set_xlabel('Time Steps', fontsize=14)
    ax.set_title('Fault-Tolerant Syndrome Extraction Circuit\n' +
                 'DiVincenzo-Aliferis Protocol for Quantum LDPC Codes', fontsize=16)
    ax.set_aspect('equal')
    
    # Remove y-axis ticks
    ax.set_yticks([])
    
    # Add legend
    legend_elements = [
        mpatches.Rectangle((0, 0), 1, 1, facecolor=lightCmap(0.3), label='Hadamard Gate'),
        mpatches.Circle((0, 0), 0.1, facecolor='black', label='CNOT Control'),
        mpatches.Circle((0, 0), 0.1, facecolor='white', edgecolor='black', label='CNOT Target'),
        mpatches.Rectangle((0, 0), 1, 1, facecolor=divCmap(0.5), label='Measurement')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=11)
    
    # Add syndrome equations
    ax.text(0.02, 0.98, 'Syndrome Equations:\n' +
                        r'$s_0 = X_0 X_2 X_4 X_6$' + '\n' +
                        r'$s_1 = X_1 X_3 X_5 X_6$' + '\n' +
                        r'$s_2 = X_0 X_1 X_4 X_5$',
           transform=ax.transAxes, fontsize=12,
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
           verticalalignment='top')
    
    plt.tight_layout()
    
    # Save the plot
    save_path = 'syndrome_extraction_circuit.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Syndrome extraction circuit saved to {save_path}")
    return "Syndrome extraction circuit visualization created"

# ============================================================================
# ADDITIONAL QISKIT CIRCUIT EXAMPLES
# ============================================================================

def create_steane_code_circuit():
    """
    Create a Steane 7-qubit error correction code circuit (if Qiskit available)
    """
    if not QISKIT_AVAILABLE:
        print("Qiskit not available for Steane code circuit")
        return None
    
    print("Creating Steane 7-qubit code circuit...")
    
    # Create circuit for Steane code
    data_qubits = QuantumRegister(7, 'data')
    ancilla_x = QuantumRegister(3, 'anc_x')  # X syndrome qubits
    ancilla_z = QuantumRegister(3, 'anc_z')  # Z syndrome qubits
    syndrome_bits = ClassicalRegister(6, 'syndrome')
    
    circuit = QuantumCircuit(data_qubits, ancilla_x, ancilla_z, syndrome_bits)
    
    # Encode logical |0⟩ (identity for Steane code)
    # Initial state |0000000⟩ is already a valid codeword
    
    # X syndrome extraction
    x_checks = [[0, 2, 4, 6], [1, 3, 5, 6], [0, 1, 4, 5]]
    for i, check in enumerate(x_checks):
        circuit.h(ancilla_x[i])
        for qubit in check:
            circuit.cx(ancilla_x[i], data_qubits[qubit])
        circuit.h(ancilla_x[i])
        circuit.measure(ancilla_x[i], syndrome_bits[i])
    
    # Z syndrome extraction  
    z_checks = [[0, 2, 4, 6], [1, 3, 5, 6], [0, 1, 4, 5]]
    for i, check in enumerate(z_checks):
        for qubit in check:
            circuit.cx(data_qubits[qubit], ancilla_z[i])
        circuit.measure(ancilla_z[i], syndrome_bits[i+3])
    
    # Draw and save circuit
    circuit_fig = circuit_drawer(circuit, output='mpl', style='iqx', fold=100)
    save_path = 'steane_code_circuit.png'
    circuit_fig.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close(circuit_fig)
    
    print(f"Steane code circuit saved to {save_path}")
    return circuit

def create_bell_state_circuit():
    """
    Create a simple Bell state preparation circuit
    """
    if not QISKIT_AVAILABLE:
        print("Qiskit not available for Bell state circuit")
        return None
    
    print("Creating Bell state circuit...")
    
    # Create 2-qubit circuit
    qreg = QuantumRegister(2, 'q')
    creg = ClassicalRegister(2, 'c')
    circuit = QuantumCircuit(qreg, creg)
    
    # Bell state preparation: |00⟩ + |11⟩
    circuit.h(qreg[0])      # Hadamard on first qubit
    circuit.cx(qreg[0], qreg[1])  # CNOT gate
    
    # Measurement
    circuit.measure(qreg, creg)
    
    # Draw and save circuit
    circuit_fig = circuit_drawer(circuit, output='mpl', style='iqx')
    save_path = 'bell_state_circuit.png'
    circuit_fig.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close(circuit_fig)
    
    print(f"Bell state circuit saved to {save_path}")
    return circuit

# ============================================================================
# MAIN EXECUTION FUNCTIONS
# ============================================================================

def create_all_circuits():
    """
    Create all quantum circuits and visualizations
    """
    print("Creating all quantum circuits from LDPC analysis...")
    print("=" * 60)
    
    circuits = {}
    
    # Cavity-mediated gates
    print("\n1. Cavity-Mediated Quantum Gates:")
    circuits['cavity_cnot'] = create_cavity_mediated_cnot()
    
    # GHZ state preparation
    print("\n2. GHZ State Preparation:")
    circuits['ghz'] = create_ghz_preparation_circuit()
    
    # Error correction
    print("\n3. Error Correction Circuits:")
    circuits['error_correction'] = create_error_correction_circuit()
    
    # Syndrome extraction
    print("\n4. Syndrome Extraction:")
    circuits['syndrome'] = create_syndrome_extraction_circuit()
    
    # Additional circuits (if Qiskit available)
    if QISKIT_AVAILABLE:
        print("\n5. Additional Qiskit Circuits:")
        circuits['steane'] = create_steane_code_circuit()
        circuits['bell'] = create_bell_state_circuit()
    
    print("\n" + "=" * 60)
    print("All quantum circuits created successfully!")
    print(f"Qiskit available: {QISKIT_AVAILABLE}")
    print(f"Circuits created: {list(circuits.keys())}")
    
    return circuits

def display_circuit_summary():
    """
    Display a summary of all available circuits
    """
    print("\nQuantum Circuits Summary:")
    print("=" * 40)
    print("1. Cavity-Mediated CNOT Gate")
    print("   - Non-local quantum gate via optical cavity")
    print("   - Implements remote entanglement operations")
    print()
    print("2. GHZ State Preparation")  
    print("   - Creates n-qubit GHZ states |000...⟩ + |111...⟩")
    print("   - Essential for quantum LDPC codes")
    print()
    print("3. Error Correction Circuit")
    print("   - 3-qubit bit-flip code with syndrome extraction")
    print("   - Demonstrates basic quantum error correction")
    print()
    print("4. Syndrome Extraction Circuit")
    print("   - Fault-tolerant syndrome measurement")
    print("   - DiVincenzo-Aliferis protocol implementation")
    print()
    if QISKIT_AVAILABLE:
        print("5. Steane 7-Qubit Code")
        print("   - Full implementation of CSS code")
        print("   - Both X and Z syndrome extraction")
        print()
        print("6. Bell State Circuit")
        print("   - Basic 2-qubit entanglement")
        print("   - Foundation for larger entangled states")
    print("=" * 40)

if __name__ == "__main__":
    print("Quantum Circuits from LDPC Analysis")
    print("Compiled from cavity_mediated_gates.py, quantum_circuits.py, and syndrome_extraction.py")
    print()
    
    # Display summary
    display_circuit_summary()
    
    # Create all circuits
    circuits = create_all_circuits()
    
    print(f"\nAll circuit files saved to current directory.")
    print("Circuit images and Qiskit objects are available for further analysis.")
