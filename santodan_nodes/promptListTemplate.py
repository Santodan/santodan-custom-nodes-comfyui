import os
import json
import folder_paths
import server
from aiohttp import web

class PromptListWithTemplates:
    # ... (the entire class definition remains exactly the same as before) ...
    """
    A ComfyUI node to create a list of prompts, with the ability to save, 
    load, and delete the list as a template via an associated JavaScript file.
    """
    
    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "prompt_list_templates")

    def __init__(self):
        os.makedirs(self.TEMPLATE_DIR, exist_ok=True)

    @classmethod
    def get_template_files(cls):
        if not os.path.exists(cls.TEMPLATE_DIR):
            return []
        template_files = []
        for root, _, files in os.walk(cls.TEMPLATE_DIR):
            for file in files:
                if file.endswith(".json"):
                    relative_path = os.path.relpath(os.path.join(root, file), cls.TEMPLATE_DIR)
                    template_files.append(relative_path)
        return sorted(template_files)

    @classmethod
    def INPUT_TYPES(cls):
        os.makedirs(cls.TEMPLATE_DIR, exist_ok=True)
        return {
            "required": {
                "prompt_1": ("STRING", {"multiline": True, "default": ""}),
                "prompt_2": ("STRING", {"multiline": True, "default": ""}),
                "prompt_3": ("STRING", {"multiline": True, "default": ""}),
                "prompt_4": ("STRING", {"multiline": True, "default": ""}),
                "prompt_5": ("STRING", {"multiline": True, "default": ""}),
                "template_file": (["None"] + cls.get_template_files(),),
                "save_filename": ("STRING", {"default": "", "placeholder": "subfolder/template_name.json"}),
            },
            "optional": { "optional_prompt_list": ("LIST",) }
        }

    RETURN_TYPES = ("LIST", "STRING")
    RETURN_NAMES = ("prompt_list", "prompt_strings")
    OUTPUT_IS_LIST = (False, True)
    FUNCTION = "run"
    CATEGORY = "Santodan/Prompt"

    def run(self, prompt_1, prompt_2, prompt_3, prompt_4, prompt_5, template_file, save_filename, optional_prompt_list=None):
        prompts = []
        if optional_prompt_list:
            prompts.extend(optional_prompt_list)
        
        source_prompts = [prompt_1, prompt_2, prompt_3, prompt_4, prompt_5]
        for p in source_prompts:
            if isinstance(p, str) and p.strip() != '':
                prompts.append(p)
                
        return (prompts, prompts)


# --- API Endpoints for JavaScript interaction ---
def get_template_dir():
    return os.path.join(os.path.dirname(__file__), "prompt_list_templates")

# This function wraps all the route definitions
def initialize_prompt_list_routes():
    # DIAGNOSTIC PRINT STATEMENT
    #print("✅ [Santodan Nodes] EXECUTING: initialize_prompt_list_routes()")

    @server.PromptServer.instance.routes.post("/easyuse/save_prompt_list")
    async def save_prompt_list_template(request):
        try:
            data = await request.json()
            filename = data.get("filename")
            prompts = data.get("prompts")
            if not filename or not prompts: return web.Response(status=400, text="...")
            if not filename.endswith(".json"): filename += ".json"
            file_path = os.path.join(get_template_dir(), filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f: json.dump(prompts, f, indent=4)
            return web.json_response({"status": "success", "message": f"Saved to {filename}"})
        except Exception as e: return web.Response(status=500, text=str(e))

    @server.PromptServer.instance.routes.post("/easyuse/delete_prompt_list")
    async def delete_prompt_list_template(request):
        try:
            data = await request.json()
            filename = data.get("filename")
            if not filename or filename == "None": return web.Response(status=400, text="...")
            file_path = os.path.join(get_template_dir(), filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                return web.json_response({"status": "success", "message": f"Deleted {filename}"})
            else: return web.Response(status=404, text="Template not found.")
        except Exception as e: return web.Response(status=500, text=str(e))

    @server.PromptServer.instance.routes.get("/easyuse/view_prompt_list")
    async def view_prompt_list_template(request):
        filename = request.query.get("filename")
        if not filename or filename == "None": return web.Response(status=400, text="...")
        file_path = os.path.join(get_template_dir(), filename)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f: data = json.load(f)
            return web.json_response(data)
        else: return web.Response(status=404, text="Template not found.")

    @server.PromptServer.instance.routes.get("/easyuse/get_prompt_lists")
    async def get_prompt_list_templates(request):
        files = PromptListWithTemplates.get_template_files()
        return web.json_response(["None"] + files)
