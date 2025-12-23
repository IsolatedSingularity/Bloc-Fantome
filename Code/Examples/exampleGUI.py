"""
Interactive 3D Quantum LDPC Circuit Builder

This module implements a real-time interactive quantum circuit builder using tkinter
with a dark theme GUI framework. The application provides a 2.5D isometric perspective
where users can drag and drop 3D quantum circuit components from a toolbox onto a
grid-based building area to construct quantum LDPC circuits and perform real-time quantum computations.

GUI Framework: tkinter with tkinter.ttk for native dark theme support
Dark Theme: Custom dark color scheme with modern UI elements
Architecture: Event-driven GUI with real-time quantum computation backend

Author: Jeffrey Morais
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
import math
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import os

# Quantum computing libraries
try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
    from qiskit.quantum_info import Statevector, Operator
    from qiskit_aer import AerSimulator
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    print("Warning: Qiskit not available. Some quantum computations will be simulated.")

# Scientific computing
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import seaborn as sns

# Set up color palettes for consistency with project standards
sns.set_style("darkgrid")
seqCmap = sns.color_palette("mako", as_cmap=True)
divCmap = sns.cubehelix_palette(start=.5, rot=-.5, as_cmap=True)
lightCmap = sns.cubehelix_palette(start=2, rot=0, dark=0, light=.95, reverse=True, as_cmap=True)


class ComponentType(Enum):
    """Enumeration of available quantum circuit components."""
    
    # Single qubit gates
    X_GATE = "X"
    Z_GATE = "Z"
    Y_GATE = "Y"
    H_GATE = "H"
    S_GATE = "S"
    T_GATE = "T"
    
    # Two qubit gates
    CNOT_GATE = "CNOT"
    CZ_GATE = "CZ"
    SWAP_GATE = "SWAP"
    
    # LDPC specific components
    PARITY_CHECK = "Parity Check"
    DATA_QUBIT = "Data Qubit"
    ANCILLA_QUBIT = "Ancilla"
    SYNDROME_EXTRACT = "Syndrome"
    
    # Measurement and reset
    MEASURE = "Measure"
    RESET = "Reset"


@dataclass
class Component3D:
    """
    Represents a 3D quantum circuit component with position and properties.
    
    Attributes:
        component_type: Type of quantum component
        position: (x, y, z) grid coordinates
        rotation: Rotation angle in degrees
        size: (width, height, depth) in grid units
        color: RGB color tuple for rendering
        connections: List of connected component IDs
        properties: Component-specific properties dictionary
    """
    
    component_type: ComponentType
    position: Tuple[int, int, int]
    rotation: float = 0.0
    size: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    color: Tuple[float, float, float] = (0.5, 0.5, 0.8)
    connections: List[int] = None
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.connections is None:
            self.connections = []
        if self.properties is None:
            self.properties = {}


class IsometricRenderer:
    """
    Handles 2.5D isometric rendering of 3D components on a tkinter canvas.
    
    This class provides methods to convert 3D coordinates to 2D isometric
    projections and render quantum circuit components as 3D blocks.
    """
    
    def __init__(self, canvas: tk.Canvas, scale: float = 30.0):
        """
        Initialize the isometric renderer.
        
        Args:
            canvas: tkinter Canvas widget for rendering
            scale: Scaling factor for isometric projection
        """
        self.canvas = canvas
        self.scale = scale
        self.offset_x = 400  # Moved grid more to the right
        self.offset_y = 200  # Moved grid down
        
        # Isometric projection angles (30 degrees)
        self.cos_30 = math.cos(math.radians(30))
        self.sin_30 = math.sin(math.radians(30))
    
    def project_3d_to_2d(self, x: float, y: float, z: float) -> Tuple[float, float]:
        """
        Convert 3D coordinates to 2D isometric projection.
        
        Args:
            x, y, z: 3D coordinates
            
        Returns:
            Tuple of 2D screen coordinates
        """
        iso_x = (x - y) * self.cos_30 * self.scale + self.offset_x
        iso_y = (x + y) * self.sin_30 * self.scale - z * self.scale + self.offset_y
        return iso_x, iso_y
    
    def draw_cube(self, x: float, y: float, z: float, 
                  width: float, height: float, depth: float,
                  color: Tuple[float, float, float], 
                  outline: str = "#333333") -> List[int]:
        """
        Draw a 3D cube using isometric projection.
        
        Args:
            x, y, z: Bottom-left-front corner position
            width, height, depth: Cube dimensions
            color: RGB color tuple (0-1 range)
            outline: Outline color hex string
            
        Returns:
            List of canvas item IDs for the rendered cube
        """
        # Convert color to hex
        hex_color = self._rgb_to_hex(color)
        
        # Define cube vertices
        vertices = [
            (x, y, z),              # 0: bottom-left-front
            (x + width, y, z),      # 1: bottom-right-front
            (x + width, y + depth, z),  # 2: bottom-right-back
            (x, y + depth, z),      # 3: bottom-left-back
            (x, y, z + height),     # 4: top-left-front
            (x + width, y, z + height),  # 5: top-right-front
            (x + width, y + depth, z + height),  # 6: top-right-back
            (x, y + depth, z + height)   # 7: top-left-back
        ]
        
        # Project vertices to 2D
        projected = [self.project_3d_to_2d(*v) for v in vertices]
        
        items = []
        
        # Draw visible faces (assuming view from front-right-top)
        
        # Top face (lighter)
        top_color = self._brighten_color(color, 1.2)
        top_hex = self._rgb_to_hex(top_color)
        items.append(self.canvas.create_polygon(
            projected[4][0], projected[4][1],
            projected[5][0], projected[5][1],
            projected[6][0], projected[6][1],
            projected[7][0], projected[7][1],
            fill=top_hex, outline=outline, width=1
        ))
        
        # Right face (medium)
        right_color = self._brighten_color(color, 1.0)
        right_hex = self._rgb_to_hex(right_color)
        items.append(self.canvas.create_polygon(
            projected[1][0], projected[1][1],
            projected[2][0], projected[2][1],
            projected[6][0], projected[6][1],
            projected[5][0], projected[5][1],
            fill=right_hex, outline=outline, width=1
        ))
        
        # Front face (darker)
        front_color = self._brighten_color(color, 0.8)
        front_hex = self._rgb_to_hex(front_color)
        items.append(self.canvas.create_polygon(
            projected[0][0], projected[0][1],
            projected[1][0], projected[1][1],
            projected[5][0], projected[5][1],
            projected[4][0], projected[4][1],
            fill=front_hex, outline=outline, width=1
        ))
        
        return items
    
    def _rgb_to_hex(self, color: Tuple[float, float, float]) -> str:
        """Convert RGB tuple (0-1 range) to hex color string."""
        r, g, b = [int(c * 255) for c in color]
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _brighten_color(self, color: Tuple[float, float, float], factor: float) -> Tuple[float, float, float]:
        """Brighten or darken a color by a given factor."""
        return tuple(min(1.0, c * factor) for c in color)


class QuantumLDPCProcessor:
    """
    Handles quantum LDPC computations for real-time circuit analysis.
    
    This class processes the built quantum circuits and performs:
    - Syndrome calculation
    - Error correction decoding
    - Quantum state evolution
    """
    
    def __init__(self):
        """Initialize the quantum processor."""
        self.circuit = None
        self.current_state = None
        self.syndrome_history = []
        self.error_corrections = []
    
    def build_circuit_from_components(self, components: List[Component3D]) -> Optional[QuantumCircuit]:
        """
        Build a Qiskit quantum circuit from placed components.
        
        Args:
            components: List of placed 3D components
            
        Returns:
            Constructed QuantumCircuit or None if build fails
        """
        if not QISKIT_AVAILABLE:
            return self._simulate_circuit_build(components)
        
        try:
            # Determine circuit size from component positions
            qubit_positions = [comp.position[1] for comp in components 
                             if comp.component_type in [ComponentType.DATA_QUBIT, ComponentType.ANCILLA_QUBIT]]
            
            if not qubit_positions:
                # No qubits found, use maximum y-position from all components
                max_qubit = max([comp.position[1] for comp in components if comp.position[1] >= 0], default=0)
            else:
                max_qubit = max(qubit_positions)
            
            num_qubits = max_qubit + 1
            
            # Create circuit
            qreg = QuantumRegister(num_qubits, 'q')
            creg = ClassicalRegister(num_qubits, 'c')
            circuit = QuantumCircuit(qreg, creg)
            
            # Sort components by x-position for temporal ordering
            sorted_components = sorted(components, key=lambda c: c.position[0])
            
            for comp in sorted_components:
                qubit_idx = comp.position[1]
                if qubit_idx < 0 or qubit_idx >= num_qubits:
                    continue
                
                self._add_component_to_circuit(circuit, comp, qreg, creg)
            
            self.circuit = circuit
            return circuit
            
        except Exception as e:
            print(f"Error building circuit: {e}")
            return None
    
    def _add_component_to_circuit(self, circuit: QuantumCircuit, 
                                 component: Component3D,
                                 qreg: QuantumRegister, 
                                 creg: ClassicalRegister):
        """Add a single component to the quantum circuit."""
        comp_type = component.component_type
        qubit = component.position[1]
        
        if comp_type == ComponentType.X_GATE:
            circuit.x(qreg[qubit])
        elif comp_type == ComponentType.Z_GATE:
            circuit.z(qreg[qubit])
        elif comp_type == ComponentType.Y_GATE:
            circuit.y(qreg[qubit])
        elif comp_type == ComponentType.H_GATE:
            circuit.h(qreg[qubit])
        elif comp_type == ComponentType.S_GATE:
            circuit.s(qreg[qubit])
        elif comp_type == ComponentType.T_GATE:
            circuit.t(qreg[qubit])
        elif comp_type == ComponentType.CNOT_GATE:
            # For CNOT, use adjacent qubit as control if no specific connection
            if component.connections and len(component.connections) > 0:
                control_qubit = component.connections[0]
                if 0 <= control_qubit < len(qreg) and control_qubit != qubit:
                    circuit.cx(qreg[control_qubit], qreg[qubit])
            else:
                # Default: use qubit-1 as control if it exists and is different
                control_qubit = max(0, qubit - 1)
                if control_qubit != qubit and control_qubit < len(qreg):
                    circuit.cx(qreg[control_qubit], qreg[qubit])
        elif comp_type == ComponentType.CZ_GATE:
            # Similar logic for CZ gate
            if component.connections and len(component.connections) > 0:
                control_qubit = component.connections[0]
                if 0 <= control_qubit < len(qreg) and control_qubit != qubit:
                    circuit.cz(qreg[control_qubit], qreg[qubit])
            else:
                control_qubit = max(0, qubit - 1)
                if control_qubit != qubit and control_qubit < len(qreg):
                    circuit.cz(qreg[control_qubit], qreg[qubit])
        elif comp_type == ComponentType.MEASURE:
            circuit.measure(qreg[qubit], creg[qubit])
        elif comp_type == ComponentType.RESET:
            circuit.reset(qreg[qubit])
    
    def _simulate_circuit_build(self, components: List[Component3D]) -> Dict[str, Any]:
        """Simulate circuit building when Qiskit is not available."""
        return {
            'num_qubits': len(set(comp.position[1] for comp in components)),
            'num_gates': len(components),
            'depth': max([comp.position[0] for comp in components], default=0) + 1
        }
    
    def calculate_syndrome(self, components: List[Component3D]) -> np.ndarray:
        """
        Calculate syndrome for current circuit configuration.
        
        Args:
            components: List of placed components
            
        Returns:
            Syndrome vector as numpy array
        """
        # Extract components - use ancilla qubits as syndrome extractors if no parity checks
        parity_checks = [c for c in components if c.component_type == ComponentType.PARITY_CHECK]
        ancilla_qubits = [c for c in components if c.component_type == ComponentType.ANCILLA_QUBIT]
        syndrome_extractors = [c for c in components if c.component_type == ComponentType.SYNDROME_EXTRACT]
        data_qubits = [c for c in components if c.component_type == ComponentType.DATA_QUBIT]
        
        # Use ancilla qubits as syndrome extractors if no dedicated parity checks
        if not parity_checks and ancilla_qubits:
            parity_checks = ancilla_qubits
        elif syndrome_extractors:
            parity_checks.extend(syndrome_extractors)
        
        if not parity_checks or not data_qubits:
            return np.array([])
        
        # Build parity check matrix
        num_checks = len(parity_checks)
        num_data = len(data_qubits)
        
        parity_matrix = np.zeros((num_checks, num_data), dtype=int)
        
        # Simulate connections between parity checks and data qubits
        for i, check in enumerate(parity_checks):
            for j, data in enumerate(data_qubits):
                # Simple distance-based connection rule
                distance = abs(check.position[0] - data.position[0]) + abs(check.position[1] - data.position[1])
                if distance <= 2:  # Connect if within Manhattan distance 2
                    parity_matrix[i, j] = 1
        
        # Check if we have any connections
        if np.sum(parity_matrix) == 0:
            # If no automatic connections, create a simple pattern
            for i in range(min(num_checks, num_data)):
                parity_matrix[i, i] = 1
                if i + 1 < num_data:
                    parity_matrix[i, i + 1] = 1
        
        # Simulate error vector (random for demonstration)
        error_vector = np.random.randint(0, 2, size=num_data)
        
        # Calculate syndrome
        syndrome = np.dot(parity_matrix, error_vector) % 2
        
        self.syndrome_history.append(syndrome.copy())
        return syndrome
    
    def perform_error_correction(self, syndrome: np.ndarray, components: List[Component3D]) -> Dict[str, Any]:
        """
        Perform belief propagation decoding for error correction.
        
        Args:
            syndrome: Current syndrome vector
            components: List of circuit components
            
        Returns:
            Dictionary with correction results
        """
        if len(syndrome) == 0:
            return {'success': False, 'error': 'No syndrome available'}
        
        # Count data qubits
        data_qubits = [c for c in components if c.component_type == ComponentType.DATA_QUBIT]
        num_bits = len(data_qubits)
        
        if num_bits == 0:
            return {'success': False, 'error': 'No data qubits found'}
        
        # Simple belief propagation simulation
        max_iterations = 10
        convergence_threshold = 1e-6
        
        # Initialize belief probabilities
        beliefs = np.ones(num_bits) * 0.5  # Initial probability of error
        
        correction_history = []
        
        for iteration in range(max_iterations):
            old_beliefs = beliefs.copy()
            
            # Update beliefs based on syndrome constraints
            # (Simplified belief propagation)
            if len(syndrome) > 0:
                syndrome_weight = np.sum(syndrome) / len(syndrome)
                # Adjust beliefs based on syndrome weight
                for i in range(num_bits):
                    # Simple heuristic: if syndrome indicates errors, increase error probability
                    if syndrome_weight > 0.5:
                        beliefs[i] = min(0.9, beliefs[i] + syndrome_weight * 0.2)
                    else:
                        beliefs[i] = max(0.1, beliefs[i] - (1 - syndrome_weight) * 0.1)
            
            beliefs = np.clip(beliefs, 0.01, 0.99)
            correction_history.append(beliefs.copy())
            
            # Check convergence
            if np.linalg.norm(beliefs - old_beliefs) < convergence_threshold:
                break
        
        # Determine correction
        correction = (beliefs > 0.5).astype(int)
        
        result = {
            'success': True,
            'correction': correction,
            'beliefs': beliefs,
            'iterations': iteration + 1,
            'history': correction_history,
            'syndrome_weight': np.sum(syndrome),
            'num_data_qubits': num_bits
        }
        
        self.error_corrections.append(result)
        return result


class CircuitBuilder3D:
    """
    Main application class for the 3D Quantum LDPC Circuit Builder.
    
    This class manages the GUI, user interactions, and coordinates between
    the rendering system and quantum computation backend.
    """
    
    def __init__(self):
        """Initialize the circuit builder application."""
        self.root = self._setup_gui()
        self.components = []
        self.selected_component = None
        self.component_counter = 0
        self.grid_size = 20
        self.current_tool = ComponentType.DATA_QUBIT
        
        # Rendering and computation
        self.renderer = None
        self.processor = QuantumLDPCProcessor()
        
        # Drag and drop state
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_component = None
        
        # Grid panning state
        self.panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        
        self._setup_ui()
        self._bind_events()
    
    def _setup_gui(self) -> tk.Tk:
        """Set up the main GUI window with dark theme."""
        root = tk.Tk()
        root.title("Quantum LDPC Circuit Builder 3D")
        root.geometry("1400x900")
        root.configure(bg='#2b2b2b')
        
        # Configure dark theme style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Dark theme colors
        style.configure('Dark.TFrame', background='#2b2b2b')
        style.configure('Dark.TLabel', background='#2b2b2b', foreground='#ffffff')
        style.configure('Dark.TLabelframe', background='#2b2b2b', foreground='#ffffff', 
                       borderwidth=1, relief='solid')
        style.configure('Dark.TLabelframe.Label', background='#2b2b2b', foreground='#ffffff',
                       font=('TkDefaultFont', 9, 'bold'))
        style.configure('Dark.TButton', background='#404040', foreground='#ffffff')
        style.configure('Dark.TNotebook', background='#2b2b2b')
        style.configure('Dark.TNotebook.Tab', background='#404040', foreground='#ffffff')
        
        return root
    
    def _setup_ui(self):
        """Set up the user interface components."""
        # Clear any existing widgets first
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Main container
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Circuit building area
        left_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Circuit canvas
        self.canvas = tk.Canvas(left_frame, bg='#1e1e1e', highlightthickness=1, 
                               highlightbackground='#404040')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Initialize renderer
        self.renderer = IsometricRenderer(self.canvas)
        
        # Right panel - Controls and toolbox
        right_frame = ttk.Frame(main_frame, style='Dark.TFrame', width=300)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        right_frame.pack_propagate(False)
        
        self._setup_toolbox(right_frame)
        self._setup_controls(right_frame)
        self._setup_status(right_frame)
        
        # Draw initial grid
        self._draw_grid()
    
    def _setup_toolbox(self, parent):
        """Set up the component toolbox."""
        # Use a simple Frame instead of LabelFrame to avoid text duplication
        toolbox_container = ttk.Frame(parent, style='Dark.TFrame')
        toolbox_container.pack(fill=tk.X, padx=5, pady=5)
        
        # Add a simple label for the title
        toolbox_label = ttk.Label(toolbox_container, text="Component Toolbox", 
                                style='Dark.TLabel', font=('TkDefaultFont', 9, 'bold'))
        toolbox_label.pack(anchor=tk.W, padx=5, pady=(5, 2))
        
        # Add a separator line
        separator = ttk.Separator(toolbox_container, orient='horizontal')
        separator.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Component categories
        categories = {
            "Single Qubit Gates": [
                ComponentType.X_GATE, ComponentType.Z_GATE, ComponentType.Y_GATE,
                ComponentType.H_GATE, ComponentType.S_GATE, ComponentType.T_GATE
            ],
            "Two Qubit Gates": [
                ComponentType.CNOT_GATE, ComponentType.CZ_GATE, ComponentType.SWAP_GATE
            ],
            "LDPC Components": [
                ComponentType.PARITY_CHECK, ComponentType.DATA_QUBIT, 
                ComponentType.ANCILLA_QUBIT, ComponentType.SYNDROME_EXTRACT
            ],
            "Measurement": [
                ComponentType.MEASURE, ComponentType.RESET
            ]
        }
        
        # Create notebook for categories
        notebook = ttk.Notebook(toolbox_container, style='Dark.TNotebook')
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        for category, components in categories.items():
            tab_frame = ttk.Frame(notebook, style='Dark.TFrame')
            notebook.add(tab_frame, text=category)
            
            for i, comp_type in enumerate(components):
                btn = ttk.Button(tab_frame, text=comp_type.value,
                               command=lambda ct=comp_type: self._select_tool(ct),
                               style='Dark.TButton')
                btn.pack(fill=tk.X, padx=2, pady=1)
    
    def _setup_controls(self, parent):
        """Set up control buttons and options."""
        # Use a simple Frame instead of LabelFrame to avoid text duplication
        controls_container = ttk.Frame(parent, style='Dark.TFrame')
        controls_container.pack(fill=tk.X, padx=5, pady=5)
        
        # Add a simple label for the title
        controls_label = ttk.Label(controls_container, text="Controls", 
                                 style='Dark.TLabel', font=('TkDefaultFont', 9, 'bold'))
        controls_label.pack(anchor=tk.W, padx=5, pady=(5, 2))
        
        # Add a separator line
        separator = ttk.Separator(controls_container, orient='horizontal')
        separator.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Circuit operations
        ttk.Button(controls_container, text="Clear Circuit",
                  command=self._clear_circuit, style='Dark.TButton').pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(controls_container, text="Save Circuit",
                  command=self._save_circuit, style='Dark.TButton').pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(controls_container, text="Load Circuit",
                  command=self._load_circuit, style='Dark.TButton').pack(fill=tk.X, padx=5, pady=2)
        
        # Separator
        ttk.Separator(controls_container, orient='horizontal').pack(fill=tk.X, padx=5, pady=5)
        
        # Quantum operations
        ttk.Button(controls_container, text="Calculate Syndrome",
                  command=self._calculate_syndrome, style='Dark.TButton').pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(controls_container, text="Run Error Correction",
                  command=self._run_error_correction, style='Dark.TButton').pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(controls_container, text="Simulate Evolution",
                  command=self._simulate_evolution, style='Dark.TButton').pack(fill=tk.X, padx=5, pady=2)
    
    def _setup_status(self, parent):
        """Set up status display area."""
        # Circuit title display
        title_container = ttk.Frame(parent, style='Dark.TFrame')
        title_container.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        title_label = ttk.Label(title_container, text="Current Circuit:", 
                              style='Dark.TLabel', font=('TkDefaultFont', 8))
        title_label.pack(anchor=tk.W, padx=5)
        
        self.circuit_title_label = ttk.Label(title_container, text="New Circuit", 
                                           style='Dark.TLabel', font=('TkDefaultFont', 10, 'bold'),
                                           foreground='#00ff88')
        self.circuit_title_label.pack(anchor=tk.W, padx=5)
        
        # Add separator
        separator = ttk.Separator(title_container, orient='horizontal')
        separator.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # Use a simple Frame instead of LabelFrame to avoid text duplication
        status_container = ttk.Frame(parent, style='Dark.TFrame')
        status_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add a simple label for the title
        status_label = ttk.Label(status_container, text="Status", 
                               style='Dark.TLabel', font=('TkDefaultFont', 9, 'bold'))
        status_label.pack(anchor=tk.W, padx=5, pady=(5, 2))
        
        # Add a separator line
        separator = ttk.Separator(status_container, orient='horizontal')
        separator.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Status text container
        text_container = ttk.Frame(status_container, style='Dark.TFrame')
        text_container.pack(fill=tk.BOTH, expand=True, padx=5)
        
        # Status text
        self.status_text = tk.Text(text_container, height=10, bg='#1e1e1e', fg='#ffffff',
                                  insertbackground='#ffffff', selectbackground='#404040')
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(text_container, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
        
        self._log_status("Circuit Builder initialized. Select a component and click to place.")
    
    def _format_circuit_title(self, filename):
        """Format a filename into a clean circuit title."""
        if not filename:
            return "New Circuit"
        
        # Remove file extension
        name = filename
        if name.endswith('.json'):
            name = name[:-5]
        
        # Replace underscores with spaces and capitalize words
        name = name.replace('_', ' ')
        
        # Capitalize each word
        words = name.split()
        formatted_words = []
        for word in words:
            if word:  # Skip empty strings
                formatted_words.append(word.capitalize())
        
        return ' '.join(formatted_words) if formatted_words else "New Circuit"
    
    def _update_circuit_title(self, title):
        """Update the circuit title display."""
        if hasattr(self, 'circuit_title_label'):
            self.circuit_title_label.config(text=title)
    
    def _bind_events(self):
        """Bind mouse and keyboard events."""
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<Button-2>", self._on_middle_click)  # Middle mouse for panning
        self.canvas.bind("<B2-Motion>", self._on_pan_drag)
        self.canvas.bind("<ButtonRelease-2>", self._on_pan_release)
        self.root.bind("<Delete>", self._delete_selected)
        self.root.bind("<Control-c>", self._copy_selected)
        self.root.bind("<Control-v>", self._paste_component)
    
    def _draw_grid(self):
        """Draw the isometric grid for component placement."""
        self.canvas.delete("grid")
        
        grid_color = "#404040"
        boundary_color = "#606060"  # Brighter color for boundaries
        grid_range = 10  # Match the grid boundaries
        
        # Draw grid lines
        for i in range(-grid_range, grid_range + 1):
            for j in range(-grid_range, grid_range + 1):
                x1, y1 = self.renderer.project_3d_to_2d(i, j, 0)
                x2, y2 = self.renderer.project_3d_to_2d(i + 1, j, 0)
                x3, y3 = self.renderer.project_3d_to_2d(i, j + 1, 0)
                
                # Use boundary color for edge lines
                color = boundary_color if (i == -grid_range or i == grid_range or 
                                        j == -grid_range or j == grid_range) else grid_color
                
                if i < grid_range:  # Don't draw beyond the boundary
                    self.canvas.create_line(x1, y1, x2, y2, fill=color, tags="grid")
                if j < grid_range:  # Don't draw beyond the boundary
                    self.canvas.create_line(x1, y1, x3, y3, fill=color, tags="grid")
    
    def _select_tool(self, component_type: ComponentType):
        """Select a component type for placement."""
        self.current_tool = component_type
        self._log_status(f"Selected tool: {component_type.value}")
    
    def _on_canvas_click(self, event):
        """Handle canvas click events for component placement."""
        # Convert screen coordinates to grid coordinates
        grid_x, grid_y = self._screen_to_grid(event.x, event.y)
        
        # Check if clicking on existing component
        clicked_component = self._get_component_at_position(grid_x, grid_y)
        
        if clicked_component:
            self._select_component(clicked_component)
            self.dragging = True
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            self.drag_component = clicked_component
        else:
            # Place new component
            self._place_component(grid_x, grid_y, 0)
    
    def _on_canvas_drag(self, event):
        """Handle canvas drag events for component movement."""
        if self.dragging and self.drag_component:
            grid_x, grid_y = self._screen_to_grid(event.x, event.y)
            
            # Define grid boundaries
            grid_min = -10
            grid_max = 10
            
            # Check if new position is within grid boundaries
            if (grid_x < grid_min or grid_x > grid_max or 
                grid_y < grid_min or grid_y > grid_max):
                return  # Don't allow dragging outside grid
            
            # Check if new position is occupied by another component
            existing_component = self._get_component_at_position(grid_x, grid_y)
            if existing_component and existing_component != self.drag_component:
                return  # Don't allow stacking components
            
            # Update component position
            old_pos = self.drag_component.position
            self.drag_component.position = (grid_x, grid_y, old_pos[2])
            
            self._redraw_circuit()
    
    def _on_canvas_release(self, event):
        """Handle canvas button release events."""
        self.dragging = False
        self.drag_component = None
    
    def _on_right_click(self, event):
        """Handle right-click context menu."""
        grid_x, grid_y = self._screen_to_grid(event.x, event.y)
        component = self._get_component_at_position(grid_x, grid_y)
        
        if component:
            self._show_context_menu(event, component)
    
    def _on_middle_click(self, event):
        """Handle middle-click for grid panning."""
        self.panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
    
    def _on_pan_drag(self, event):
        """Handle grid panning with middle mouse drag."""
        if self.panning:
            dx = event.x - self.pan_start_x
            dy = event.y - self.pan_start_y
            
            # Update renderer offset
            self.renderer.offset_x += dx
            self.renderer.offset_y += dy
            
            # Redraw grid and components
            self._draw_grid()
            self._redraw_circuit()
            
            # Update pan start position
            self.pan_start_x = event.x
            self.pan_start_y = event.y
    
    def _on_pan_release(self, event):
        """Handle middle mouse button release."""
        self.panning = False
    
    def _screen_to_grid(self, screen_x: float, screen_y: float) -> Tuple[int, int]:
        """Convert screen coordinates to grid coordinates."""
        # Reverse isometric projection (approximate)
        relative_x = screen_x - self.renderer.offset_x
        relative_y = screen_y - self.renderer.offset_y
        
        # Simple approximation - can be improved for accuracy
        grid_x = round((relative_x / self.renderer.scale / self.renderer.cos_30 + 
                       relative_y / self.renderer.scale / self.renderer.sin_30) / 2)
        grid_y = round((relative_y / self.renderer.scale / self.renderer.sin_30 - 
                       relative_x / self.renderer.scale / self.renderer.cos_30) / 2)
        
        return grid_x, grid_y
    
    def _get_component_at_position(self, grid_x: int, grid_y: int) -> Optional[Component3D]:
        """Get component at specified grid position."""
        for component in self.components:
            comp_x, comp_y, comp_z = component.position
            if comp_x == grid_x and comp_y == grid_y:
                return component
        return None
    
    def _place_component(self, grid_x: int, grid_y: int, grid_z: int):
        """Place a new component at the specified grid position."""
        # Define grid boundaries
        grid_min = -10
        grid_max = 10
        
        # Check if position is within grid boundaries
        if (grid_x < grid_min or grid_x > grid_max or 
            grid_y < grid_min or grid_y > grid_max):
            self._log_status(f"Cannot place component outside grid boundaries ({grid_min} to {grid_max})")
            return
        
        # Check if position is occupied
        if self._get_component_at_position(grid_x, grid_y):
            self._log_status(f"Position ({grid_x}, {grid_y}) is already occupied!")
            return
        
        # Get component color based on type
        color = self._get_component_color(self.current_tool)
        
        # Create new component
        component = Component3D(
            component_type=self.current_tool,
            position=(grid_x, grid_y, grid_z),
            color=color,
            size=(1.0, 1.0, 1.0)
        )
        
        self.components.append(component)
        self.component_counter += 1
        
        self._log_status(f"Placed {self.current_tool.value} at ({grid_x}, {grid_y}, {grid_z})")
        self._redraw_circuit()
    
    def _get_component_color(self, component_type: ComponentType) -> Tuple[float, float, float]:
        """Get color for component type."""
        color_map = {
            # Single qubit gates - distinct blue shades
            ComponentType.X_GATE: (0.1, 0.3, 0.9),     # Bright blue
            ComponentType.Z_GATE: (0.2, 0.5, 0.7),     # Medium blue
            ComponentType.Y_GATE: (0.4, 0.7, 1.0),     # Light blue
            ComponentType.H_GATE: (0.0, 0.2, 0.6),     # Dark blue
            ComponentType.S_GATE: (0.3, 0.4, 0.8),     # Purple-blue
            ComponentType.T_GATE: (0.5, 0.6, 0.9),     # Lavender
            
            # Two qubit gates - distinct purple/magenta shades
            ComponentType.CNOT_GATE: (0.8, 0.2, 0.6),  # Magenta
            ComponentType.CZ_GATE: (0.6, 0.1, 0.8),    # Purple
            ComponentType.SWAP_GATE: (0.9, 0.4, 0.7),  # Pink
            
            # LDPC components - distinct green/orange shades
            ComponentType.PARITY_CHECK: (0.9, 0.5, 0.1),   # Orange
            ComponentType.DATA_QUBIT: (0.2, 0.9, 0.3),     # Bright green
            ComponentType.ANCILLA_QUBIT: (0.6, 0.8, 0.1),  # Yellow-green
            ComponentType.SYNDROME_EXTRACT: (0.1, 0.7, 0.5), # Teal
            
            # Measurement - distinct red shades
            ComponentType.MEASURE: (0.9, 0.1, 0.1),    # Bright red
            ComponentType.RESET: (0.7, 0.3, 0.2),      # Dark red
        }
        
        return color_map.get(component_type, (0.5, 0.5, 0.5))
    
    def _redraw_circuit(self):
        """Redraw the entire circuit."""
        # Clear previous components
        self.canvas.delete("component")
        
        # Draw all components
        for component in self.components:
            x, y, z = component.position
            w, h, d = component.size
            
            # Draw the component cube
            items = self.renderer.draw_cube(x, y, z, w, h, d, component.color)
            
            # Tag items for deletion and selection
            for item in items:
                self.canvas.addtag_withtag("component", item)
            
            # Add component label
            center_x, center_y = self.renderer.project_3d_to_2d(x + w/2, y + d/2, z + h + 0.2)
            self.canvas.create_text(center_x, center_y, text=component.component_type.value,
                                  fill="#ffffff", font=("Arial", 8), tags="component")
            
            # Add rotation indicator if component is rotated
            if component.rotation != 0:
                # Draw small arrow to show rotation direction
                arrow_length = 15
                angle_rad = math.radians(component.rotation)
                arrow_end_x = center_x + arrow_length * math.cos(angle_rad)
                arrow_end_y = center_y + arrow_length * math.sin(angle_rad)
                
                self.canvas.create_line(center_x, center_y, arrow_end_x, arrow_end_y,
                                      fill="#ffff00", width=2, arrow=tk.LAST, tags="component")
                
                # Add rotation angle text
                self.canvas.create_text(center_x + 20, center_y - 10, text=f"{component.rotation}°",
                                      fill="#ffff00", font=("Arial", 7), tags="component")
    
    def _select_component(self, component: Component3D):
        """Select a component for manipulation."""
        self.selected_component = component
        self._log_status(f"Selected {component.component_type.value} at {component.position}")
    
    def _show_context_menu(self, event, component: Component3D):
        """Show context menu for component operations."""
        context_menu = tk.Menu(self.root, tearoff=0, bg='#404040', fg='#ffffff',
                              activebackground='#606060', activeforeground='#ffffff')
        
        context_menu.add_command(label="Rotate", 
                               command=lambda: self._rotate_component(component))
        context_menu.add_command(label="Duplicate", 
                               command=lambda: self._duplicate_component(component))
        context_menu.add_command(label="Delete", 
                               command=lambda: self._delete_component(component))
        context_menu.add_separator()
        context_menu.add_command(label="Properties", 
                               command=lambda: self._show_properties(component))
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def _rotate_component(self, component: Component3D):
        """Rotate a component by 90 degrees."""
        component.rotation = (component.rotation + 90) % 360
        self._log_status(f"Rotated {component.component_type.value} to {component.rotation}°")
        self._redraw_circuit()
    
    def _duplicate_component(self, component: Component3D):
        """Duplicate a component at an adjacent position."""
        x, y, z = component.position
        
        # Try to find an adjacent free position
        adjacent_positions = [(x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z)]
        
        for new_x, new_y, new_z in adjacent_positions:
            # Check grid boundaries
            if (new_x < -10 or new_x > 10 or new_y < -10 or new_y > 10):
                continue
                
            # Check if position is free
            if not self._get_component_at_position(new_x, new_y):
                new_component = Component3D(
                    component_type=component.component_type,
                    position=(new_x, new_y, new_z),
                    rotation=component.rotation,
                    size=component.size,
                    color=component.color,
                    connections=component.connections.copy(),
                    properties=component.properties.copy()
                )
                
                self.components.append(new_component)
                self._log_status(f"Duplicated {component.component_type.value} at ({new_x}, {new_y}, {new_z})")
                self._redraw_circuit()
                return
        
        # No free adjacent position found
        self._log_status("No free adjacent position available for duplication")
    
    def _delete_component(self, component: Component3D):
        """Delete a component from the circuit."""
        if component in self.components:
            self.components.remove(component)
            if self.selected_component == component:
                self.selected_component = None
            self._log_status(f"Deleted {component.component_type.value}")
            self._redraw_circuit()
    
    def _delete_selected(self, event):
        """Delete currently selected component."""
        if self.selected_component:
            self._delete_component(self.selected_component)
    
    def _copy_selected(self, event):
        """Copy currently selected component."""
        if self.selected_component:
            self._duplicate_component(self.selected_component)
    
    def _paste_component(self, event):
        """Paste component at cursor position."""
        # Implementation for paste functionality
        pass
    
    def _show_properties(self, component: Component3D):
        """Show component properties dialog."""
        props_window = tk.Toplevel(self.root)
        props_window.title(f"{component.component_type.value} Properties")
        props_window.configure(bg='#2b2b2b')
        props_window.geometry("300x400")
        
        # Properties display
        props_frame = ttk.Frame(props_window, style='Dark.TFrame')
        props_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Component info
        ttk.Label(props_frame, text=f"Type: {component.component_type.value}",
                 style='Dark.TLabel').pack(anchor=tk.W, pady=2)
        ttk.Label(props_frame, text=f"Position: {component.position}",
                 style='Dark.TLabel').pack(anchor=tk.W, pady=2)
        ttk.Label(props_frame, text=f"Rotation: {component.rotation}°",
                 style='Dark.TLabel').pack(anchor=tk.W, pady=2)
        ttk.Label(props_frame, text=f"Size: {component.size}",
                 style='Dark.TLabel').pack(anchor=tk.W, pady=2)
        
        # Additional properties
        if component.properties:
            ttk.Separator(props_frame, orient='horizontal').pack(fill=tk.X, pady=10)
            ttk.Label(props_frame, text="Custom Properties:",
                     style='Dark.TLabel').pack(anchor=tk.W, pady=2)
            
            for key, value in component.properties.items():
                ttk.Label(props_frame, text=f"{key}: {value}",
                         style='Dark.TLabel').pack(anchor=tk.W, pady=1)
    
    def _clear_circuit(self):
        """Clear all components from the circuit."""
        self.components.clear()
        self.selected_component = None
        self._update_circuit_title("New Circuit")
        self._log_status("Circuit cleared")
        self._redraw_circuit()
    
    def _save_circuit(self):
        """Save current circuit to file."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Circuit"
        )
        
        if filename:
            try:
                circuit_data = {
                    'components': [
                        {
                            'type': comp.component_type.value,
                            'position': comp.position,
                            'rotation': comp.rotation,
                            'size': comp.size,
                            'color': comp.color,
                            'connections': comp.connections,
                            'properties': comp.properties
                        }
                        for comp in self.components
                    ]
                }
                
                with open(filename, 'w') as f:
                    json.dump(circuit_data, f, indent=2)
                
                # Update circuit title
                circuit_name = os.path.basename(filename)
                formatted_title = self._format_circuit_title(circuit_name)
                self._update_circuit_title(formatted_title)
                
                self._log_status(f"Circuit saved to {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save circuit: {e}")
    
    def _load_circuit(self):
        """Load circuit from file."""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Load Circuit"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    circuit_data = json.load(f)
                
                # Clear current circuit
                self.components.clear()
                
                # Load components
                for comp_data in circuit_data.get('components', []):
                    # Find component type
                    comp_type = None
                    for ct in ComponentType:
                        if ct.value == comp_data['type']:
                            comp_type = ct
                            break
                    
                    if comp_type:
                        component = Component3D(
                            component_type=comp_type,
                            position=tuple(comp_data['position']),
                            rotation=comp_data.get('rotation', 0.0),
                            size=tuple(comp_data.get('size', (1.0, 1.0, 1.0))),
                            color=tuple(comp_data.get('color', (0.5, 0.5, 0.5))),
                            connections=comp_data.get('connections', []),
                            properties=comp_data.get('properties', {})
                        )
                        self.components.append(component)
                
                # Update circuit title
                circuit_name = os.path.basename(filename)
                formatted_title = self._format_circuit_title(circuit_name)
                self._update_circuit_title(formatted_title)
                
                self._log_status(f"Circuit loaded from {filename}")
                self._redraw_circuit()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load circuit: {e}")
    
    def _calculate_syndrome(self):
        """Calculate syndrome for current circuit."""
        try:
            syndrome = self.processor.calculate_syndrome(self.components)
            
            if len(syndrome) > 0:
                # Count circuit components for context
                data_qubits = len([c for c in self.components if c.component_type == ComponentType.DATA_QUBIT])
                ancilla_qubits = len([c for c in self.components if c.component_type == ComponentType.ANCILLA_QUBIT])
                parity_checks = len([c for c in self.components if c.component_type == ComponentType.PARITY_CHECK])
                
                self._log_status(f"=== Syndrome Calculation ===")
                self._log_status(f"Data qubits: {data_qubits}, Ancilla qubits: {ancilla_qubits}, Parity checks: {parity_checks}")
                self._log_status(f"Syndrome: {syndrome}")
                self._log_status(f"Syndrome weight: {np.sum(syndrome)} / {len(syndrome)}")
                
                if np.sum(syndrome) == 0:
                    self._log_status("✓ No errors detected (all syndrome bits are 0)")
                else:
                    self._log_status(f"⚠ Errors detected (syndrome weight: {np.sum(syndrome)})")
            else:
                self._log_status("No syndrome extractors found. Need ancilla qubits or parity check components.")
                
        except Exception as e:
            self._log_status(f"Error calculating syndrome: {e}")
    
    def _run_error_correction(self):
        """Run error correction algorithm."""
        try:
            # First calculate syndrome
            syndrome = self.processor.calculate_syndrome(self.components)
            
            if len(syndrome) == 0:
                self._log_status("No syndrome available for error correction. Need ancilla qubits or parity checks.")
                return
            
            # Run error correction
            result = self.processor.perform_error_correction(syndrome, self.components)
            
            if result['success']:
                correction = result['correction']
                beliefs = result['beliefs']
                iterations = result['iterations']
                syndrome_weight = result.get('syndrome_weight', 0)
                num_data_qubits = result.get('num_data_qubits', 0)
                
                self._log_status(f"=== Error Correction Results ===")
                self._log_status(f"Converged in {iterations} iterations")
                self._log_status(f"Data qubits: {num_data_qubits}, Syndrome weight: {syndrome_weight}")
                self._log_status(f"Correction vector: {correction}")
                self._log_status(f"Error probabilities: {[f'{p:.3f}' for p in beliefs]}")
                
                # Provide interpretation
                if np.sum(correction) == 0:
                    self._log_status("✓ No corrections needed")
                else:
                    self._log_status(f"⚠ Applying {np.sum(correction)} corrections")
                    
            else:
                self._log_status(f"Error correction failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self._log_status(f"Error during error correction: {e}")
                
        except Exception as e:
            self._log_status(f"Error in correction algorithm: {e}")
    
    def _simulate_evolution(self):
        """Simulate quantum state evolution."""
        try:
            circuit = self.processor.build_circuit_from_components(self.components)
            
            if circuit is None:
                self._log_status("Failed to build quantum circuit")
                return
            
            if QISKIT_AVAILABLE and hasattr(circuit, 'num_qubits'):
                # Run actual quantum simulation
                simulator = AerSimulator()
                
                # Add measurements if not present
                if not any(instr.operation.name == 'measure' for instr in circuit.data):
                    circuit.measure_all()
                
                # Execute circuit
                transpiled = transpile(circuit, simulator)
                job = simulator.run(transpiled, shots=1024)
                result = job.result()
                counts = result.get_counts()
                
                self._log_status("Quantum state evolution completed")
                self._log_status(f"Measurement results: {counts}")
                
                # Display most frequent outcomes
                sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
                for state, count in sorted_counts[:5]:
                    probability = count / 1024
                    self._log_status(f"State |{state}>: {probability:.3f}")
            
            else:
                # Fallback simulation
                self._log_status("Quantum evolution simulation (classical fallback)")
                self._log_status(f"Circuit stats: {circuit}")
                
        except Exception as e:
            self._log_status(f"Error in quantum simulation: {e}")
    
    def _log_status(self, message: str):
        """Log a status message to the status display."""
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.root.update_idletasks()
    
    def run(self):
        """Start the application main loop."""
        self._log_status("Starting Quantum LDPC Circuit Builder 3D")
        self._log_status("Ready for interactive circuit construction!")
        self._log_status("TIP: Middle-click and drag to pan the grid view")
        self._log_status("TIP: Right-click components for rotation and other options")
        self._log_status("IMPROVEMENT: Grid boundaries enforced - components cannot be placed outside grid")
        self._log_status("IMPROVEMENT: Component stacking prevented - only one component per grid position")
        self.root.mainloop()


def main():
    """Main entry point for the application."""
    try:
        app = CircuitBuilder3D()
        app.run()
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()