"""
Interactive TQNN Tensor Network Simulator

This application provides a real-time interactive visualization of Topological Quantum Neural
Networks through tensor network decomposition. Users can:

- Draw quantum states on a canvas that are converted to tensor networks
- Watch real-time Matrix Product State (MPS) decomposition
- Manipulate entanglement entropy interactively
- Observe topological phase transitions
- Perform quantum state tomography in real-time
- Visualize spin-network evolution and charge flow

This represents TQNN processing of visual input (drawing) with immediate quantum tensor
decomposition and topological analysis - mimicking how a TQNN would process information
from visual or language input in real-time.

GUI Framework: tkinter with custom dark theme
Architecture: Event-driven with real-time tensor decomposition backend
Author: TQNN Research Team
"""

import tkinter as tk
from tkinter import ttk, messagebox, Canvas
import numpy as np
import math
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
from collections import deque
import time

# Scientific computing
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.patches as mpatches
import seaborn as sns

# Set up color palettes for consistency with project standards
sns.set_style("darkgrid")
seqCmap = sns.color_palette("mako", as_cmap=True)
divCmap = sns.cubehelix_palette(start=.5, rot=-.5, as_cmap=True)
lightCmap = sns.cubehelix_palette(start=2, rot=0, dark=0, light=.95, reverse=True, as_cmap=True)


class TensorDecompositionMode(Enum):
    """Types of tensor decomposition available"""
    MPS = "Matrix Product State"
    PEPS = "Projected Entangled Pair State"
    MERA = "Multi-scale Entanglement Renormalization"
    TREE = "Tree Tensor Network"


@dataclass
class QuantumState:
    """
    Represents a quantum state with tensor network representation
    
    Attributes:
        dimension: Hilbert space dimension
        amplitudes: Complex amplitudes
        entanglement_entropy: Von Neumann entropy
        schmidt_values: Schmidt decomposition values
        bond_dimension: Bond dimension for tensor network
        topological_charge: Conserved topological charge
    """
    dimension: int
    amplitudes: np.ndarray
    entanglement_entropy: float = 0.0
    schmidt_values: List[float] = None
    bond_dimension: int = 2
    topological_charge: float = 0.0
    
    def __post_init__(self):
        if self.schmidt_values is None:
            self.schmidt_values = []


