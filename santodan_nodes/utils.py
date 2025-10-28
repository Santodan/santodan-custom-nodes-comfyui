import time
import torch
import random
from nodes import interrupt_processing
#from cozy_comfyui.api import parse_reset, comfy_api_post
from datetime import datetime
import os
import json
import folder_paths
import comfy.sd
import comfy.utils

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

class ListSelector:
    # This class-level dictionary correctly maintains the state for each node instance.
    current_indices = {}

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt_list": ("LIST",),
                "mode": (["all_run", "selected", "increment"],),
                "index": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "stop_at_end": ("BOOLEAN", {"default": False, "label_on": "HALT QUEUE AT END", "label_off": "LOOP AT END"}),
                # --- MODIFIED WIDGET ---
                # This is now a boolean toggle switch. It's more intuitive for a one-shot action.
                "reset_counter": ("BOOLEAN", {"default": False, "label_on": "RESET ON NEXT RUN", "label_off": "NORMAL RUN"})
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO", "unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("prompt", "current_index")
    OUTPUT_IS_LIST = (True, False)
    FUNCTION = "run"
    CATEGORY = "Santodan/Prompt"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN") # Always run this node to check for state changes.

    def run(self, prompt_list, mode, index, stop_at_end, reset_counter, unique_id, prompt, extra_pnginfo):
        node_id = unique_id
        
        if node_id not in self.current_indices:
            self.current_indices[node_id] = 0

        # --- UPDATED RESET LOGIC ---
        # The Python code only needs to check if the toggle is True.
        # The JavaScript will be responsible for turning it back to False.
        if reset_counter:
            print(f"💡 [ListSelector ID: {node_id}] Counter has been reset to 0 by the reset toggle.")
            self.current_indices[node_id] = 0
        
        current_index = self.current_indices[node_id]

        # The rest of the function logic remains the same...
        if not prompt_list:
            return ([""], 0)

        list_size = len(prompt_list)

        if mode == "all_run":
            return (prompt_list, list_size)
        
        elif mode == "selected":
            self.current_indices[node_id] = index
            if 0 <= index < list_size:
                return ([prompt_list[index]], index)
            else:
                return ([""], index)

        elif mode == "increment":
            if current_index >= list_size:
                if stop_at_end:
                    print(f"🛑 [ListSelector ID: {node_id}] Queue is halted. Reset to start again.")
                    interrupt_processing()
                    return ([""], current_index)
                else:
                    print(f"💡 [ListSelector ID: {node_id}] Reached end of list. Looping back to start.")
                    current_index = 0
            
            idx_to_use = current_index
            prompt_to_return = [prompt_list[idx_to_use]]
            
            self.current_indices[node_id] = current_index + 1
            
            return (prompt_to_return, idx_to_use)
        
class PromptListWithTemplates:
    # ... (the entire class definition remains exactly the same as before) ...
    """
    A ComfyUI node to create a list of prompts, with the ability to save, 
    load, and delete the list as a template via an associated JavaScript file.
    """
    
    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "prompt_list_templates")

    def __init__(self):
        os.makedirs(self.TEMPLATE_DIR, exist_ok=True)

    @classmethod
    def get_template_files(cls):
        if not os.path.exists(cls.TEMPLATE_DIR):
            return []
        template_files = []
        for root, _, files in os.walk(cls.TEMPLATE_DIR):
            for file in files:
                if file.endswith(".json"):
                    relative_path = os.path.relpath(os.path.join(root, file), cls.TEMPLATE_DIR)
                    template_files.append(relative_path)
        return sorted(template_files)

    @classmethod
    def INPUT_TYPES(cls):
        os.makedirs(cls.TEMPLATE_DIR, exist_ok=True)
        return {
            "required": {
                "prompt_1": ("STRING", {"multiline": True, "default": ""}),
                "prompt_2": ("STRING", {"multiline": True, "default": ""}),
                "prompt_3": ("STRING", {"multiline": True, "default": ""}),
                "prompt_4": ("STRING", {"multiline": True, "default": ""}),
                "prompt_5": ("STRING", {"multiline": True, "default": ""}),
                "template_file": (["None"] + cls.get_template_files(),),
                "save_filename": ("STRING", {"default": "", "placeholder": "subfolder/template_name.json"}),
            },
            "optional": { "optional_prompt_list": ("LIST",) }
        }

    RETURN_TYPES = ("LIST", "STRING")
    RETURN_NAMES = ("prompt_list", "prompt_strings")
    OUTPUT_IS_LIST = (False, True)
    FUNCTION = "run"
    CATEGORY = "Santodan/Prompt"

    def run(self, prompt_1, prompt_2, prompt_3, prompt_4, prompt_5, template_file, save_filename, optional_prompt_list=None):
        prompts = []
        if optional_prompt_list:
            prompts.extend(optional_prompt_list)
        
        source_prompts = [prompt_1, prompt_2, prompt_3, prompt_4, prompt_5]
        for p in source_prompts:
            if isinstance(p, str) and p.strip() != '':
                prompts.append(p)
                
        return (prompts, prompts)

