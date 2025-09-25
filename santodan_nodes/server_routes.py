import os
import server
from aiohttp import web
from werkzeug.utils import secure_filename

# This function will be called from __init__.py to set up all the web routes.
def initialize_routes(wildcards_path):
    print("[Santodan Nodes] Initializing wildcard API routes...")

    @server.PromptServer.instance.routes.get("/santodan/wildcards")
    async def get_wildcards_endpoint(request):
        if not os.path.exists(wildcards_path):
            return web.json_response([])
        files = [f for f in os.listdir(wildcards_path) if os.path.isfile(os.path.join(wildcards_path, f))]
        filenames = sorted([os.path.splitext(f)[0] for f in files if f.lower().endswith('.txt')])
        return web.json_response(filenames)

    @server.PromptServer.instance.routes.get("/santodan/wildcard-content")
    async def get_wildcard_content(request):
        filename = request.query.get('filename')
        if not filename:
            return web.Response(text="Filename parameter is missing", status=400)
        
        safe_filename = secure_filename(filename) + ".txt"
        file_path = os.path.join(wildcards_path, safe_filename)

        if os.path.commonpath([wildcards_path, os.path.abspath(file_path)]) != wildcards_path:
            return web.Response(text="Directory traversal attempt detected.", status=403)

        try:
            print(f"[Santodan Wildcard Manager] Attempting to read file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"[Santodan Wildcard Manager] Success! Sending content for '{safe_filename}'.")
            return web.json_response({"content": content})
        except FileNotFoundError:
            print(f"[Santodan Wildcard Manager] File not found. Sending empty content for new file '{safe_filename}'.")
            return web.json_response({"content": ""})
        except Exception as e:
            print(f"[Santodan Wildcard Manager] ERROR reading file {safe_filename}: {e}")
            return web.json_response({"error": f"Failed to read file: {e}"}, status=500)

    @server.PromptServer.instance.routes.post("/santodan/wildcard-save")
    async def save_wildcard_content(request):
        data = await request.json()
        filename = data.get('filename')
        content = data.get('content', '')

        if not filename: return web.Response(text="Filename is missing", status=400)
        safe_filename = secure_filename(filename) + ".txt"
        file_path = os.path.join(wildcards_path, safe_filename)
        if os.path.commonpath([wildcards_path, os.path.abspath(file_path)]) != wildcards_path:
            return web.Response(text="Directory traversal attempt detected.", status=403)
        try:
            with open(file_path, 'w', encoding='utf-8') as f: f.write(content)
            return web.json_response({"status": "success", "message": f"Saved {safe_filename}"})
        except Exception as e:
            return web.Response(text=f"Error saving file: {str(e)}", status=500)

    @server.PromptServer.instance.routes.delete("/santodan/wildcard-delete")
    async def delete_wildcard_file(request):
        data = await request.json()
        filename = data.get('filename')
        if not filename: return web.Response(text="Filename is missing", status=400)
        safe_filename = secure_filename(filename) + ".txt"
        file_path = os.path.join(wildcards_path, safe_filename)
        if os.path.commonpath([wildcards_path, os.path.abspath(file_path)]) != wildcards_path:
            return web.Response(text="Directory traversal attempt detected.", status=403)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return web.json_response({"status": "success", "message": f"Deleted {safe_filename}"})
            else:
                return web.Response(text=f"File not found: {safe_filename}", status=404)
        except Exception as e:
            return web.Response(text=f"Error deleting file: {str(e)}", status=500)
