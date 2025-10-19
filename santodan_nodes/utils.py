import time
import torch

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
                "filename": ("STRING", {"default": "-SDXL_"}),
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
        self.last_call_time = 0.0
        # time window (seconds) to consider sequential calls part of the same run
        self._same_run_window = 1.0

    def pair_one(self, images, filename, index):
        if not isinstance(images, torch.Tensor):
            raise ValueError("Expected 'images' to be a torch.Tensor")

        if images.ndim != 4:
            raise ValueError(f"Expected [B,H,W,C] tensor, got {images.shape}")

        # detect new run:
        # - reset immediately if the starting index or prefix changed
        # - otherwise, treat closely-timed sequential calls as the same run
        now = time.time()
        if self.last_input_index != index or self.last_filename != filename:
            # new run parameters -> reset
            self.current_global_index = 0
        else:
            # if the previous call was long ago, treat as a new run
            if (now - self.last_call_time) > self._same_run_window:
                self.current_global_index = 0

        # update run tracking
        self.last_input_index = index
        self.last_filename = filename
        self.last_call_time = now

        # Calculate the batch size
        batch_size = images.shape[0]

        # Check if the counter has exceeded the number of images in the batch
        if self.current_global_index >= batch_size:
            # clamp to the last image
            print(f"Warning: Global index ({self.current_global_index}) exceeds batch size ({batch_size}). Using last image.")
            current_image_index = max(0, batch_size - 1)
        else:
            current_image_index = self.current_global_index

        #print(f"Batch size: {batch_size}")
        #print(f"Global index: {self.current_global_index}")
        #print(f"Input index: {index}")

        # Select the image using the current global index
        img = images[current_image_index].unsqueeze(0)
        name = f"{self.current_global_index + index}{filename}"

        self.current_global_index += 1

        return (img, name)