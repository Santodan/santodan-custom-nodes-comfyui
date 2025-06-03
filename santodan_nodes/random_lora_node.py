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

    always_dirty = True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import uuid
        return str(uuid.uuid4())

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
        py_random.seed(time.time_ns())

        lora_names = [kwargs.get(f"lora_name_{i}") for i in range(1, 11)]
        min_strengths = [kwargs.get(f"min_strength_{i}") for i in range(1, 11)]
        max_strengths = [kwargs.get(f"max_strength_{i}") for i in range(1, 11)]

        active_loras = [name for name in lora_names if name and name != "None"]
        #print(f"Active LoRAs: {active_loras}")

        if not active_loras:
            return ([], "", "No active LoRAs found.")

        if exclusive_mode == "On":
            used_loras = {py_random.choice(active_loras)}
        else:
            n = py_random.choice(range(1, len(active_loras) + 1))
            used_loras = set(py_random.sample(active_loras, n))

        #print(f"Used LoRAs: {used_loras}")

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
            "exclusive_mode:\n"
            " - On: Selects only one random LoRA from the active list.\n"
            " - Off: Selects a random number of LoRAs (between 1 and total active LoRAs).\n\n"
            "stride:\n"
            " - Currently ignored.\n\n"
            "force_randomize_after_stride:\n"
            " - Currently ignored.\n"
        )

        return (output_loras, trigger_words_string, help_text)