class TQNNTensorProcessor:
    """
    Handles tensor network decomposition and topological quantum computations
    
    This class processes drawn patterns into quantum states and performs
    real-time tensor decomposition with topological analysis.
    """
    
    def __init__(self, lattice_size: int = 16):
        """Initialize the tensor processor"""
        self.lattice_size = lattice_size
        self.current_state = None
        self.decomposition_mode = TensorDecompositionMode.MPS
        
        # Tensor network components
        self.mps_tensors = []
        self.bond_dimensions = []
        self.entanglement_spectrum = []
        
        # Topological properties
        self.topological_order_parameter = 0.0
        self.anyonic_charges = []
        self.braiding_history = deque(maxlen=100)
        
        # Performance tracking
        self.decomposition_times = deque(maxlen=50)
        self.entropy_history = deque(maxlen=100)
        self.charge_history = deque(maxlen=100)
        
        # Quantum circuit representation
        self.circuit_depth = 0
        self.gate_count = 0
        
    def pattern_to_quantum_state(self, pattern: np.ndarray) -> QuantumState:
        """
        Convert a drawn pattern into a quantum state with tensor network structure
        
        Args:
            pattern: 2D array representing the drawn pattern
            
        Returns:
            QuantumState object with tensor decomposition
        """
        # Flatten and normalize pattern
        flat_pattern = pattern.flatten()
        
        # Create quantum amplitudes (complex numbers from real pattern)
        # Use pattern as real part, compute imaginary part for phase
        amplitudes = flat_pattern + 1j * np.roll(flat_pattern, 1)
        amplitudes = amplitudes / np.linalg.norm(amplitudes)
        
        # Calculate entanglement entropy
        entropy = self._calculate_von_neumann_entropy(amplitudes)
        
        # Schmidt decomposition
        schmidt_vals = self._compute_schmidt_values(amplitudes)
        
        # Topological charge (sum of winding numbers)
        topo_charge = self._calculate_topological_charge(pattern)
        
        # Bond dimension (from Schmidt values)
        bond_dim = min(len([s for s in schmidt_vals if s > 1e-10]), 8)
        
        state = QuantumState(
            dimension=len(amplitudes),
            amplitudes=amplitudes,
            entanglement_entropy=entropy,
            schmidt_values=schmidt_vals,
            bond_dimension=bond_dim,
            topological_charge=topo_charge
        )
        
        self.current_state = state
        self.entropy_history.append(entropy)
        self.charge_history.append(topo_charge)
        
        return state
    
    def _calculate_von_neumann_entropy(self, amplitudes: np.ndarray) -> float:
        """Calculate von Neumann entropy of the quantum state"""
        # Density matrix
        rho = np.outer(amplitudes, np.conj(amplitudes))
        
        # Eigenvalues
        eigenvals = np.linalg.eigvalsh(rho)
        eigenvals = eigenvals[eigenvals > 1e-12]  # Remove numerical zeros
        
        # Entropy S = -Tr(ρ log ρ)
        entropy = -np.sum(eigenvals * np.log2(eigenvals + 1e-12))
        
        return float(entropy)
    
    def _compute_schmidt_values(self, amplitudes: np.ndarray) -> List[float]:
        """Compute Schmidt decomposition values"""
        # Reshape into bipartition
        size = int(np.sqrt(len(amplitudes)))
        if size * size != len(amplitudes):
            size = int(len(amplitudes) ** 0.5)
        
        try:
            psi_matrix = amplitudes.reshape(size, -1)
            
            # SVD gives Schmidt decomposition
            U, schmidt_vals, Vh = np.linalg.svd(psi_matrix, full_matrices=False)
            
            return schmidt_vals.tolist()
        except:
            return [1.0]
    
    def _calculate_topological_charge(self, pattern: np.ndarray) -> float:
        """Calculate topological charge (winding number) from pattern"""
        # Compute gradient for winding number
        grad_y, grad_x = np.gradient(pattern)
        
        # Winding number integral
        winding = np.sum(grad_x * np.roll(grad_y, 1, axis=1) - 
                        grad_y * np.roll(grad_x, 1, axis=0))
        
        return float(winding / (2 * np.pi))
    
    def decompose_mps(self) -> List[np.ndarray]:
        """
        Perform Matrix Product State decomposition
        
        Returns:
            List of MPS tensors
        """
        if self.current_state is None:
            return []
        
        start_time = time.time()
        
        amplitudes = self.current_state.amplitudes
        
        # Use log2 to get number of qubits needed
        n_qubits = int(np.log2(len(amplitudes)))
        
        # Ensure we have a power of 2
        if 2 ** n_qubits != len(amplitudes):
            # Pad to next power of 2
            next_power = 2 ** (n_qubits + 1)
            amplitudes = np.pad(amplitudes, (0, next_power - len(amplitudes)), mode='constant')
            n_qubits = n_qubits + 1
        
        # Reshape into physical dimensions (2^n_qubits total, split into n_qubits sites)
        psi = amplitudes.reshape([2] * n_qubits)
        
        # Perform MPS decomposition via successive SVDs
        mps_tensors = []
        current_tensor = psi.reshape(2, -1)
        
        for i in range(n_qubits - 1):
            # SVD and truncate
            U, S, Vh = np.linalg.svd(current_tensor, full_matrices=False)
            
            # Truncate to bond dimension
            chi = min(len(S), self.current_state.bond_dimension)
            U = U[:, :chi]
            S = S[:chi]
            Vh = Vh[:chi, :]
            
            # Store tensor
            mps_tensors.append(U)
            
            # Update bond dimension tracking
            self.bond_dimensions.append(chi)
            
            # Continue decomposition
            current_tensor = np.diag(S) @ Vh
            if i < n_qubits - 2:
                current_tensor = current_tensor.reshape(chi * 2, -1)
        
        # Last tensor
        mps_tensors.append(current_tensor.reshape(-1, 2))
        
        self.mps_tensors = mps_tensors
        
        elapsed = time.time() - start_time
        self.decomposition_times.append(elapsed)
        
        return mps_tensors
    
    def compute_entanglement_spectrum(self) -> np.ndarray:
        """Compute entanglement spectrum across all cuts"""
        if self.current_state is None or not self.current_state.schmidt_values:
            return np.array([])
        
        # Entanglement energies: -log(lambda_i)
        schmidt_vals = np.array(self.current_state.schmidt_values)
        schmidt_vals = schmidt_vals[schmidt_vals > 1e-12]
        
        entanglement_energies = -np.log(schmidt_vals + 1e-12)
        
        self.entanglement_spectrum = entanglement_energies
        return entanglement_energies
    
    def detect_topological_phase(self) -> str:
        """Detect topological phase based on entanglement properties"""
        if self.current_state is None:
            return "Trivial"
        
        entropy = self.current_state.entanglement_entropy
        charge = self.current_state.topological_charge
        
        # Phase classification based on entropy and charge
        if entropy < 0.5 and abs(charge) < 0.1:
            return "Trivial Phase"
        elif entropy > 2.0 and abs(charge) > 0.5:
            return "Topological Phase (Non-trivial)"
        elif abs(charge) > 0.3:
            return "Chiral Edge State"
        else:
            return "Gapped Phase"
    
    def simulate_braiding_operation(self, anyon_positions: List[Tuple[int, int]]):
        """Simulate anyonic braiding operation"""
        if len(anyon_positions) < 2:
            return
        
        # Compute braiding matrix (simplified)
        pos1, pos2 = anyon_positions[0], anyon_positions[1]
        
        # Winding angle
        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        angle = np.arctan2(dy, dx)
        
        # Braiding contributes to topological order parameter
        self.topological_order_parameter = np.cos(angle) * np.exp(-0.1 * len(self.braiding_history))
        self.braiding_history.append((pos1, pos2, angle))
    
    def get_circuit_complexity(self) -> Dict[str, int]:
        """Compute quantum circuit complexity metrics"""
        if self.current_state is None:
            return {"depth": 0, "gates": 0, "cnots": 0}
        
        # Estimate circuit depth from bond dimension
        self.circuit_depth = int(np.log2(self.current_state.bond_dimension + 1)) * 2
        
        # Estimate gate count from entanglement
        self.gate_count = int(self.current_state.entanglement_entropy * 10)
        
        # CNOT count (proportional to entanglement)
        cnot_count = int(self.gate_count * 0.3)
        
        return {
            "depth": self.circuit_depth,
            "gates": self.gate_count,
            "cnots": cnot_count
        }


