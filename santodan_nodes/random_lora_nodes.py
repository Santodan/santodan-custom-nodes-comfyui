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
                "lora_count": ("INT", {"default": 0, "min": 0, "max": 10}),
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
        lora_count,
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
            seed_string = f"{exclusive_mode}_{stride}_{lora_count}"
            py_random.seed(hash(seed_string) % (2**32))

        lora_names = [kwargs.get(f"lora_name_{i}") for i in range(1, 11)]
        min_strengths = [kwargs.get(f"min_strength_{i}") for i in range(1, 11)]
        max_strengths = [kwargs.get(f"max_strength_{i}") for i in range(1, 11)]

        active_loras = [name for name in lora_names if name and name != "None"]

        if not active_loras:
            return ([], "", "No active LoRAs found.")

        # Determine how many LoRAs to use
        if exclusive_mode == "On":
            used_loras = {py_random.choice(active_loras)}
        else:
            if lora_count == 0:
                # Random number of LoRAs (original behavior)
                n = py_random.choice(range(1, len(active_loras) + 1))
            else:
                # User-specified number of LoRAs
                n = min(lora_count, len(active_loras))
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
            " - Off: Uses lora_count to determine how many LoRAs to select.\n\n"
            "stride:\n"
            " - Currently ignored.\n\n"
            "lora_count:\n"
            " - 0: Selects a random number of LoRAs (between 1 and total active LoRAs).\n"
            " - >0: Selects exactly this number of LoRAs (or all available if less than count).\n"
            " - Note: Ignored when exclusive_mode is On.\n"
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


class LoRACachePreloader:
    """
    A simple node that pre-loads LoRA information for all LoRAs in all folders
    to populate the cache used by RandomLoRAFolder for faster performance.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        folders = ["All folders"] + RandomLoRAFolder.get_lora_subfolders()
        
        return {
            "required": {
                "preload_cache": ("BOOLEAN", {"default": False}),
                "folder_path": (folders, {"default": "All folders"}),
            }
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("status", "cached_count")
    FUNCTION = "preload_lora_cache"
    CATEGORY = "SantoDan/LoRA"

    @classmethod
    def IS_CHANGED(cls, preload_cache=False, **kwargs):
        # Only trigger when the user sets preload_cache to True
        if preload_cache:
            import uuid
            return str(uuid.uuid4())
        return False

    def get_all_lora_files(self, folder_path="All folders"):
        """Get all LoRA files from all folders or a specific folder"""
        import os
        
        lora_base_path = folder_paths.get_folder_paths("loras")[0]
        lora_files = []
        
        if folder_path == "All folders":
            # Walk through all folders and subfolders
            for root, dirs, files in os.walk(lora_base_path):
                for file in files:
                    if file.endswith((".safetensors", ".pt")):
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path, lora_base_path)
                        lora_files.append(relative_path.replace("\\", "/"))
        else:
            # Process only the specific folder
            target_folder = os.path.join(lora_base_path, folder_path)
            if os.path.isdir(target_folder):
                for root, dirs, files in os.walk(target_folder):
                    for file in files:
                        if file.endswith((".safetensors", ".pt")):
                            full_path = os.path.join(root, file)
                            relative_path = os.path.relpath(full_path, lora_base_path)
                            lora_files.append(relative_path.replace("\\", "/"))
        
        return lora_files

    def preload_lora_cache(self, preload_cache=False, folder_path="All folders"):
        if not preload_cache:
            current_cache_size = len(RandomLoRAFolder._lora_info_cache)
            return (
                f"Ready to preload. Current cache: {current_cache_size} LoRAs",
                current_cache_size
            )
        
        import time
        start_time = time.time()
        
        # Get all LoRA files
        lora_files = self.get_all_lora_files(folder_path)
        
        if not lora_files:
            return (f"No LoRA files found in {folder_path}", 0)
        
        total_files = len(lora_files)
        processed_count = 0
        error_count = 0
        
        print(f"Starting preload of {total_files} LoRA files from {folder_path}...")
        
        for i, lora_path in enumerate(lora_files):
            try:
                # Use the same caching method as RandomLoRAFolder
                RandomLoRAFolder.get_cached_lora_info(lora_path)
                processed_count += 1
                
                # Log progress every 50 files
                if (i + 1) % 50 == 0:
                    print(f"Processed {i + 1}/{total_files} files...")
                    
            except Exception as e:
                error_count += 1
                print(f"Error processing {lora_path}: {e}")
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        final_cache_size = len(RandomLoRAFolder._lora_info_cache)
        
        status = f"Preloaded {processed_count}/{total_files} LoRAs from {folder_path} in {elapsed_time:.1f}s (errors: {error_count})"
        
        return (status, final_cache_size)
