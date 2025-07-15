import os
import sys
import time
import folder_paths
from random import uniform, sample
from .lora_info import get_lora_info

sys.path.append(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))

class RandomLoRACustom:
    @classmethod
    def INPUT_TYPES(cls):
        loras = ["None"] + folder_paths.get_filename_list("loras")
        inputs = {
            "required": {
                "refresh_loras": ("BOOLEAN", {"default": False}),
                "exclusive_mode": (["Off", "On"],),
                "stride": ("INT", {"default": 1, "min": 1, "max": 1000}),
                "force_randomize_after_stride": (["Off", "On"],),
            },
            "optional": {
                "lora_stack": ("LORA_STACK",),
                "extra_trigger_words": ("STRING", {"forceInput": True}),
            }
        }

        for i in range(1, 11):
            inputs["required"][f"lora_name_{i}"] = (loras,)
            inputs["required"][f"min_strength_{i}"] = (
                "FLOAT", {"default": 0.6, "min": 0.0, "max": 10.0, "step": 0.01})
            inputs["required"][f"max_strength_{i}"] = (
                "FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01})

        return inputs

    RETURN_TYPES = ("LORA_STACK", "STRING", "STRING")
    RETURN_NAMES = ("lora_stack", "trigger_words", "help_text")
    FUNCTION = "random_lora_stacker"
    CATEGORY = "SantoDan/LoRA"

    # Remove this line to stop constant refreshing
    # always_dirty = True

    # Store last refresh state
    _last_refresh_state = {}

    @classmethod
    def IS_CHANGED(cls, refresh_loras=False, **kwargs):
        # Create a unique key for this node instance
        node_key = str(kwargs)
        
        # Only refresh if refresh_loras is True OR if this is the first time
        if refresh_loras or node_key not in cls._last_refresh_state:
            import uuid
            new_id = str(uuid.uuid4())
            cls._last_refresh_state[node_key] = new_id
            return new_id
        
        # Return the cached ID if no refresh is needed
        return cls._last_refresh_state[node_key]

    def random_lora_stacker(
        self,
        exclusive_mode,
        stride,
        force_randomize_after_stride,
        refresh_loras=False,
        lora_stack=None,
        extra_trigger_words="",
        **kwargs
    ):
        import random as py_random
        
        # Use a more deterministic seed approach
        if refresh_loras:
            py_random.seed(time.time_ns())
        else:
            # Use a seed based on parameters for consistency
            seed_string = f"{exclusive_mode}_{stride}_{force_randomize_after_stride}"
            py_random.seed(hash(seed_string) % (2**32))

        lora_names = [kwargs.get(f"lora_name_{i}") for i in range(1, 11)]
        min_strengths = [kwargs.get(f"min_strength_{i}") for i in range(1, 11)]
        max_strengths = [kwargs.get(f"max_strength_{i}") for i in range(1, 11)]

        active_loras = [name for name in lora_names if name and name != "None"]

        if not active_loras:
            return ([], "", "No active LoRAs found.")

        if exclusive_mode == "On":
            used_loras = {py_random.choice(active_loras)}
        else:
            n = py_random.choice(range(1, len(active_loras) + 1))
            used_loras = set(py_random.sample(active_loras, n))

        output_loras = []
        trigger_words_list = []

        for i, name in enumerate(lora_names):
            if name in used_loras:
                min_s = min_strengths[i]
                max_s = max_strengths[i]
                strength = round(py_random.uniform(min_s, max_s), 3)
                output_loras.append((name, strength, strength))
                _, trainedWords, _, _ = get_lora_info(name)
                if trainedWords:
                    trigger_words_list.append(trainedWords)

        # Merge with incoming lora_stack, if provided
        if lora_stack:
            output_loras = list(lora_stack) + output_loras

        # Combine trigger words from generated and input
        all_trigger_words = list(filter(None, trigger_words_list))
        if extra_trigger_words:
            all_trigger_words.append(extra_trigger_words)

        trigger_words_string = ", ".join(all_trigger_words)

        help_text = (
            "refresh_loras:\n"
            " - True: Forces new randomization with time-based seed.\n"
            " - False: Uses consistent seed based on parameters.\n\n"
            "exclusive_mode:\n"
            " - On: Selects only one random LoRA from the active list.\n"
            " - Off: Selects a random number of LoRAs (between 1 and total active LoRAs).\n\n"
            "stride:\n"
            " - Currently ignored.\n\n"
            "force_randomize_after_stride:\n"
            " - Currently ignored.\n"
        )

        return (output_loras, trigger_words_string, help_text)
        
class RandomLoRAFolder:
    # Class-level cache for LoRA info to avoid regenerating files
    _lora_info_cache = {}
    
    @classmethod
    def INPUT_TYPES(cls):
        folders = ["None"] + cls.get_lora_subfolders()

        inputs = {
            "required": {
                "exclusive_mode": (["Off", "On"],),
                "force_refresh_cache": ("BOOLEAN", {"default": False}),  # Only for cache refresh
            },
            "optional": {
                "lora_stack": ("LORA_STACK",),
                "extra_trigger_words": ("STRING", {"forceInput": True}),
            }
        }

        for i in range(1, 11):
            inputs["optional"][f"folder_path_{i}"] = (folders,)
            inputs["optional"][f"lora_count_{i}"] = (
                "INT", {"default": 1, "min": 1, "max": 10, "step": 1, "display": "number"})
            inputs["optional"][f"min_strength_{i}"] = (
                "FLOAT", {"default": 0.6, "min": 0.0, "max": 10.0, "step": 0.01, "display": "number"})
            inputs["optional"][f"max_strength_{i}"] = (
                "FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01, "display": "number"})

        return inputs

    RETURN_TYPES = ("LORA_STACK", "STRING", "STRING")
    RETURN_NAMES = ("lora_stack", "trigger_words", "help_text")
    FUNCTION = "random_lora_stacker"
    CATEGORY = "SantoDan/LoRA"

    @classmethod
    def IS_CHANGED(cls, force_refresh_cache=False, **kwargs):
        # Always randomize selection, but handle cache refresh separately
        if force_refresh_cache:
            # Clear the cache when forced refresh is requested
            cls._lora_info_cache.clear()
        
        # Always return a new UUID for randomization, but cache will handle efficiency
        import uuid
        return str(uuid.uuid4())

    @classmethod
    def get_lora_subfolders(cls):
        import os
        
        # Get the first LoRA path from ComfyUI's configuration
        lora_base_path = folder_paths.get_folder_paths("loras")[0]
        
        subfolders = set()
        for root, dirs, files in os.walk(lora_base_path):
            for d in dirs:
                full_path = os.path.join(root, d)
                rel_path = os.path.relpath(full_path, lora_base_path)
                subfolders.add(rel_path.replace("\\", "/"))
        
        return sorted(subfolders)

    @classmethod
    def get_cached_lora_info(cls, lora_path):
        """Get LoRA info with caching to avoid regenerating files"""
        if lora_path not in cls._lora_info_cache:
            try:
                cls._lora_info_cache[lora_path] = get_lora_info(lora_path)
            except Exception as e:
                print(f"Error getting LoRA info for {lora_path}: {e}")
                cls._lora_info_cache[lora_path] = (None, None, None, None)
        
        return cls._lora_info_cache[lora_path]

    def pick_random_loras_from_folder(self, relative_folder, count=1):
        import random
        lora_base_path = folder_paths.get_folder_paths("loras")[0]
        folder = os.path.join(lora_base_path, relative_folder)

        if not os.path.isdir(folder):
            return []

        files = [f for f in os.listdir(folder) if f.endswith((".safetensors", ".pt"))]
        if not files:
            return []

        actual_count = min(count, len(files))
        selected_files = random.sample(files, actual_count)
        
        result = []
        for f in selected_files:
            filename_only = f
            full_relative_path = os.path.join(relative_folder, f).replace("\\", "/")
            result.append((filename_only, full_relative_path))
        
        return result

    def random_lora_stacker(
        self,
        exclusive_mode,
        force_refresh_cache=False,
        lora_stack=None,
        extra_trigger_words="",
        **kwargs
    ):
        import time, random as py_random
        
        # Always use time-based seed for true randomization
        py_random.seed(time.time_ns())

        # Process all folder inputs
        valid_entries = []
        for i in range(1, 11):
            folder = kwargs.get(f"folder_path_{i}")
            if folder and folder != "None":
                count = kwargs.get(f"lora_count_{i}", 1)
                min_strength = kwargs.get(f"min_strength_{i}", 0.6)
                max_strength = kwargs.get(f"max_strength_{i}", 1.0)
                
                picked_loras = self.pick_random_loras_from_folder(folder.strip(), count)
                for filename_only, full_path in picked_loras:
                    valid_entries.append((filename_only, full_path, min_strength, max_strength))

        if not valid_entries:
            return ([], "", "No valid folders or LoRA files found.")

        if exclusive_mode == "On":
            selected_entries = [py_random.choice(valid_entries)]
        else:
            selected_entries = valid_entries

        output_loras = []
        trigger_words_list = []

        for filename_only, full_path, min_s, max_s in selected_entries:
            strength = round(py_random.uniform(min_s, max_s), 3)
            output_loras.append((full_path, strength, strength))

            # Use cached LoRA info to avoid regenerating files
            _, trained_words, _, _ = self.get_cached_lora_info(full_path)
            if trained_words:
                trigger_words_list.append(trained_words)

        if lora_stack:
            output_loras = list(lora_stack) + output_loras

        all_trigger_words = list(filter(None, trigger_words_list))
        if extra_trigger_words:
            all_trigger_words.append(extra_trigger_words)

        trigger_words_string = ", ".join(all_trigger_words)

        cache_size = len(self._lora_info_cache)
        help_text = (
            "Usage:\n"
            " - Connect inputs to see available folder options.\n"
            " - Only folders with valid paths (not 'None') will be processed.\n"
            " - LoRA selection randomizes every execution.\n\n"
            "force_refresh_cache:\n"
            " - True: Clears LoRA info cache and regenerates files.\n"
            " - False: Uses cached LoRA info for better performance.\n\n"
            f"Current cache size: {cache_size} LoRAs\n\n"
            "folder_path_x:\n"
            " - Path to a subfolder inside your LoRA directory.\n\n"
            "lora_count_x:\n"
            " - Number of LoRAs to randomly select from each folder (1-10).\n\n"
            "exclusive_mode:\n"
            " - On: Selects only one LoRA randomly from all collected LoRAs.\n"
            " - Off: Uses all LoRAs from all specified folders.\n"
        )

        return (output_loras, trigger_words_string, help_text)
