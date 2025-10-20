import time
import torch
from datetime import datetime

class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False
any_typ = AnyType("*")

class SplitBatchWithPrefix:
    """
    Takes a batch of images and outputs one image and one string per iteration.
    Each image is assigned an incremental prefix-based name.
    Compatible with Save Image.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "subfolder": ("STRING", {"default": ""}),
                "filename": ("STRING", {"default": "_SDXL_"}),
                "index": ("INT", {"default": 0, "min": 0, "max": 9999}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "name")
    FUNCTION = "pair_one"
    CATEGORY = "Santodan/utils"

    def __init__(self):
        self.current_global_index = 0
        self.last_input_index = None
        self.last_filename = None
        self.last_subfolder = None
        self.last_call_time = 0.0
        # time window (seconds) to consider sequential calls part of the same run
        self._same_run_window = 1.0

    def pair_one(self, images, filename, index, subfolder):
        if not isinstance(images, torch.Tensor):
            raise ValueError("Expected 'images' to be a torch.Tensor")

        if images.ndim != 4:
            raise ValueError(f"Expected [B,H,W,C] tensor, got {images.shape}")

        # Replace %date:yyyy-MM-dd% with actual date
        if '%date:' in subfolder:
            today = datetime.now()
            subfolder = subfolder.replace('%date:yyyy-MM-dd%', today.strftime('%Y-%m-%d'))

        # detect new run:
        now = time.time()
        if (self.last_input_index != index or 
            self.last_filename != filename or 
            self.last_subfolder != subfolder):
            # new run parameters -> reset
            self.current_global_index = 0
        else:
            # if the previous call was long ago, treat as a new run
            if (now - self.last_call_time) > self._same_run_window:
                self.current_global_index = 0

        # update run tracking
        self.last_input_index = index
        self.last_filename = filename
        self.last_subfolder = subfolder
        self.last_call_time = now

        # Calculate the batch size
        batch_size = images.shape[0]

        # Use modulo to wrap around the index instead of resetting
        current_image_index = self.current_global_index % batch_size

        # Select the image using the current image index
        img = images[current_image_index].unsqueeze(0)
        
        # Create path with subfolder
        subfolder = subfolder.strip().rstrip('/')  # Remove trailing slashes
        if subfolder:
            name = f"{subfolder}/{self.current_global_index + index}{filename}"
        else:
            name = f"{self.current_global_index + index}{filename}"

        self.current_global_index += 1

        return (img, name)
