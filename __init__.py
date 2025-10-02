import os

# Import the node classes
from .santodan_nodes.random_lora_nodes import *
from .santodan_nodes.wildcard import *
from .santodan_nodes.promptListTemplate import *
from .santodan_nodes import promptListTemplate
from .santodan_nodes.shutdownNode import *
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
promptListTemplate.initialize_prompt_list_routes()

# --- Node Mappings for ComfyUI ---
NODE_CLASS_MAPPINGS = {
    "RandomLoRACustom": RandomLoRACustom,
    "RandomLoRAFolder": RandomLoRAFolder,
    "LoRACachePreloader": LoRACachePreloader,
    "ExcludedLoras": ExcludedLoras,
    "ExtractAndApplyLoRAs": ExtractAndApplyLoRAs,
    "WildcardManager": WildcardManager,
    "PromptListWithTemplates": PromptListWithTemplates,
    "SaveWorkflowAndShutdown": SaveWorkflowAndShutdown,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomLoRACustom": "Random LoRA Selector",
    "RandomLoRAFolder": "Random LoRA Folder Selector",
    "LoRACachePreloader": "LoRA Cache Preloader",
    "ExcludedLoras": "Excluded Loras",
    "ExtractAndApplyLoRAs": "Extract And Apply LoRAs",
    "WildcardManager": "Wildcard Manager",
    "PromptListWithTemplates": "PromptList w/ Template",
    "Save Workflow & Shutdown": "SaveWorkflowAndShutdown",
}
WEB_DIRECTORY = "web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
