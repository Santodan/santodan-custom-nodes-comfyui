import os
import server
from aiohttp import web
#from werkzeug.utils import secure_filename
#
import json
from . import utils 

def get_safe_wildcard_path(root, user_filename):
    user_filename = user_filename.replace('\\', '/').lstrip('/')
    
    # If no extension is provided, assume .txt
    if '.' not in os.path.basename(user_filename):
        user_filename += ".txt"
        
    parts = user_filename.split('/')
    safe_parts = [part for part in parts if part and part not in ['.', '..']]
    if not safe_parts: return None

    safe_relative_path = os.path.join(*safe_parts)
    full_path = os.path.abspath(os.path.join(root, safe_relative_path))
    
    abs_root = os.path.abspath(root)
    if os.path.commonpath([abs_root, full_path]) != abs_root: return None
    return full_path

def initialize_routes(wildcards_path):
    #print("[Santodan Nodes] Initializing wildcard API routes...")

    @server.PromptServer.instance.routes.get("/santodan/wildcards")
    async def get_wildcards_endpoint(request):
        if not os.path.exists(wildcards_path): return web.json_response([])
        filenames = []
        for root, _, files in os.walk(wildcards_path):
            for file in files:
                if file.lower().endswith(('.txt', '.yaml', '.yml')):
                    rel = os.path.relpath(os.path.join(root, file), wildcards_path)
                    name = rel.replace('\\', '/')
                    # Hide .txt extension from the list
                    if name.lower().endswith('.txt'):
                        name = name[:-4]
                    filenames.append(name)
        return web.json_response(sorted(filenames))

    @server.PromptServer.instance.routes.get("/santodan/wildcard-content")
    async def get_wildcard_content(request):
        filename = request.query.get('filename')
        if not filename:
            return web.Response(text="Filename parameter is missing", status=400)
        
        file_path = get_safe_wildcard_path(wildcards_path, filename)
        if not file_path:
            return web.Response(text="Invalid filename or directory traversal attempt.", status=403)

        try:
            print(f"[Santodan Wildcard Manager] Attempting to read file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"[Santodan Wildcard Manager] Success! Sending content for '{filename}'.")
            return web.json_response({"content": content})
        except FileNotFoundError:
            print(f"[Santodan Wildcard Manager] File not found. Sending empty content for new file '{filename}'.")
            return web.json_response({"content": ""})
        except Exception as e:
            print(f"[Santodan Wildcard Manager] ERROR reading file {filename}: {e}")
            return web.json_response({"error": f"Failed to read file: {e}"}, status=500)

    @server.PromptServer.instance.routes.post("/santodan/wildcard-save")
    async def save_wildcard_content(request):
        data = await request.json()
        filename = data.get('filename')
        content = data.get('content', '')

        if not filename: return web.Response(text="Filename is missing", status=400)
        
        file_path = get_safe_wildcard_path(wildcards_path, filename)
        if not file_path:
            return web.Response(text="Invalid filename or directory traversal attempt.", status=403)

        try:
            # Create subdirectories if they don't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f: f.write(content)
            return web.json_response({"status": "success", "message": f"Saved {filename}"})
        except Exception as e:
            return web.Response(text=f"Error saving file: {str(e)}", status=500)

    @server.PromptServer.instance.routes.delete("/santodan/wildcard-delete")
    async def delete_wildcard_file(request):
        data = await request.json()
        filename = data.get('filename')
        if not filename: return web.Response(text="Filename is missing", status=400)
        
        file_path = get_safe_wildcard_path(wildcards_path, filename)
        if not file_path:
            return web.Response(text="Invalid filename or directory traversal attempt.", status=403)

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return web.json_response({"status": "success", "message": f"Deleted {filename}"})
            else:
                return web.Response(text=f"File not found: {filename}", status=404)
        except Exception as e:
            return web.Response(text=f"Error deleting file: {str(e)}", status=500)

def initialize_prompt_list_routes():
    #print("✅ [Santodan Nodes] Initializing PromptListTemplate routes...")

    # This is the class from your other file, so we need to import it
    from .utils import PromptListWithTemplates

    def get_template_dir():
        # We need to recreate this helper function here
        base_path = os.path.dirname(os.path.realpath(utils.__file__))
        return os.path.join(base_path, "prompt_list_templates")

    @server.PromptServer.instance.routes.post("/santodan/save_prompt_list")
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

    @server.PromptServer.instance.routes.post("/santodan/delete_prompt_list")
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

    @server.PromptServer.instance.routes.get("/santodan/view_prompt_list")
    async def view_prompt_list_template(request):
        filename = request.query.get("filename")
        if not filename or filename == "None": return web.Response(status=400, text="...")
        file_path = os.path.join(get_template_dir(), filename)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f: data = json.load(f)
            return web.json_response(data)
        else: return web.Response(status=404, text="Template not found.")

    @server.PromptServer.instance.routes.get("/santodan/get_prompt_lists")
    async def get_prompt_list_templates(request):
        files = PromptListWithTemplates.get_template_files()
        return web.json_response(["None"] + files)