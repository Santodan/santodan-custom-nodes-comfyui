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
                "prefix_text": ("STRING", {"default": "-SDXL_"}),
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

    def pair_one(self, images, prefix_text, index):
        if not isinstance(images, torch.Tensor):
            raise ValueError("Expected 'images' to be a torch.Tensor")

        if images.ndim != 4:
            raise ValueError(f"Expected [B,H,W,C] tensor, got {images.shape}")

        # Reset counter if input index changed
        if self.last_input_index != index:
            self.current_global_index = 0
            self.last_input_index = index

        batch_size = images.shape[0]
        # Check if the counter has exceeded the number of images in the batch
        if self.current_global_index >= batch_size:
            # You might want to handle this case, e.g., by looping back to the first image
            # or stopping. For now, we'll just clamp it to the last image.
            print(f"Warning: Global index ({self.current_global_index}) exceeds batch size ({batch_size}). Using last image.")
            current_image_index = batch_size - 1
        else:
            current_image_index = self.current_global_index
            
        print(f"Batch size: {batch_size}")
        print(f"Global index: {self.current_global_index}")
        print(f"Input index: {index}")
        
        # Select the image using the current global index, not always index 0
        img = images[current_image_index].unsqueeze(0)
        name = f"{self.current_global_index + index}{prefix_text}"
        
        self.current_global_index += 1
        
        return (img, name)