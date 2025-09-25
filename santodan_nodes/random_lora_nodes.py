import os
import sys
import time
import folder_paths
import random
from .lora_info import get_lora_info
import re
from PIL import Image, PngImagePlugin
import nodes  # ComfyUI’s built-in
from pathlib import Path

sys.path.append(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))

#import inspect
#from nodes import LoraLoader
#print(inspect.signature(LoraLoader.load_lora))

class ExtractAndApplyLoRAs:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_path": ("STRING", {"default": "./input/example.png"}),
                "model": ("MODEL",),
                "clip": ("CLIP",),  # Needed to apply LoRAs
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP", "STRING")
    RETURN_NAMES = ("MODEL", "CLIP", "LORA_INFO")
    FUNCTION = "apply"
    CATEGORY = "Santodan/LoRA"

    def _normalize_name(self, name: str) -> str:
        # lowercase and replace spaces, dots, dashes with underscores
        return re.sub(r"[ .-]", "_", name.lower())

    def apply(self, image_path, model, clip):
        # Load image metadata
        try:
            with Image.open(image_path) as img:
                metadata = img.info.get("parameters", "")
        except Exception as e:
            return model, clip, f"Error reading metadata: {e}"

        if not metadata:
            return model, clip, "No LoRAs found in metadata"

        # Extract <lora:NAME:STRENGTH>
        lora_matches = re.findall(r"<lora:([^:>]+):([-+]?[0-9]*\.?[0-9]+)>", metadata)
        if not lora_matches:
            return model, clip, "No LoRAs found in metadata"

        # Build lookup of all LoRA files in ComfyUI's loras folder
        loras_root = folder_paths.get_folder_paths("loras")[0]
        available_loras = {}
        for root, _, files in os.walk(loras_root):
            for f in files:
                if f.endswith((".safetensors", ".ckpt", ".pt")):
                    norm = self._normalize_name(os.path.splitext(f)[0])
                    rel_path = os.path.relpath(os.path.join(root, f), loras_root)  # relative path
                    available_loras[norm] = rel_path

        loader = nodes.LoraLoader()
        applied = []

        for name, weight_str in lora_matches:
            try:
                weight = float(weight_str)
            except:
                weight = 1.0

            norm_name = self._normalize_name(name)

            if norm_name in available_loras:
                lora_file = available_loras[norm_name]  # relative path
                try:
                    model, clip = loader.load_lora(model, clip, lora_file, weight, weight)
                    applied.append(f"{name}:{weight} -> {lora_file}")
                except Exception as e:
                    applied.append(f"{name}:{weight} ❌ ({e})")
            else:
                applied.append(f"{name}:{weight} (NOT FOUND)")

        applied_text = ", ".join(applied) if applied else "No LoRAs applied"
        return model, clip, applied_text

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
                "FLOAT", {"default": 0.6, "min": -10.0, "max": 10.0, "step": 0.01})
            inputs["required"][f"max_strength_{i}"] = (
                "FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01})

        return inputs

    RETURN_TYPES = ("LORA_STACK", "STRING", "STRING")
    RETURN_NAMES = ("lora_stack", "trigger_words", "help_text")
    FUNCTION = "random_lora_stacker"
    CATEGORY = "Santodan/LoRA"
    _last_refresh_state = {}

    @classmethod
    def IS_CHANGED(cls, refresh_loras=False, **kwargs):
        node_key = str(kwargs)
        if refresh_loras or node_key not in cls._last_refresh_state:
            import uuid
            new_id = str(uuid.uuid4())
            cls._last_refresh_state[node_key] = new_id
        return cls._last_refresh_state[node_key]

    def random_lora_stacker(
        self, exclusive_mode, stride, lora_count,
        refresh_loras=False, lora_stack=None,
        extra_trigger_words="", **kwargs
    ):
        import random as py_random
        import time

        # Seed handling
        if refresh_loras:
            py_random.seed(time.time_ns())
        else:
            seed_string = f"{exclusive_mode}_{stride}_{lora_count}"
            py_random.seed(hash(seed_string) % (2**32))

        # Collect inputs
        lora_names = [kwargs.get(f"lora_name_{i}") for i in range(1, 11)]
        min_strengths = [kwargs.get(f"min_strength_{i}") for i in range(1, 11)]
        max_strengths = [kwargs.get(f"max_strength_{i}") for i in range(1, 11)]
        active_loras = [name for name in lora_names if name and name != "None"]

        if not active_loras:
            if lora_stack:
                return (list(lora_stack), "", "No active LoRAs found. Passing through input stack.")
            return ([], "", "No active LoRAs found.")

        # Determine which LoRAs to use
        if exclusive_mode == "On":
            used_loras = {py_random.choice(active_loras)}
        else:
            if lora_count == 0:
                n = py_random.choice(range(1, len(active_loras) + 1))
            else:
                n = min(lora_count, len(active_loras))  # Clamp to number of available LoRAs
            used_loras = set(py_random.sample(active_loras, n))

        # Build output list
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

        # Normalize lora_stack to prevent unpacking errors
        if lora_stack:
            normalized_stack = [
                tup[:3] if len(tup) >= 3 else (tup[0], tup[1], tup[1])
                for tup in lora_stack
            ]
            output_loras = normalized_stack + output_loras

        # Prepare trigger words
        all_trigger_words = list(filter(None, trigger_words_list))
        if extra_trigger_words:
            all_trigger_words.append(extra_trigger_words)
        trigger_words_string = ", ".join(all_trigger_words)

        # Help text
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
            " - 0: Random number of LoRAs (1–total).\n"
            " - >0: Exactly this number (or all available if fewer).\n"
        )

        return (output_loras, trigger_words_string, help_text)

