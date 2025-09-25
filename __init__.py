from .santodan_nodes.random_lora_nodes import *
from .santodan_nodes.wildcard import *

NODE_CLASS_MAPPINGS = {
    "RandomLoRACustom": RandomLoRACustom,
    "RandomLoRAFolder": RandomLoRAFolder,
    "LoRACachePreloader": LoRACachePreloader,
    "ExcludedLoras": ExcludedLoras,
    "ExtractAndApplyLoRAs": ExtractAndApplyLoRAs,
    "WildcardManager": WildcardManager,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomLoRACustom": "Random LoRA Selector",
    "RandomLoRAFolder": "Random LoRA Folder Selector",
    "LoRACachePreloader": "LoRA Cache Preloader",
    "ExcludedLoras": "Excluded Loras",
    "ExtractAndApplyLoRAs": "Extract And Apply LoRAs",
    "WildcardManager": "Wildcard Manager",
}

WEB_DIRECTORY = "web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