# --- API Endpoints for JavaScript interaction ---
def get_template_dir():
    return os.path.join(os.path.dirname(__file__), "prompt_list_templates")

class ModelAssembler:
    @classmethod
    def INPUT_TYPES(s):
        checkpoints_list = folder_paths.get_filename_list("checkpoints")
        clips_list = ["None"] + folder_paths.get_filename_list("text_encoders")
        vaes_list = folder_paths.get_filename_list("vae")
        
        # A comprehensive list of clip types from ComfyUI's loaders
        clip_types = [
            "stable_diffusion", "sdxl", "sd3", "stable_cascade", "flux", 
            "hunyuan_video", "hidream", "hunyuan_image", "stable_audio", 
            "mochi", "ltxv", "pixart", "cosmos", "lumina2", "wan", 
            "chroma", "ace", "omnigen2", "qwen_image"
        ]

        return {
            "required": {
                "load_mode": (["full_checkpoint", "separate_components"],),

                # Inputs for 'full_checkpoint' mode
                "ckpt_name": (checkpoints_list,),

                # Inputs for 'separate_components' mode
                "base_model": (checkpoints_list,),
                "weight_dtype": (["default", "fp8_e4m3fn", "fp8_e4m3fn_fast", "fp8_e5m2"],),
                "vae_model": (vaes_list,),
                "clip_type": (clip_types, {"tooltip": "Select the appropriate type for your CLIP model(s). E.g., 'sdxl' for a LoRA/HiRA pair."}),
                "device": (["default", "cpu"], {"advanced": True}),
                "clip_model_1": (clips_list,),
            },
            "optional": {
                "clip_model_2": (clips_list, {"default": "None"}),
                "clip_model_3": (clips_list, {"default": "None"}),
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    FUNCTION = "load_and_assemble"
    CATEGORY = "loaders"

    def load_and_assemble(self, load_mode, ckpt_name, base_model, weight_dtype, vae_model, clip_type, clip_model_1, clip_model_2, clip_model_3, device="default"):
        
        if load_mode == "full_checkpoint":
            ckpt_path = folder_paths.get_full_path("checkpoints", ckpt_name)
            if not ckpt_path: raise FileNotFoundError(f"Checkpoint file not found: {ckpt_name}")
            
            model, clip, vae = comfy.sd.load_checkpoint_guess_config(
                ckpt_path, output_vae=True, output_clip=True,
                embedding_directory=folder_paths.get_folder_paths("embeddings")
            )[:3]
            return (model, clip, vae)

        # --- Separate Components Mode ---

        # 1. Load UNet with correct data type
        unet_options = {}
        if weight_dtype == "fp8_e4m3fn":
            unet_options["dtype"] = torch.float8_e4m3fn
        elif weight_dtype == "fp8_e4m3fn_fast":
            unet_options["dtype"] = torch.float8_e4m3fn
            unet_options["fp8_optimizations"] = True
        elif weight_dtype == "fp8_e5m2":
            unet_options["dtype"] = torch.float8_e5m2
        
        base_model_path = folder_paths.get_full_path("checkpoints", base_model)
        if not base_model_path: raise FileNotFoundError(f"Base model file not found: {base_model}")
        model = comfy.sd.load_diffusion_model(base_model_path, model_options=unet_options)

        # 2. Load VAE
        vae_path = folder_paths.get_full_path("vae", vae_model)
        if not vae_path: raise FileNotFoundError(f"VAE file not found: {vae_model}")
        sd = comfy.utils.load_torch_file(vae_path)
        vae = comfy.sd.VAE(sd=sd)

        # 3. Load CLIP(s) using the correct type and device logic
        clip_paths = []
        for clip_name in [clip_model_1, clip_model_2, clip_model_3]:
            if clip_name and clip_name != "None":
                path = folder_paths.get_full_path("text_encoders", clip_name)
                if not path: raise FileNotFoundError(f"CLIP file not found: {clip_name}")
                clip_paths.append(path)
        
        if not clip_paths: raise ValueError("At least one CLIP model must be selected.")

        clip_options = {}
        if device == "cpu":
            clip_options["load_device"] = clip_options["offload_device"] = torch.device("cpu")

        clip_target_type = getattr(comfy.sd.CLIPType, clip_type.upper(), comfy.sd.CLIPType.STABLE_DIFFUSION)
        
        clip = comfy.sd.load_clip(
            ckpt_paths=clip_paths,
            embedding_directory=folder_paths.get_folder_paths("embeddings"),
            clip_type=clip_target_type,
            model_options=clip_options
        )

        return (model, clip, vae)