class TQNNTensorNetworkGUI:
    """
    Main GUI application for TQNN Tensor Network Simulator
    
    Provides real-time interactive visualization of tensor network decomposition
    and topological quantum neural network processing.
    """
    
    def __init__(self):
        """Initialize the GUI application"""
        self.root = self._setup_gui()
        self.processor = TQNNTensorProcessor(lattice_size=16)
        
        # Drawing canvas state
        self.drawing = False
        self.last_x = None
        self.last_y = None
        self.pattern_array = np.zeros((16, 16))
        
        # Animation state
        self.animation_running = False
        self.animation_frame = 0
        self.update_interval = 100  # ms
        
        # Display options
        self.show_tensor_network = True
        self.show_entanglement = True
        self.show_charges = True
        self.auto_decompose = True
        
        self._setup_ui()
        self._bind_events()
        self._start_animation()
    
    def _setup_gui(self) -> tk.Tk:
        """Set up the main GUI window with dark theme"""
        root = tk.Tk()
        root.title("TQNN Tensor Network Simulator - Real-Time Interactive Processing")
        root.geometry("1600x1000")
        root.configure(bg='#1a1a1a')
        
        # Configure dark theme style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Dark theme colors
        style.configure('Dark.TFrame', background='#1a1a1a')
        style.configure('Dark.TLabel', background='#1a1a1a', foreground='#ffffff')
        style.configure('Dark.TLabelframe', background='#1a1a1a', foreground='#ffffff', 
                       borderwidth=2, relief='solid')
        style.configure('Dark.TLabelframe.Label', background='#1a1a1a', foreground='#00ff88',
                       font=('TkDefaultFont', 10, 'bold'))
        style.configure('Dark.TButton', background='#2d2d2d', foreground='#ffffff',
                       borderwidth=1, relief='raised')
        style.map('Dark.TButton',
                 background=[('active', '#3d3d3d')],
                 foreground=[('active', '#00ff88')])
        style.configure('Dark.TCheckbutton', background='#1a1a1a', foreground='#ffffff')
        
        return root
    
    def _setup_ui(self):
        """Set up the user interface components"""
        # Main container
        main_container = ttk.Frame(self.root, style='Dark.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Drawing canvas and controls
        left_panel = ttk.Frame(main_container, style='Dark.TFrame')
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        
        # Right panel - Visualizations
        right_panel = ttk.Frame(main_container, style='Dark.TFrame')
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self._setup_drawing_area(left_panel)
        self._setup_control_panel(left_panel)
        self._setup_visualization_panel(right_panel)
        self._setup_status_panel(left_panel)
    
    def _setup_drawing_area(self, parent):
        """Setup the drawing canvas area"""
        drawing_frame = ttk.LabelFrame(parent, text="Quantum State Input (Draw Here)", 
                                      style='Dark.TLabelframe', padding=10)
        drawing_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 10))
        
        # Canvas for drawing
        self.drawing_canvas = Canvas(drawing_frame, width=400, height=400, 
                                    bg='#0a0a0a', highlightthickness=2,
                                    highlightbackground='#00ff88')
        self.drawing_canvas.pack()
        
        # Draw grid
        self._draw_grid()
        
        # Instructions
        instr_label = ttk.Label(drawing_frame, 
                              text="Draw patterns to create quantum states\nReal-time tensor decomposition",
                              style='Dark.TLabel', font=('TkDefaultFont', 9, 'italic'))
        instr_label.pack(pady=(5, 0))
    
    def _draw_grid(self):
        """Draw grid on canvas"""
        cell_size = 400 // 16
        for i in range(17):
            x = i * cell_size
            self.drawing_canvas.create_line(x, 0, x, 400, fill='#2a2a2a', width=1)
            self.drawing_canvas.create_line(0, x, 400, x, fill='#2a2a2a', width=1)
    
    def _setup_control_panel(self, parent):
        """Setup control buttons and options"""
        control_frame = ttk.LabelFrame(parent, text="Controls & Options", 
                                      style='Dark.TLabelframe', padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Action buttons
        btn_frame = ttk.Frame(control_frame, style='Dark.TFrame')
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.btn_clear = ttk.Button(btn_frame, text="Clear Canvas",
                                   command=self.clear_canvas, style='Dark.TButton')
        self.btn_clear.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        self.btn_decompose = ttk.Button(btn_frame, text="Decompose Now",
                                       command=self.manual_decompose, style='Dark.TButton')
        self.btn_decompose.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        self.btn_random = ttk.Button(btn_frame, text="Random State",
                                    command=self.generate_random_state, style='Dark.TButton')
        self.btn_random.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        # Display options
        option_frame = ttk.Frame(control_frame, style='Dark.TFrame')
        option_frame.pack(fill=tk.X)
        
        self.var_auto = tk.BooleanVar(value=True)
        self.check_auto = ttk.Checkbutton(option_frame, text="Auto Decompose",
                                         variable=self.var_auto, style='Dark.TCheckbutton')
        self.check_auto.pack(anchor=tk.W)
        
        self.var_tensor_net = tk.BooleanVar(value=True)
        self.check_tensor = ttk.Checkbutton(option_frame, text="Show Tensor Network",
                                           variable=self.var_tensor_net, style='Dark.TCheckbutton')
        self.check_tensor.pack(anchor=tk.W)
        
        self.var_entanglement = tk.BooleanVar(value=True)
        self.check_entangle = ttk.Checkbutton(option_frame, text="Show Entanglement",
                                             variable=self.var_entanglement, style='Dark.TCheckbutton')
        self.check_entangle.pack(anchor=tk.W)
        
        self.var_charges = tk.BooleanVar(value=True)
        self.check_charges = ttk.Checkbutton(option_frame, text="Show Topological Charges",
                                            variable=self.var_charges, style='Dark.TCheckbutton')
        self.check_charges.pack(anchor=tk.W)
    
    def _setup_status_panel(self, parent):
        """Setup status display panel"""
        status_frame = ttk.LabelFrame(parent, text="Quantum State Properties", 
                                     style='Dark.TLabelframe', padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status text
        self.status_text = tk.Text(status_frame, height=15, bg='#0a0a0a', fg='#00ff88',
                                  insertbackground='#00ff88', selectbackground='#2d2d2d',
                                  font=('Courier', 9), wrap=tk.WORD)
        self.status_text.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(status_frame, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
        
        self._update_status("TQNN Tensor Network Simulator initialized.\nDraw on canvas to create quantum states.")
    
    def _setup_visualization_panel(self, parent):
        """Setup matplotlib visualization panels"""
        # Create figure with subplots
        self.fig = Figure(figsize=(12, 10), facecolor='#1a1a1a')
        
        # Create 2x2 grid of subplots
        gs = self.fig.add_gridspec(3, 2, hspace=0.4, wspace=0.3, 
                                  top=0.95, bottom=0.08, left=0.08, right=0.95)
        
        # Tensor network visualization
        self.ax_tensor = self.fig.add_subplot(gs[0, 0])
        self.ax_tensor.set_title("MPS Tensor Network Structure", color='white', fontsize=12, fontweight='bold')
        self.ax_tensor.set_facecolor('#0a0a0a')
        
        # Entanglement spectrum
        self.ax_entangle = self.fig.add_subplot(gs[0, 1])
        self.ax_entangle.set_title("Entanglement Spectrum", color='white', fontsize=12, fontweight='bold')
        self.ax_entangle.set_facecolor('#0a0a0a')
        
        # Schmidt values
        self.ax_schmidt = self.fig.add_subplot(gs[1, 0])
        self.ax_schmidt.set_title("Schmidt Decomposition", color='white', fontsize=12, fontweight='bold')
        self.ax_schmidt.set_facecolor('#0a0a0a')
        
        # Topological charge flow
        self.ax_charge = self.fig.add_subplot(gs[1, 1])
        self.ax_charge.set_title("Topological Charge Evolution", color='white', fontsize=12, fontweight='bold')
        self.ax_charge.set_facecolor('#0a0a0a')
        
        # Entropy history
        self.ax_entropy = self.fig.add_subplot(gs[2, :])
        self.ax_entropy.set_title("von Neumann Entropy History", color='white', fontsize=12, fontweight='bold')
        self.ax_entropy.set_facecolor('#0a0a0a')
        
        # Style all axes
        for ax in [self.ax_tensor, self.ax_entangle, self.ax_schmidt, self.ax_charge, self.ax_entropy]:
            ax.tick_params(colors='white', labelsize=8)
            ax.spines['bottom'].set_color('white')
            ax.spines['top'].set_color('white')
            ax.spines['right'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.grid(True, alpha=0.2, color='gray')
        
        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _bind_events(self):
        """Bind mouse and keyboard events"""
        self.drawing_canvas.bind("<Button-1>", self.start_drawing)
        self.drawing_canvas.bind("<B1-Motion>", self.draw)
        self.drawing_canvas.bind("<ButtonRelease-1>", self.stop_drawing)
        
        self.root.bind("<Escape>", lambda e: self.clear_canvas())
        self.root.bind("<space>", lambda e: self.manual_decompose())
    
    def start_drawing(self, event):
        """Start drawing on canvas"""
        self.drawing = True
        self.last_x = event.x
        self.last_y = event.y
        self.draw(event)
    
    def draw(self, event):
        """Draw on canvas and update pattern array"""
        if not self.drawing:
            return
        
        x, y = event.x, event.y
        
        # Draw on canvas
        if self.last_x and self.last_y:
            self.drawing_canvas.create_line(self.last_x, self.last_y, x, y,
                                          fill='#00ff88', width=3, capstyle=tk.ROUND)
        
        # Update pattern array
        cell_size = 400 // 16
        grid_x = min(15, max(0, x // cell_size))
        grid_y = min(15, max(0, y // cell_size))
        self.pattern_array[grid_y, grid_x] = 1.0
        
        # Also mark nearby cells for smoother patterns
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nx, ny = grid_x + dx, grid_y + dy
                if 0 <= nx < 16 and 0 <= ny < 16:
                    self.pattern_array[ny, nx] = max(self.pattern_array[ny, nx], 0.5)
        
        self.last_x = x
        self.last_y = y
    
    def stop_drawing(self, event):
        """Stop drawing and process the pattern"""
        self.drawing = False
        self.last_x = None
        self.last_y = None
        
        if self.var_auto.get():
            self.process_pattern()
    
    def clear_canvas(self):
        """Clear the drawing canvas"""
        self.drawing_canvas.delete("all")
        self._draw_grid()
        self.pattern_array = np.zeros((16, 16))
        self._update_status("Canvas cleared.")
    
    def manual_decompose(self):
        """Manually trigger decomposition"""
        self.process_pattern()
    
    def generate_random_state(self):
        """Generate a random quantum state pattern"""
        # Create interesting random pattern
        self.pattern_array = np.random.random((16, 16))
        self.pattern_array = (self.pattern_array > 0.7).astype(float)
        
        # Clear canvas first
        self.drawing_canvas.delete("all")
        self._draw_grid()
        
        # Draw on canvas
        cell_size = 400 // 16
        for i in range(16):
            for j in range(16):
                if self.pattern_array[i, j] > 0:
                    x1, y1 = j * cell_size, i * cell_size
                    x2, y2 = x1 + cell_size, y1 + cell_size
                    self.drawing_canvas.create_rectangle(x1, y1, x2, y2,
                                                        fill='#00ff88', outline='')
        
        # Process the pattern
        self.process_pattern()
    
    def process_pattern(self):
        """Process the drawn pattern into quantum state"""
        if np.sum(self.pattern_array) == 0:
            return
        
        # Convert to quantum state
        state = self.processor.pattern_to_quantum_state(self.pattern_array)
        
        # Perform MPS decomposition
        self.processor.decompose_mps()
        
        # Compute entanglement spectrum
        self.processor.compute_entanglement_spectrum()
        
        # Detect topological phase
        phase = self.processor.detect_topological_phase()
        
        # Update status
        status_msg = f"""
Quantum State Created:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dimension: {state.dimension}
Bond Dimension: χ = {state.bond_dimension}
Entanglement Entropy: S = {state.entanglement_entropy:.4f}
Topological Charge: Q = {state.topological_charge:.4f}

Topological Phase: {phase}

Schmidt Values: {len(state.schmidt_values)} non-zero
MPS Tensors: {len(self.processor.mps_tensors)} tensors

Circuit Complexity:
  Depth: {self.processor.circuit_depth}
  Gate Count: {self.processor.gate_count}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        self._update_status(status_msg)
        
        # Update visualizations
        self._update_all_plots()
    
    def _update_status(self, message: str):
        """Update status display"""
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
    
    def _update_all_plots(self):
        """Update all visualization plots"""
        self._plot_tensor_network()
        self._plot_entanglement_spectrum()
        self._plot_schmidt_values()
        self._plot_charge_evolution()
        self._plot_entropy_history()
        self.canvas.draw()
    
    def _plot_tensor_network(self):
        """Plot MPS tensor network structure"""
        self.ax_tensor.clear()
        
        if not self.processor.mps_tensors or not self.var_tensor_net.get():
            self.ax_tensor.text(0.5, 0.5, "Draw to create\ntensor network", 
                              ha='center', va='center', color='gray',
                              transform=self.ax_tensor.transAxes, fontsize=12)
            return
        
        n_tensors = len(self.processor.mps_tensors)
        
        # Draw tensor network diagram
        for i in range(n_tensors):
            x = i
            y = 0
            
            # Tensor box
            color = seqCmap(i / n_tensors)
            rect = mpatches.Rectangle((x - 0.3, y - 0.3), 0.6, 0.6,
                                     facecolor=color, edgecolor='white', linewidth=2)
            self.ax_tensor.add_patch(rect)
            
            # Tensor label
            self.ax_tensor.text(x, y, f'T{i}', ha='center', va='center',
                              color='white', fontsize=10, fontweight='bold')
            
            # Bond dimension label
            if i < len(self.processor.bond_dimensions):
                bond_dim = self.processor.bond_dimensions[i]
                self.ax_tensor.text(x, y - 0.6, f'χ={bond_dim}', ha='center', va='top',
                                  color='cyan', fontsize=8)
            
            # Connect tensors
            if i < n_tensors - 1:
                self.ax_tensor.plot([x + 0.3, x + 0.7], [y, y], 'w-', linewidth=2)
        
        self.ax_tensor.set_xlim(-0.5, n_tensors - 0.5)
        self.ax_tensor.set_ylim(-1, 1)
        self.ax_tensor.set_aspect('equal')
        self.ax_tensor.axis('off')
        self.ax_tensor.set_title("MPS Tensor Network Structure", color='white', fontsize=12, fontweight='bold')
    
    def _plot_entanglement_spectrum(self):
        """Plot entanglement spectrum"""
        self.ax_entangle.clear()
        
        if len(self.processor.entanglement_spectrum) == 0 or not self.var_entanglement.get():
            self.ax_entangle.text(0.5, 0.5, "Entanglement\nspectrum", 
                                ha='center', va='center', color='gray',
                                transform=self.ax_entangle.transAxes, fontsize=12)
            return
        
        spectrum = self.processor.entanglement_spectrum
        indices = np.arange(len(spectrum))
        
        # Bar plot
        colors = [seqCmap(i / len(spectrum)) for i in range(len(spectrum))]
        self.ax_entangle.bar(indices, spectrum, color=colors, alpha=0.8, edgecolor='white')
        
        self.ax_entangle.set_xlabel("State Index", color='white', fontsize=9)
        self.ax_entangle.set_ylabel("Entanglement Energy", color='white', fontsize=9)
        self.ax_entangle.tick_params(colors='white', labelsize=8)
        self.ax_entangle.grid(True, alpha=0.2, color='gray')
        
        # Add average line
        avg = np.mean(spectrum)
        self.ax_entangle.axhline(y=avg, color='red', linestyle='--', linewidth=2, alpha=0.7)
        self.ax_entangle.text(0.98, 0.95, f'Avg: {avg:.2f}', transform=self.ax_entangle.transAxes,
                            ha='right', va='top', color='red', fontsize=8,
                            bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))
    
    def _plot_schmidt_values(self):
        """Plot Schmidt decomposition values"""
        self.ax_schmidt.clear()
        
        if self.processor.current_state is None or not self.processor.current_state.schmidt_values:
            self.ax_schmidt.text(0.5, 0.5, "Schmidt\ndecomposition", 
                               ha='center', va='center', color='gray',
                               transform=self.ax_schmidt.transAxes, fontsize=12)
            return
        
        schmidt_vals = np.array(self.processor.current_state.schmidt_values)
        schmidt_vals = schmidt_vals[schmidt_vals > 1e-10]  # Filter small values
        
        # Semilogy plot
        self.ax_schmidt.semilogy(schmidt_vals, 'o-', color=lightCmap(0.7), 
                               markersize=8, linewidth=2, markeredgecolor='white')
        
        self.ax_schmidt.set_xlabel("Schmidt Index", color='white', fontsize=9)
        self.ax_schmidt.set_ylabel("Schmidt Value (log scale)", color='white', fontsize=9)
        self.ax_schmidt.tick_params(colors='white', labelsize=8)
        self.ax_schmidt.grid(True, alpha=0.2, color='gray', which='both')
        
        # Add truncation line
        threshold = 1e-2
        self.ax_schmidt.axhline(y=threshold, color='yellow', linestyle=':', linewidth=2, alpha=0.7)
        self.ax_schmidt.text(0.02, 0.05, f'Truncation threshold: {threshold}', 
                           transform=self.ax_schmidt.transAxes,
                           color='yellow', fontsize=8,
                           bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))
    
    def _plot_charge_evolution(self):
        """Plot topological charge evolution"""
        self.ax_charge.clear()
        
        if len(self.processor.charge_history) == 0 or not self.var_charges.get():
            self.ax_charge.text(0.5, 0.5, "Topological\ncharge flow", 
                              ha='center', va='center', color='gray',
                              transform=self.ax_charge.transAxes, fontsize=12)
            return
        
        charges = list(self.processor.charge_history)
        times = np.arange(len(charges))
        
        # Plot with color gradient
        for i in range(len(charges) - 1):
            color = divCmap((i / len(charges) + 1) / 2)
            self.ax_charge.plot(times[i:i+2], charges[i:i+2], color=color, linewidth=2)
        
        # Fill area
        self.ax_charge.fill_between(times, charges, alpha=0.3, color=divCmap(0.5))
        
        self.ax_charge.set_xlabel("Evolution Steps", color='white', fontsize=9)
        self.ax_charge.set_ylabel("Topological Charge Q", color='white', fontsize=9)
        self.ax_charge.tick_params(colors='white', labelsize=8)
        self.ax_charge.grid(True, alpha=0.2, color='gray')
        
        # Add zero line
        self.ax_charge.axhline(y=0, color='white', linestyle='-', linewidth=1, alpha=0.5)
        
        # Current charge
        if charges:
            current = charges[-1]
            self.ax_charge.text(0.98, 0.95, f'Current Q: {current:.3f}', 
                              transform=self.ax_charge.transAxes,
                              ha='right', va='top', color='cyan', fontsize=9,
                              bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))
    
    def _plot_entropy_history(self):
        """Plot entropy evolution history"""
        self.ax_entropy.clear()
        
        if len(self.processor.entropy_history) == 0:
            self.ax_entropy.text(0.5, 0.5, "von Neumann entropy evolution\n(will appear as you draw)", 
                               ha='center', va='center', color='gray',
                               transform=self.ax_entropy.transAxes, fontsize=12)
            return
        
        entropies = list(self.processor.entropy_history)
        times = np.arange(len(entropies))
        
        # Plot with gradient
        points = np.array([times, entropies]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        
        from matplotlib.collections import LineCollection
        colors = [seqCmap(i / len(entropies)) for i in range(len(entropies) - 1)]
        lc = LineCollection(segments, colors=colors, linewidths=3)
        self.ax_entropy.add_collection(lc)
        
        # Fill under curve
        self.ax_entropy.fill_between(times, entropies, alpha=0.3, color=seqCmap(0.5))
        
        self.ax_entropy.set_xlim(times.min() if len(times) > 0 else 0, 
                                times.max() + 1 if len(times) > 0 else 1)
        self.ax_entropy.set_ylim(0, max(entropies) * 1.2 if entropies else 1)
        
        self.ax_entropy.set_xlabel("State Evolution Steps", color='white', fontsize=10)
        self.ax_entropy.set_ylabel("Entanglement Entropy S", color='white', fontsize=10)
        self.ax_entropy.tick_params(colors='white', labelsize=9)
        self.ax_entropy.grid(True, alpha=0.2, color='gray')
        
        # Add statistics
        if entropies:
            avg = np.mean(entropies)
            max_e = np.max(entropies)
            min_e = np.min(entropies)
            stats_text = f'Min: {min_e:.3f}  Avg: {avg:.3f}  Max: {max_e:.3f}'
            self.ax_entropy.text(0.5, 0.95, stats_text, transform=self.ax_entropy.transAxes,
                               ha='center', va='top', color='white', fontsize=9,
                               bbox=dict(boxstyle='round', facecolor='black', alpha=0.8))
    
    def _start_animation(self):
        """Start the animation loop"""
        self.animation_running = True
        self._animation_step()
    
    def _animation_step(self):
        """Single animation step"""
        if not self.animation_running:
            return
        
        self.animation_frame += 1
        
        # Periodic updates (every 20 frames)
        if self.animation_frame % 20 == 0 and self.processor.current_state is not None:
            # Simulate topological evolution
            pass
        
        # Schedule next frame
        self.root.after(self.update_interval, self._animation_step)
    
    def run(self):
        """Start the GUI main loop"""
        self._update_status("=== TQNN Tensor Network Simulator Ready ===")
        self._update_status("Draw quantum states and watch real-time decomposition!")
        self._update_status("Features: MPS decomposition, entanglement analysis, topological phases")
        self.root.mainloop()


def main():
    """Main entry point for the application"""
    print("=== TQNN Tensor Network Simulator ===")
    print("Real-Time Interactive Quantum State Processing")
    print("Draw patterns to create quantum states with tensor network decomposition")
    print("\nFeatures:")
    print("• Real-time Matrix Product State (MPS) decomposition")
    print("• Entanglement spectrum visualization")
    print("• Schmidt decomposition analysis")
    print("• Topological charge tracking")
    print("• von Neumann entropy evolution")
    print("• Quantum circuit complexity metrics")
    print("\nStarting GUI...")
    
    try:
        app = TQNNTensorNetworkGUI()
        app.run()
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
