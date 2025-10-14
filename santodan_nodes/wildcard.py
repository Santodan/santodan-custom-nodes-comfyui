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
        # Path is now defined in the class method for consistency
        pass

    @classmethod
    def get_wildcard_files(cls):
        """Gets a list of wildcard files from the wildcards folder and its subfolders."""
        wildcards_path = os.path.join(folder_paths.base_path, "wildcards")
        if not os.path.exists(wildcards_path):
            return ["[Create New]"]
        
        file_list = []
        try:
            for root, _, files in os.walk(wildcards_path):
                for file in files:
                    if file.endswith('.txt'):
                        # Get the relative path from the wildcards_path
                        relative_path = os.path.relpath(os.path.join(root, file), wildcards_path)
                        # Remove the .txt extension and normalize path separators for display
                        wildcard_name = os.path.splitext(relative_path)[0].replace('\\', '/')
                        file_list.append(wildcard_name)
            return ["[Create New]"] + sorted(file_list, key=str.lower)
        except Exception as e:
            print(f"WildcardManager Error: Could not read wildcards folder. {e}")
            return ["[Create New]", "(Error reading folder)"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "wildcards_list": (cls.get_wildcard_files(),),
                "text": ("STRING", {"multiline": True, "default": "A {1$$cute|big|small} {3::cat|dog} is sitting on the __object__."}),
                "processing_mode": (["entire text as one","line by line"],),
                "processed_text_preview": ("STRING", {"multiline": True, "default": "", "output": True}), # Mark as output
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
        }

    # --- MODIFIED FOR NEW OUTPUT ---
    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("processed_text", "all_wildcards",)
    # The first output is a list of prompts, the second is a single string containing all wildcard names
    OUTPUT_IS_LIST = (True, False,) 
    # -----------------------------

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
    - Dynamic Prompts: Randomly select one item from a list.
        Example: {blue|red|green} will randomly become blue, red, or green.
    - Wildcards: Randomly select a line from a .txt file in your ComfyUI/wildcards directory.
        Example: __person__ or __subfolder/person__ will pull a random line from person.txt.
    - Nesting: Combine syntaxes for complex results.
        Example: {a|{b|__c__}}
    - Weighted Choices: Give certain options a higher chance of being selected.
        Example: {5::red|2::green|blue} (red is most likely, blue is least).
    - Multi-Select: Select multiple items from a list, with a custom separator.
        Example: {1-2$$ and $$cat|dog|bird} could become cat, dog, bird, cat and dog, cat and bird, or dog and bird.
    - Quantifiers: Repeat a wildcard multiple times to create a list for multi-selection.
        Example: {2$$, $$3#__colors__} expands to select 2 items from __colors__|__colors__|__colors__.
    - Comments: Lines starting with # are ignored, both in the node's text field and within wildcard files.
"""

    def _get_wildcard_options(self, wildcard_name):
        """Loads and caches options from a wildcard file, supporting subdirectories."""
        wildcards_path = os.path.join(folder_paths.base_path, "wildcards")
        # os.path.join handles both Windows and Linux separators correctly
        wildcard_file_path = os.path.join(wildcards_path, f"{wildcard_name}.txt")
        if os.path.exists(wildcard_file_path):
            with open(wildcard_file_path, 'r', encoding='utf-8') as f:
                return [line for line in (l.strip() for l in f) if line and not line.startswith('#')]
        return []

    def _process_syntax(self, text, rng):
        """Recursively processes the full syntax."""
        quantifier_pattern = re.compile(r'(\d+)#(__[\w\./\-\\]+__)')
        inner_prompt_pattern = re.compile(r'\{([^{}]*)\}')
        wildcard_pattern = re.compile(r'__([\w\./\-\\]+)__')

        def expand_quantifier(match):
            count = int(match.group(1))
            wildcard = match.group(2)
            return '|'.join([wildcard] * count)
        text, count = quantifier_pattern.subn(expand_quantifier, text)
        while count > 0:
            text, count = quantifier_pattern.subn(expand_quantifier, text)

        while '{' in text and '}' in text:
            match = inner_prompt_pattern.search(text)
            if not match: break
            content, replacement = match.group(1), ""
            if '$$' in content:
                parts = content.split('$$')
                range_str, options_str = parts[0], parts[1]
                separator = ", "
                if len(parts) > 2: separator, options_str = parts[1], parts[2]
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
                num_to_select = min(rng.randint(min_count, max_count), len(options))
                selected = rng.sample(options, num_to_select)
                replacement = separator.join(selected)
            else:
                options = content.split('|')
                weights, choices = [], []
                for option in options:
                    if '::' in option:
                        try:
                            weight_str, choice = option.split('::', 1)
                            weights.append(float(weight_str)); choices.append(choice)
                        except ValueError:
                            weights.append(1.0); choices.append(option)
                    else:
                        weights.append(1.0); choices.append(option)
                processed_choices = [self._process_syntax(c, rng) for c in choices]
                replacement = rng.choices(processed_choices, weights=weights, k=1)[0]
            text = text[:match.start()] + replacement + text[match.end():]

        while '__' in text:
            match = wildcard_pattern.search(text)
            if not match: break
            wildcard_name = match.group(1)
            options = self._get_wildcard_options(wildcard_name)
            if options:
                choice = self._process_syntax(rng.choice(options), rng)
                text = text[:match.start()] + choice + text[match.end():]
            else:
                print(f"Warning: Wildcard '{wildcard_name}' not found or is empty."); text = text[:match.start()] + text[match.end():].lstrip()
        return text

    # --- CORRECTED FUNCTION SIGNATURE ---
    # The order of parameters now exactly matches the order in INPUT_TYPES.
    def process_text(self, wildcards_list, text, processing_mode, processed_text_preview, seed):
        if isinstance(text, list): text = "\n".join(text)
        rng = random.Random(seed); processed_texts = []
        if processing_mode == "entire text as one":
            lines = text.split('\n')
            non_comment_lines = [l for l in lines if not l.strip().startswith('#')]
            cleaned_text_block = "\n".join(non_comment_lines).strip()
            if cleaned_text_block:
                processed_texts.append(self._process_syntax(cleaned_text_block, rng))
        else:
            for line in text.split('\n'):
                stripped_line = line.strip()
                if not stripped_line or stripped_line.startswith('#'): continue
                processed_texts.append(self._process_syntax(stripped_line, rng))
        if not processed_texts: processed_texts.append("")
        
        # --- NEW CODE TO GET WILDCARD LIST FOR OUTPUT ---
        all_wc_files = self.get_wildcard_files()
        # Filter out the non-file entries used by the dropdown
        actual_wc_files = [w for w in all_wc_files if w not in ["[Create New]", "(Error reading folder)"]]
        # Format as a single newline-separated string for the output
        all_wildcards_output_str = "\n".join([f"__{w}__" for w in actual_wc_files])
        # ----------------------------------------------
        
        # --- MODIFIED RETURN FOR PREVIEW AND NEW OUTPUT ---
        return {
            "ui": {
                "preview_list": processed_texts,
                "processed_text_preview": ["\n".join(processed_texts)]
            }, 
            "result": (processed_texts, all_wildcards_output_str,)
        }