class RandomLoRAFolder:
    _lora_info_cache = {}
    _last_refresh_state = {}

    @classmethod
    def INPUT_TYPES(cls):
        folders = ["None"] + cls.get_lora_subfolders()
        inputs = {
            "required": {
                "exclusive_mode": (["Off", "On"],),
                "refresh_loras": ("BOOLEAN", {"default": False}),
                "force_refresh_cache": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "lora_stack": ("LORA_STACK",),
                "extra_trigger_words": ("STRING", {"forceInput": True}),
                "exclude_loras_from_node": ("LORA_LIST",),
            }
        }
        for i in range(1, 11):
            inputs["optional"][f"folder_path_{i}"] = (folders,)
            inputs["optional"][f"lora_count_{i}"] = (
                "INT", {"default": 1, "min": 1, "max": 99, "step": 1})
            inputs["optional"][f"min_strength_{i}"] = (
                "FLOAT", {"default": 0.6, "min": -10.0, "max": 10.0, "step": 0.01})
            inputs["optional"][f"max_strength_{i}"] = (
                "FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01})
        return inputs

    RETURN_TYPES = ("LORA_STACK", "STRING", "STRING")
    RETURN_NAMES = ("lora_stack", "trigger_words", "help_text")
    FUNCTION = "random_lora_stacker"
    CATEGORY = "Santodan/LoRA"

    @classmethod
    def IS_CHANGED(cls, refresh_loras=False, force_refresh_cache=False, **kwargs):
        if force_refresh_cache:
            cls._lora_info_cache.clear()
        node_key = str(kwargs)
        import uuid
        if refresh_loras or node_key not in cls._last_refresh_state:
            new_id = str(uuid.uuid4())
            cls._last_refresh_state[node_key] = new_id
            return new_id
        return cls._last_refresh_state[node_key]

    @classmethod
    def get_lora_subfolders(cls):
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
        if lora_path not in cls._lora_info_cache:
            try:
                cls._lora_info_cache[lora_path] = get_lora_info(lora_path)
            except Exception as e:
                print(f"Error getting LoRA info for {lora_path}: {e}")
                cls._lora_info_cache[lora_path] = (None, None, None, None)
        return cls._lora_info_cache[lora_path]

    def pick_random_loras_from_folder(self, relative_folder, count=1, rng=None, exclude_list=None):
        import os, random
        lora_base_path = folder_paths.get_folder_paths("loras")[0]
        folder = os.path.join(lora_base_path, relative_folder)
        if not os.path.isdir(folder):
            return []

        files = [f for f in os.listdir(folder) if f.endswith((".safetensors", ".pt"))]

        # 🔹 Robust exclusion logic
        if exclude_list:
            exclude_set = {os.path.basename(f).strip() for f in exclude_list if f and f != "None"}
            files = [f for f in files if f.strip() not in exclude_set]

        if not files:
            return []

        actual_count = min(count, len(files))
        rng = rng or random
        selected_files = rng.sample(files, actual_count)
        return [os.path.join(relative_folder, f).replace("\\", "/") for f in selected_files]

    def random_lora_stacker(
        self, exclusive_mode,
        refresh_loras=False,
        force_refresh_cache=False,
        lora_stack=None,
        extra_trigger_words="",
        exclude_loras_from_node=None,
        **kwargs
    ):
        import random as py_random

        # -----------------------
        # Step 1: select LoRAs
        # -----------------------
        if refresh_loras:
            selection_rng = py_random.Random(py_random.randrange(1 << 30))
        else:
            selection_seed_data = []
            for i in range(1, 11):
                selection_seed_data.append((
                    kwargs.get(f"folder_path_{i}"),
                    kwargs.get(f"lora_count_{i}", 1)
                ))
            selection_seed_string = str(exclusive_mode) + str(selection_seed_data)
            selection_rng = py_random.Random(hash(selection_seed_string) % (2**32))

        valid_entries = []
        for i in range(1, 11):
            folder = kwargs.get(f"folder_path_{i}")
            if folder and folder != "None":
                count = kwargs.get(f"lora_count_{i}", 1)
                min_strength = kwargs.get(f"min_strength_{i}", 0.6)
                max_strength = kwargs.get(f"max_strength_{i}", 1.0)

                picked_loras = self.pick_random_loras_from_folder(
                    folder.strip(),
                    count,
                    rng=selection_rng,
                    exclude_list=exclude_loras_from_node
                )

                for full_path in picked_loras:
                    valid_entries.append((full_path, min_strength, max_strength))

        if not valid_entries:
            if lora_stack:
                all_trigger_words = [extra_trigger_words] if extra_trigger_words else []
                return list(lora_stack), ", ".join(all_trigger_words), "No valid folders selected. Passing through existing lora_stack."
            return [], "", "No valid folders or LoRA files found."

        if exclusive_mode == "On":
            selected_entries = [selection_rng.choice(valid_entries)]
        else:
            selected_entries = valid_entries

        # -----------------------
        # Step 2: generate strengths
        # -----------------------
        if refresh_loras:
            strength_rng = py_random.Random(py_random.randrange(1 << 30))
        else:
            strength_seed_string = str(selected_entries)
            strength_rng = py_random.Random(hash(strength_seed_string) % (2**32))

        output_loras = []
        trigger_words_list = []
        for full_path, min_s, max_s in selected_entries:
            strength = round(strength_rng.uniform(min_s, max_s), 3)
            output_loras.append((full_path, strength, strength))
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
            "refresh_loras:\n"
            " - True: Forces new randomization for LoRAs and strengths.\n"
            " - False: Maintains LoRA selection but regenerates strengths if min/max changed.\n\n"
            f"Current cache size: {cache_size} LoRAs\n"
            "exclusive_mode:\n"
            " - On: Selects one random LoRA from all collected.\n"
            " - Off: Uses all LoRAs from specified folders.\n"
        )

        return output_loras, trigger_words_string, help_text

