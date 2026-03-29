import numpy as np

class IPIC_LossAwareCompiler:
    def __init__(self, mesh_size, base_loss_db=0.1):
        """
        Initializes the LAC Compiler for a specific IPIC MZI mesh.
        :param mesh_size: Number of MZI units in the grid (N x N)
        :param base_loss_db: Average optical insertion loss per MZI junction
        """
        self.N = mesh_size
        self.base_loss = base_loss_db
        # Create a 'Loss Map' representing the physical degradation of the chip
        self.loss_map = self._generate_physical_calibration_map()

    def _generate_physical_calibration_map(self):
        """
        Simulates the 'Singing Machine' diagnostics. 
        In a real chip, this data comes from the Germanium photodetectors.
        """
        # Every MZI has a slightly different loss due to manufacturing variance
        return np.random.normal(self.base_loss, 0.01, (self.N, self.N))

    def compensate_weights(self, target_weights):
        """
        CORE ALGORITHM: Adjusts target weights to counteract physical attenuation.
        Formula: W_compensated = W_target * exp(Total_Path_Loss)
        """
        compensated_mesh = np.zeros_like(target_weights)
        
        for i in range(self.N):
            for j in range(self.N):
                # Calculate cumulative loss based on the light's path (Manhattan distance)
                # Light travels through i rows and j columns to reach junction (i,j)
                path_loss_db = np.sum(self.loss_map[:i+1, :j+1]) / (i + j + 1)
                loss_linear = 10**(-path_loss_db / 10)
                
                # Inverse Mapping: Boost the input phase/power to negate the loss
                # We cap the compensation to avoid laser clipping (Saturation)
                compensation_factor = 1.0 / max(loss_linear, 0.01)
                compensated_mesh[i, j] = target_weights[i, j] * compensation_factor
                
        return compensated_mesh

    def calculate_mzi_phases(self, compensated_weights):
        """
        Converts compensated mathematical weights into physical Phase Shifts (phi).
        U = cos(theta) ... mapping weights to [0, pi]
        """
        # Ensure weights are normalized between 0 and 1 for the MZI range
        norm_weights = np.clip(compensated_weights / np.max(compensated_weights), 0, 1)
        phases = np.arccos(norm_weights) # Mapping to Phase State
        return phases

# --- SIMULATION RUN ---

# 1. Define a 4x4 target weight matrix (e.g., from a Layer in Llama-3)
target_W = np.array([[0.8, 0.2, 0.5, 0.9],
                     [0.1, 0.6, 0.3, 0.4],
                     [0.9, 0.1, 0.7, 0.2],
                     [0.4, 0.5, 0.2, 0.8]])

# 2. Initialize the LAC Compiler
lac = IPIC_LossAwareCompiler(mesh_size=4, base_loss_db=0.15)

# 3. Run Compensation
comp_W = lac.compensate_weights(target_W)

# 4. Generate Physical Control Signals (Phases for the MZIs)
physical_phases = lac.calculate_mzi_phases(comp_W)

print("--- IPIC LAC DIAGNOSTICS ---")
print(f"Target Weight (0,0): {target_W[0,0]}")
print(f"Compensated Weight (0,0): {comp_W[0,0]:.4f} (Boosted to counter loss)")
print(f"Final MZI Phase Shift (rad): {physical_phases[0,0]:.4f}")
