from .santodan_nodes.random_lora_nodes import *

NODE_CLASS_MAPPINGS = {
    "RandomLoRACustom": RandomLoRACustom,
    "RandomLoRAFolder": RandomLoRAFolder,
    "LoRACachePreloader": LoRACachePreloader,
    "ExcludedLoras": ExcludedLoras,
    "ExtractAndApplyLoRAs": ExtractAndApplyLoRAs,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomLoRACustom": "Random LoRA Selector",
    "RandomLoRAFolder": "Random LoRA Folder Selector",
    "LoRACachePreloader": "LoRA Cache Preloader",
    "ExcludedLoras": "Excluded Loras",
    "ExtractAndApplyLoRAs": "Extract And Apply LoRAs",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
