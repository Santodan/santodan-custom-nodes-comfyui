from .santodan_nodes.random_lora_node import *

NODE_CLASS_MAPPINGS = {
    "RandomLoRACustom": RandomLoRACustom,
    "RandomLoRAFolder": RandomLoRAFolder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomLoRACustom": "Random LoRA Selector",
    "RandomLoRAFolder": "Random LoRA Folder Selector",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
