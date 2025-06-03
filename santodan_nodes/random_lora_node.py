import os
import sys
import time
import folder_paths
from random import uniform, sample, choice
from .lora_info import get_lora_info

# If you’re using icons from your own categories.py
# from .categories import icons

# Optional: Use icons if you define them
# CATEGORY = icons.get("SantoDan/LoRA")

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
    CATEGORY = "SantoDan/LoRA"
    always_dirty = True  # Ensures re-run every time

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import uuid
        return str(uuid.uuid4())

    def random_lora_stacker(self, exclusive_mode, stride, force_randomize_after_stride, refresh_loras=False, lora_stack=None, **kwargs):
        lora_names = [kwargs.get(f"lora_name_{i}") for i in range(1, 11)]
        min_strengths = [kwargs.get(f"min_strength_{i}") for i in range(1, 11)]
        max_strengths = [kwargs.get(f"max_strength_{i}") for i in range(1, 11)]

        active_loras = [name for name in lora_names if name and name != "None"]
        print(f"Active LoRAs: {active_loras}")

        if not active_loras:
            return ([], "", "")

        if exclusive_mode == "On":
            used_loras = {choice(active_loras)}
        else:
            n = choice(range(1, len(active_loras) + 1))
            used_loras = set(sample(active_loras, n))

        print(f"Used LoRAs: {used_loras}")

        output_loras = []
        trigger_words_list = []

        for i, name in enumerate(lora_names):
            if name in used_loras:
                min_s = min_strengths[i]
                max_s = max_strengths[i]
                strength = round(uniform(min_s, max_s), 3)
                output_loras.append((name, strength, strength))

                try:
                    _, trainedWords, _, _ = get_lora_info(name)
                    if trainedWords:
                        trigger_words_list.append(trainedWords)
                except Exception as e:
                    print(f"[WARN] Could not get trigger words for {name}: {e}")

        trigger_words_string = ", ".join(trigger_words_list)

        help_text = (
            "exclusive_mode:\n"
            " - On: Selects only one random LoRA from the active list.\n"
            " - Off: Selects a random number of LoRAs (between 1 and total active LoRAs).\n\n"
            "stride:\n"
            " - (Not implemented yet)\n\n"
            "force_randomize_after_stride:\n"
            " - (Not implemented yet)\n"
        )

        # Optional: Append previous stack if chaining
        if lora_stack:
            output_loras = lora_stack + output_loras

        return (output_loras, trigger_words_string, help_text)
