import os
import sys
import requests  # You'll need requests for HTTP calls
import comfy.sd
import comfy.utils
import folder_paths
import hashlib
import json
from random import random, uniform, choice, sample
from ..categories import icons
sys.path.append(os.path.dirname(__file__))
from lora_info import get_lora_info

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))

class CR_RandomLoRACustom:
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
            }
        }
        for i in range(1, 11):
            inputs["required"][f"lora_name_{i}"] = (loras,)
            inputs["required"][f"min_strength_{i}"] = ("FLOAT", {"default": 0.6, "min": 0.0, "max": 10.0, "step": 0.01})
            inputs["required"][f"max_strength_{i}"] = ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01})
        return inputs

    RETURN_TYPES = ("LORA_STACK", "STRING", "STRING")
    RETURN_NAMES = ("lora_stack", "trigger_words", "help_text")
    FUNCTION = "random_lora_stacker"
    CATEGORY = icons.get("Comfyroll/LoRA")

    always_dirty = True  # always run the node
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import uuid
        return str(uuid.uuid4())

    def random_lora_stacker(self, exclusive_mode, stride, force_randomize_after_stride, refresh_loras=False, lora_stack=None, **kwargs):
        import random as py_random
        import time
        py_random.seed(time.time_ns())  # reseed for max randomness

        lora_names = [kwargs.get(f"lora_name_{i}") for i in range(1, 11)]
        min_strengths = [kwargs.get(f"min_strength_{i}") for i in range(1, 11)]
        max_strengths = [kwargs.get(f"max_strength_{i}") for i in range(1, 11)]

        active_loras = [name for name in lora_names if name and name != "None"]
        print(f"Active LoRAs: {active_loras}")

        if not active_loras:
            return ([], "", "")

        if exclusive_mode == "On":
            used_loras = {py_random.choice(active_loras)}
        else:
            n = py_random.choice(range(1, len(active_loras) + 1))
            used_loras = set(py_random.sample(active_loras, n))

        print(f"Used LoRAs: {used_loras}")

        # Reset output stack each time to avoid duplicates
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

        trigger_words_string = ", ".join(trigger_words_list)

        help_text = (
            "exclusive_mode:\n"
            " - On: Selects only one random LoRA from the active list.\n"
            " - Off: Selects a random number of LoRAs (between 1 and total active LoRAs).\n\n"
            "stride:\n"
            " - Ignored in this version; randomization happens every call.\n\n"
            "force_randomize_after_stride:\n"
            " - Ignored in this version.\n"
        )

        return (output_loras, trigger_words_string, help_text)
