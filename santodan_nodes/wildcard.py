import os
import random
import re
import folder_paths
import yaml

class WildcardManager:
    global_sync_index = 0

    def __init__(self):
        pass

    @classmethod
    def get_wildcards_path(cls):
        """Centralized path logic using ComfyUI's base path."""
        path = os.path.join(folder_paths.base_path, "wildcards")
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @classmethod
    def get_wildcard_files(cls):
        wildcards_path = cls.get_wildcards_path()
        file_list = []
        try:
            for root, _, files in os.walk(wildcards_path):
                for file in files:
                    if file.lower().endswith(('.txt', '.yaml', '.yml')):
                        rel = os.path.relpath(os.path.join(root, file), wildcards_path)
                        name = rel.replace('\\', '/')
                        if name.lower().endswith('.txt'): name = name[:-4]
                        file_list.append(name)
            return ["[Create New]"] + sorted(file_list, key=str.lower)
        except Exception: return ["[Create New]", "(Error)"]

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

    def _get_wildcard_options(self, wildcard_name):
        import yaml
        wildcards_path = self.get_wildcards_path()
        
        # 1. Check if it's a YAML path (e.g., styles.yaml/lighting)
        if ".yaml" in wildcard_name.lower() or ".yml" in wildcard_name.lower():
            parts = wildcard_name.split('/')
            file_path, yaml_keys = None, []
            for i, part in enumerate(parts):
                if part.lower().endswith(('.yaml', '.yml')):
                    file_path = os.path.join(wildcards_path, *parts[:i+1])
                    yaml_keys = parts[i+1:]
                    break
            
            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                    for key in yaml_keys:
                        data = data.get(key) if isinstance(data, dict) else None
                    if isinstance(data, list): return [str(x) for x in data]
                except Exception: pass
            return []

        # 2. Default logic: It's a .txt file (user just typed __test__)
        # We manually add the .txt here because the UI sends the name without it
        wildcard_file_path = os.path.join(wildcards_path, f"{wildcard_name}.txt")
        if os.path.exists(wildcard_file_path):
            with open(wildcard_file_path, 'r', encoding='utf-8') as f:
                return [line for line in (l.strip() for l in f) if line and not line.startswith('#')]
        return []
    
    def _parse_range(self, range_str, opt_count, rng):
        if not range_str: return 1
        try:
            if '-' in range_str:
                parts = range_str.split('-')
                low = int(parts[0]) if parts[0] else 1
                high = int(parts[1]) if parts[1] else opt_count
                return rng.randint(low, high)
            else: return int(range_str)
        except ValueError: return 1

    def _process_syntax(self, text, seeded_rng):
        quantifier_pattern = re.compile(r'(\d+)#(__[\w\s\./\-\\]+?__)')
        def expand_quantifier(match):
            count, wc = int(match.group(1)), match.group(2)
            return '|'.join([wc] * count)
        while quantifier_pattern.search(text):
            text = quantifier_pattern.sub(expand_quantifier, text)

        dynamic_pattern = re.compile(r'\{([*+]?)([^{}]+)\}')
        while True:
            match = dynamic_pattern.search(text)
            if not match: break
            prefix, content = match.group(1), match.group(2)
            current_rng = random.Random() if prefix == '*' else seeded_rng
            use_sequential = (prefix == '+')
            replacement = ""
            if '$$' in content:
                parts = content.split('$$')
                if len(parts) == 3: range_str, sep, opt_str = parts[0], parts[1], parts[2]
                else: range_str, sep, opt_str = parts[0], ", ", parts[1]
                options = opt_str.split('|')
                if use_sequential:
                    choice_idx = WildcardManager.global_sync_index % len(options)
                    selected = [options[choice_idx]]
                else:
                    num_to_select = self._parse_range(range_str, len(options), current_rng)
                    num_to_select = max(0, min(num_to_select, len(options)))
                    selected = current_rng.sample(options, num_to_select)
                processed = [self._process_syntax(s, seeded_rng) for s in selected]
                replacement = sep.join(processed)
            else:
                options = content.split('|')
                if use_sequential:
                    idx = WildcardManager.global_sync_index % len(options)
                    choice = options[idx]
                else:
                    weights, clean_options = [], []
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

        wildcard_pattern = re.compile(r'__([*+]?)([\w\s\./\-\\]+?)__')
        while True:
            match = wildcard_pattern.search(text)
            if not match: break
            prefix, wc_name = match.group(1), match.group(2)
            options = self._get_wildcard_options(wc_name)
            if options:
                if prefix == '+': choice = options[WildcardManager.global_sync_index % len(options)]
                elif prefix == '*': choice = random.Random().choice(options)
                else: choice = seeded_rng.choice(options)
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
            if clean_text: processed_texts.append(self._process_syntax(clean_text, rng))
        else:
            for line in input_lines:
                if not line.strip() or line.strip().startswith('#'): continue
                processed_texts.append(self._process_syntax(line.strip(), rng))

        WildcardManager.global_sync_index += 1
        if not processed_texts: processed_texts.append("")
        all_wc = self.get_wildcard_files()
        all_wc_str = "\n".join([f"__{w}__" for w in all_wc if w not in ["[Create New]", "(Error reading folder)"]])
        processed_string = "\n".join(processed_texts)
        
        return {
            "ui": {"preview_list": processed_texts, "processed_text_preview": [processed_string]}, 
            "result": (processed_texts, processed_string, all_wc_str,)
        }