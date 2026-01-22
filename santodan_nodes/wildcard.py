import os
import random
import re
import folder_paths

class WildcardManager:
    global_sync_index = 0

    def __init__(self):
        pass

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Force re-run to prevent caching of sequential/unseeded random results
        return float("NaN")

    @classmethod
    def get_wildcard_files(cls):
        wildcards_path = os.path.join(folder_paths.base_path, "wildcards")
        if not os.path.exists(wildcards_path):
            return ["[Create New]"]
        file_list = []
        try:
            for root, _, files in os.walk(wildcards_path):
                for file in files:
                    if file.endswith('.txt'):
                        relative_path = os.path.relpath(os.path.join(root, file), wildcards_path)
                        wildcard_name = os.path.splitext(relative_path)[0].replace('\\', '/')
                        file_list.append(wildcard_name)
            return ["[Create New]"] + sorted(file_list, key=str.lower)
        except Exception as e:
            return ["[Create New]", "(Error reading folder)"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "wildcards_list": (cls.get_wildcard_files(),),
                "text": ("STRING", {"multiline": True, "default": "A {*cute|big|small} {+cat|dog} is sitting on the __object__."}),
                "processing_mode": (["entire text as one","line by line"],),
                "processed_text_preview": ("STRING", {"multiline": True, "default": "", "output": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING",)
    RETURN_NAMES = ("processed_text", "processed_string", "all_wildcards",)
    OUTPUT_IS_LIST = (True, False, False,) 
    FUNCTION = "process_text"
    CATEGORY = "Santodan/Wildcard"

    DESCRIPTION = """
# Wildcard Manager Node

This node provides a complete system for managing and using wildcard files directly within your workflow. It allows you to dynamically generate multiple prompts from a single template.

### HOW TO USE:

Tooltips:
    - Insert Selected: Insertes the selected wildcard to the text.
    - Edit/Create Wildcard: Opens the content of the wildcard currently selected in the dropdown in an editor, allowing you to make changes and save/create them.
        - You need to have the [Create New] selected in the wildcards_list dropdown
    - Delete Selected: Asks for confirmation and then permanently deletes the wildcard file selected in the dropdown.

### ADDITIONAL SYNTAX:
    - Randomize (Unseeded): Use '*' to bypass the seed. Changes every generation.
        Example Wildcard: __*person__
        Example Dynamic: {*red|blue|green}
    - Sequential: Use '+' to select items in order across different queue runs.
        Example Wildcard: __+person__
        Example Dynamic: {+red|blue|green}
    - Standard Random (Seeded): Results stay the same if the seed is fixed.
        Example: __person__ or {red|blue|green}
    - Weighted Choices: {5::red|2::green|blue} (Seeded/Unseeded random only).
    - Multi-Select: {1-2$$ and $$cat|dog|bird}.
    - Comments: Lines starting with # are ignored.
"""

    def _get_wildcard_options(self, wildcard_name):
        wildcards_path = os.path.join(folder_paths.base_path, "wildcards")
        wildcard_file_path = os.path.join(wildcards_path, f"{wildcard_name}.txt")
        if os.path.exists(wildcard_file_path):
            with open(wildcard_file_path, 'r', encoding='utf-8') as f:
                return [line for line in (l.strip() for l in f) if line and not line.startswith('#')]
        return []

    def _parse_range(self, range_str, opt_count, rng):
        """Parses '1-2' or '2' into an actual integer."""
        if not range_str:
            return 1
        try:
            if '-' in range_str:
                parts = range_str.split('-')
                low = int(parts[0]) if parts[0] else 1
                high = int(parts[1]) if parts[1] else opt_count
                return rng.randint(low, high)
            else:
                return int(range_str)
        except ValueError:
            return 1

    def _process_syntax(self, text, seeded_rng):
        # 1. Expand Quantifiers first: '3#__test__' -> '__test__|__test__|__test__'
        quantifier_pattern = re.compile(r'(\d+)#(__[\w\s\./\-\\]+?__)')
        def expand_quantifier(match):
            count, wc = int(match.group(1)), match.group(2)
            return '|'.join([wc] * count)
        
        while quantifier_pattern.search(text):
            text = quantifier_pattern.sub(expand_quantifier, text)

        # 2. Handle Dynamic Prompts {prefix}{content}
        # This regex handles the inner-most brackets first
        dynamic_pattern = re.compile(r'\{([*+]?)([^{}]+)\}')
        
        while True:
            match = dynamic_pattern.search(text)
            if not match: break
            
            prefix, content = match.group(1), match.group(2)
            current_rng = random.Random() if prefix == '*' else seeded_rng
            use_sequential = (prefix == '+')
            
            replacement = ""
            if '$$' in content:
                # Multi-select: {range$$sep$$options} or {range$$options}
                parts = content.split('$$')
                if len(parts) == 3:
                    range_str, sep, opt_str = parts[0], parts[1], parts[2]
                else:
                    range_str, sep, opt_str = parts[0], ", ", parts[1]
                
                options = opt_str.split('|')
                
                if use_sequential:
                    # Sequential multi-select: start at global index and take 1
                    choice_idx = WildcardManager.global_sync_index % len(options)
                    selected = [options[choice_idx]]
                else:
                    num_to_select = self._parse_range(range_str, len(options), current_rng)
                    num_to_select = max(0, min(num_to_select, len(options)))
                    selected = current_rng.sample(options, num_to_select)
                
                # Process selected options recursively
                processed = [self._process_syntax(s, seeded_rng) for s in selected]
                replacement = sep.join(processed)
            else:
                # Standard choice: {a|b|c}
                options = content.split('|')
                if use_sequential:
                    idx = WildcardManager.global_sync_index % len(options)
                    choice = options[idx]
                else:
                    # Weights support
                    weights = []
                    clean_options = []
                    for opt in options:
                        if '::' in opt:
                            w_str, c = opt.split('::', 1)
                            weights.append(float(w_str))
                            clean_options.append(c)
                        else:
                            weights.append(1.0)
                            clean_options.append(opt)
                    choice = current_rng.choices(clean_options, weights=weights, k=1)[0]
                
                replacement = self._process_syntax(choice, seeded_rng)
            
            text = text[:match.start()] + replacement + text[match.end():]

        # 3. Handle Wildcards __prefix__name__
        wildcard_pattern = re.compile(r'__([*+]?)([\w\s\./\-\\]+?)__')
        while True:
            match = wildcard_pattern.search(text)
            if not match: break
            
            prefix, wc_name = match.group(1), match.group(2)
            options = self._get_wildcard_options(wc_name)
            
            if options:
                if prefix == '+':
                    choice = options[WildcardManager.global_sync_index % len(options)]
                elif prefix == '*':
                    choice = random.Random().choice(options)
                else:
                    choice = seeded_rng.choice(options)
                
                replacement = self._process_syntax(choice, seeded_rng)
                text = text[:match.start()] + replacement + text[match.end():]
            else:
                text = text[:match.start()] + text[match.end():].lstrip()
        
        return text

    def process_text(self, wildcards_list, text, processing_mode, processed_text_preview, seed):
        if isinstance(text, list): text = "\n".join(text)
        rng = random.Random(seed)
        processed_texts = []
        
        input_lines = text.split('\n')
        if processing_mode == "entire text as one":
            clean_text = "\n".join([l for l in input_lines if not l.strip().startswith('#')]).strip()
            if clean_text:
                processed_texts.append(self._process_syntax(clean_text, rng))
        else:
            for line in input_lines:
                if not line.strip() or line.strip().startswith('#'): continue
                processed_texts.append(self._process_syntax(line.strip(), rng))

        # Update counter for next run
        WildcardManager.global_sync_index += 1

        if not processed_texts: processed_texts.append("")
        all_wc = self.get_wildcard_files()
        all_wc_str = "\n".join([f"__{w}__" for w in all_wc if w not in ["[Create New]", "(Error reading folder)"]])
        processed_string = "\n".join(processed_texts)
        
        return {
            "ui": {
                "preview_list": processed_texts,
                "processed_text_preview": [processed_string]
            }, 
            "result": (processed_texts, processed_string, all_wc_str,)
        }