import os
import random
import re
import folder_paths

class WildcardManager:
    """
    A node to manage and process text with wildcards and dynamic prompts.
    Supports ImpactWildcardProcessor syntax including nesting, weights, multi-select,
    quantifiers, and comments.
    """
    def __init__(self):
        self.wildcards_path = os.path.join(folder_paths.base_path, "wildcards")
        self.wildcard_files = self.get_wildcard_files()
        # Pre-compile regex for efficiency
        self.quantifier_pattern = re.compile(r'(\d+)#(__[\w\./\-\\]+__)') # Updated to support paths in wildcards
        self.inner_prompt_pattern = re.compile(r'\{([^{}]*)\}')
        self.wildcard_pattern = re.compile(r'__([\w\./\-\\]+)__') # Updated to support paths in wildcards

    def get_wildcard_files(self):
        if not os.path.exists(self.wildcards_path):
            return []
        # This function can be improved to handle subdirectories if needed,
        # but for now, it lists top-level files for the dropdown.
        return sorted([f[:-4] for f in os.listdir(self.wildcards_path) if f.endswith('.txt')])

    @classmethod
    def INPUT_TYPES(cls):
        instance = cls()
        wildcard_files_list = instance.get_wildcard_files()
        
        return {
            "required": {
                "wildcards_list": (wildcard_files_list,),
                "text": ("STRING", {"multiline": True, "default": "A {1$$cute|big|small} {3::cat|dog} is sitting on the __object__."}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "processing_mode": (["line by line", "entire text as one"],), # <-- NEW WIDGET
                "control_after_generate": (["fixed", "increment", "decrement", "randomize"],),
                "processed_text_preview": ("STRING", {"multiline": True, "default": "", "input": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("processed_text",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "process_text"
    CATEGORY = "santodan"

    def _get_wildcard_options(self, wildcard_name):
        """Loads and caches options from a wildcard file."""
        # This allows for subdirectories like __animals/cats__
        wildcard_file_path = os.path.join(self.wildcards_path, f"{wildcard_name}.txt")
        if os.path.exists(wildcard_file_path):
            with open(wildcard_file_path, 'r', encoding='utf-8') as f:
                return [line for line in (l.strip() for l in f) if line and not line.startswith('#')]
        return []

    def _process_syntax(self, text, rng):
        """Recursively processes the full syntax."""
        # 1. Expand quantifiers like 3#__wildcard__
        def expand_quantifier(match):
            count = int(match.group(1))
            wildcard = match.group(2)
            return '|'.join([wildcard] * count)
        
        text, count = self.quantifier_pattern.subn(expand_quantifier, text)
        while count > 0:
            text, count = self.quantifier_pattern.subn(expand_quantifier, text)

        # 2. Process innermost dynamic prompts {...}
        while '{' in text and '}' in text:
            match = self.inner_prompt_pattern.search(text)
            if not match: break

            content = match.group(1)
            replacement = ""

            if '$$' in content:
                parts = content.split('$$')
                range_str = parts[0]
                
                if len(parts) == 2: separator, options_str = ", ", parts[1]
                else: separator, options_str = parts[1], parts[2]

                options = [self._process_syntax(opt, rng) for opt in options_str.split('|')]
                
                min_count, max_count = 1, 1
                if '-' in range_str:
                    min_str, max_str = range_str.split('-', 1)
                    min_count = int(min_str) if min_str else 1
                    max_count = int(max_str) if max_str else len(options)
                elif range_str:
                    count_val = int(range_str)
                    if count_val < 0: min_count, max_count = 1, abs(count_val)
                    else: min_count = max_count = count_val
                
                num_to_select = rng.randint(min_count, max_count)
                num_to_select = min(num_to_select, len(options))
                
                selected = rng.sample(options, num_to_select)
                replacement = separator.join(selected)

            else:
                options = content.split('|')
                weights, choices = [], []
                for option in options:
                    if '::' in option:
                        try:
                            weight_str, choice = option.split('::', 1)
                            weights.append(float(weight_str))
                            choices.append(choice)
                        except ValueError:
                            weights.append(1.0)
                            choices.append(option)
                    else:
                        weights.append(1.0)
                        choices.append(option)
                
                processed_choices = [self._process_syntax(c, rng) for c in choices]
                replacement = rng.choices(processed_choices, weights=weights, k=1)[0]
            
            text = text[:match.start()] + replacement + text[match.end():]

        # 3. Process wildcards __...__
        while '__' in text:
            match = self.wildcard_pattern.search(text)
            if not match: break
            
            wildcard_name = match.group(1)
            options = self._get_wildcard_options(wildcard_name)
            
            if options:
                choice = self._process_syntax(rng.choice(options), rng)
                text = text[:match.start()] + choice + text[match.end():]
            else:
                print(f"Warning: Wildcard '{wildcard_name}' not found or is empty.")
                text = text[:match.start()] + text[match.end():].lstrip()
        return text

    # --- MODIFIED FUNCTION ---
    def process_text(self, wildcards_list, text, seed, processing_mode, control_after_generate, processed_text_preview=""):
        if isinstance(text, list):
            text = "\n".join(text)

        rng = random.Random(seed)
        processed_texts = []

        if processing_mode == "entire text as one":
            # Filter out comment lines first, then join back together
            lines = text.split('\n')
            non_comment_lines = [l for l in lines if not l.strip().startswith('#')]
            cleaned_text_block = "\n".join(non_comment_lines).strip()
            
            # Process the entire block only if it's not empty after cleaning
            if cleaned_text_block:
                processed_text = self._process_syntax(cleaned_text_block, rng)
                processed_texts.append(processed_text)

        else: # "line by line" mode (original behavior)
            lines = text.split('\n')
            for line in lines:
                stripped_line = line.strip()
                # Ignore comments and empty lines for batch processing
                if not stripped_line or stripped_line.startswith('#'):
                    continue
                processed_line = self._process_syntax(stripped_line, rng)
                processed_texts.append(processed_line)
        
        # Ensure the node never outputs an empty list, which can cause errors downstream
        if not processed_texts:
            processed_texts.append("")

        return {"ui": {"preview_list": processed_texts}, "result": (processed_texts,)}

