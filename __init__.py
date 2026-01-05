import os    
# Import the node classes
from .santodan_nodes.random_lora_nodes import *
from .santodan_nodes.wildcard import *
from .santodan_nodes.shutdownNode import *
from .santodan_nodes.utils import *
# Import our new API routes module
from .santodan_nodes import server_routes

# --- Setup Paths ---
comfy_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
wildcards_path = os.path.join(comfy_path, "wildcards")

# --- Initialize Wildcards Directory ---
if not os.path.exists(wildcards_path):
    print("Santodan Nodes: Wildcards directory not found, creating it.")
    os.makedirs(wildcards_path)

# --- Initialize API Routes ---
# This single line replaces all the previous API endpoint code
server_routes.initialize_routes(wildcards_path)
server_routes.initialize_prompt_list_routes()

# --- Node Mappings for ComfyUI ---
NODE_CLASS_MAPPINGS = {
    #from random_lora_nodes.py
    "RandomLoRACustom": RandomLoRACustom,
    "RandomLoRACustomModel": RandomLoRACustomModel,
    "RandomLoRAFolder": RandomLoRAFolder,
    "RandomLoRAFolderModel": RandomLoRAFolderModel,
    "LoRACachePreloader": LoRACachePreloader,
    "ExcludedLoras": ExcludedLoras,
    "ExtractAndApplyLoRAs": ExtractAndApplyLoRAs,
    "LoraMetadataHub": LoraMetadataHub,
    #from wildcard.py
    "WildcardManager": WildcardManager,
    #from shutdownNode.py
    "SaveWorkflowAndShutdown": SaveWorkflowAndShutdown,
    #from utils.py
    "PromptListWithTemplates": PromptListWithTemplates,
    "SplitBatchWithPrefix": SplitBatchWithPrefix,
    "ListSelector": ListSelector,
    "ModelAssembler": ModelAssembler,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    #from random_lora_nodes.py
    "RandomLoRACustom": "Random LoRA Selector",
    "RandomLoRAFolder": "Random LoRA Folder Selector",
    "RandomLoRACustomModel": "Random LoRA Selector to Model Selector",
    "RandomLoRAFolderModel": "Random LoRA Folder to Model Selector",
    "LoRACachePreloader": "LoRA Cache Preloader",
    "ExcludedLoras": "Excluded Loras",
    "ExtractAndApplyLoRAs": "Extract And Apply LoRAs",
    "LoraMetadataHub": "LoRA Metadata Hub",
    #from wildcard.py
    "WildcardManager": "Wildcard Manager",
    #from shutdownNode.py
    "Save Workflow & Shutdown": "SaveWorkflowAndShutdown",
    #from utils.py
    "SplitBatchWithPrefix": "Split Batch With Prefix",
    "ListSelector": "List Selector",
    "PromptListWithTemplates": "PromptList w/ Template",
    "ModelAssembler": "Model Assembler",
}
WEB_DIRECTORY = "web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
