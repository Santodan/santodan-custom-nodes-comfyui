from .santodan_nodes.random_lora_nodes import *

NODE_CLASS_MAPPINGS = {
    "RandomLoRACustom": RandomLoRACustom,
    "RandomLoRAFolder": RandomLoRAFolder,
    "LoRACachePreloader": LoRACachePreloader,
    "ExcludedLoras": ExcludedLoras,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomLoRACustom": "Random LoRA Selector",
    "RandomLoRAFolder": "Random LoRA Folder Selector",
    "LoRACachePreloader": "LoRA Cache Preloader",
    "ExcludedLoras": "Excluded Loras",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