class ExcludedLoras:
    @classmethod
    def INPUT_TYPES(cls):
        loras = ["None"] + folder_paths.get_filename_list("loras")
        inputs = {
            "required": {
                "lora_1": (loras,),
                "lora_2": (loras,),
                "lora_3": (loras,),
                "lora_4": (loras,),
                "lora_5": (loras,),
            },
            "optional": {
                "merge_previous": ("LORA_LIST",)  # accept previous ExcludedLoras output
            }
        }
        return inputs

    RETURN_TYPES = ("LORA_LIST",)
    RETURN_NAMES = ("excluded_loras",)
    FUNCTION = "generate_excluded_loras"
    CATEGORY = "Santodan/LoRA"

    def generate_excluded_loras(self, lora_1, lora_2, lora_3, lora_4, lora_5, merge_previous=None):
        excluded = [lora_1, lora_2, lora_3, lora_4, lora_5]
        excluded = [l for l in excluded if l and l != "None"]

        # Merge previous nodes if provided
        if merge_previous:
            excluded.extend([l for l in merge_previous if l and l != "None"])

        return excluded,

class LoRACachePreloader:
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
    CATEGORY = "Santodan/LoRA"

    @classmethod
    def IS_CHANGED(cls, preload_cache=False, **kwargs):
        if preload_cache:
            import uuid
            return str(uuid.uuid4())
        return False

    def get_all_lora_files(self, folder_path="All folders"):
        lora_base_path = folder_paths.get_folder_paths("loras")[0]
        lora_files = []
        if folder_path == "All folders":
            for root, dirs, files in os.walk(lora_base_path):
                for file in files:
                    if file.endswith((".safetensors", ".pt")):
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path, lora_base_path)
                        lora_files.append(relative_path.replace("\\", "/"))
        else:
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
        lora_files = self.get_all_lora_files(folder_path)
        if not lora_files:
            return (f"No LoRA files found in {folder_path}", 0)

        total_files = len(lora_files)
        processed_count = 0
        error_count = 0
        print(f"Starting preload of {total_files} LoRA files from {folder_path}...")

        for i, lora_path in enumerate(lora_files):
            try:
                RandomLoRAFolder.get_cached_lora_info(lora_path)
                processed_count += 1
                if (i + 1) % 50 == 0:
                    print(f"Processed {i + 1}/{total_files} files...")
            except Exception as e:
                error_count += 1
                print(f"Error processing {lora_path}: {e}")

        elapsed_time = time.time() - start_time
        final_cache_size = len(RandomLoRAFolder._lora_info_cache)
        status = f"Preloaded {processed_count}/{total_files} LoRAs from {folder_path} in {elapsed_time:.1f}s (errors: {error_count})"
        return (status, final_cache_size)
