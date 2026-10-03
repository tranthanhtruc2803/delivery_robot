import torch
import os
from models.loc_model_basic import LocModel1D

# --- CONFIGURATION ---
WEIGHTS_PATH = "data/lfe_ppn_best_V3.pth"
ONNX_PATH = "results/lfe_ppn.onnx"
os.makedirs("results", exist_ok=True)

# Define your input parameters
BATCH_SIZE = 1  # 1 is standard for real-time Jetson inference
# Replace these with the actual values from your FrogDataLoader
SCAN_LENGTH = 1080  # The 'L' dimension in your (B, 1, L) tensor
NUM_ANCHORS_PER_SECTOR = 2  

def export_to_onnx():
    device = torch.device("cpu") # CPU is fine for exporting

    # 1. Initialize the model
    print("Initializing model...")
    model = LocModel1D(
        num_anchors_per_sector=NUM_ANCHORS_PER_SECTOR,
        glob=True
    ).to(device)

    # 2. Load the trained weights
    if not os.path.exists(WEIGHTS_PATH):
        print(f"Error: Weights not found at {WEIGHTS_PATH}")
        return

    model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device))
    model.eval() # CRITICAL: Set to eval mode before export

    # 3. Create dummy input matching (B, 1, L)
    print("Creating dummy input...")
    dummy_input = torch.randn(BATCH_SIZE, 1, SCAN_LENGTH, device=device)

    # 4. Export to ONNX
    print(f"Exporting model to {ONNX_PATH}...")
    torch.onnx.export(
        model,                      # Model being run
        dummy_input,                # Model input (or a tuple for multiple inputs)
        ONNX_PATH,                  # Where to save the model
        export_params=True,         # Store the trained parameter weights inside the model file
        opset_version=11,           # Opset 11 or 13 is highly compatible with TensorRT
        do_constant_folding=True,   # Optimize constant folding for deployment
        input_names=['input_scan'], # Custom name for the input
        output_names=['output_loc'],# Custom name for the output
        dynamic_axes={              # Allow dynamic batch sizes (optional but recommended)
            'input_scan': {0: 'batch_size'},
            'output_loc': {0: 'batch_size'}
        }
    )
    print("Export complete! You can now move the ONNX file to your Jetson Orin Nano.")

if __name__ == "__main__":
    export_to_onnx()
