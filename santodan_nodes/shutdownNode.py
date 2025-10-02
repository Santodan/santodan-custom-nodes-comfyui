import os
import server
import json
import time
import platform
import subprocess
from aiohttp import web
from datetime import datetime
import folder_paths

class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False
any_typ = AnyType("*")

SHUTDOWN_IN_PROGRESS = False

@server.PromptServer.instance.routes.post("/save_and_shutdown/trigger")
async def handle_save_and_shutdown(request):
    global SHUTDOWN_IN_PROGRESS
    
    post_data = await request.json()
    workflow = post_data.get('workflow')
    filepath_from_frontend = post_data.get('filepath')
    params = post_data.get('params', {})
    
    enabled = params.get('enabled', False)
    delay = params.get('delay', 60)
    save_workflow_enabled = params.get('save_workflow', True)
    save_mode = params.get('save_mode', "Save as New Timestamped File")
    new_filename_prefix = params.get('filename_prefix', 'workflow_autosave.json')
    
    if not enabled:
        print("Save & Shutdown API: Triggered, but node is disabled. Aborting.")
        return web.Response(status=200, text="OK, but disabled")
        
    if SHUTDOWN_IN_PROGRESS:
        print("Save & Shutdown API: Shutdown already in progress.")
        return web.Response(status=409, text="Shutdown already initiated")

    prompt_queue = server.PromptServer.instance.prompt_queue
    remaining_tasks = prompt_queue.get_tasks_remaining()

    if remaining_tasks == 0:
        if save_workflow_enabled and workflow:
            save_path = ""
            try:
                if save_mode == "Overwrite Existing File" and filepath_from_frontend:
                    save_path = os.path.join(folder_paths.get_input_directory(), '..', filepath_from_frontend)
                    save_path = os.path.normpath(save_path)
                    print(f"Save & Shutdown API: Preparing to overwrite workflow at '{save_path}'")
                else:
                    if save_mode == "Overwrite Existing File":
                        print("Save & Shutdown API: 'Overwrite' selected, but no original file was loaded. Saving as new file instead.")
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    base, ext = os.path.splitext(new_filename_prefix)
                    ext = ext if ext.lower() == '.json' else '.json'
                    final_filename = f"{base}_{timestamp}{ext}"
                    output_dir = folder_paths.get_output_directory()
                    save_path = os.path.join(output_dir, final_filename)
                    print(f"Save & Shutdown API: Preparing to save new workflow to '{save_path}'")
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(workflow, f, indent=4)
                print(f"Save & Shutdown API: Workflow successfully saved.")
            except Exception as e:
                print(f"Save & Shutdown API: ERROR! Failed to save workflow: {e}")

        SHUTDOWN_IN_PROGRESS = True
        print(f"\n##############################################################")
        print(f"# ComfyUI Queue is empty.")
        print(f"# SHUTDOWN INITIATED! Attempting shutdown in {delay} seconds.")
        print(f"# To cancel, close this command window immediately.")
        print(f"##############################################################\n")
        
        time.sleep(delay)

        try:
            system = platform.system()
            print(f"Save & Shutdown API: Detected Operating System: {system}")
            
            command = []
            if system == "Windows":
                command = ["shutdown", "/s", "/t", "1"]
            else: 
                command = ["sudo", "shutdown", "-h", "now"]
            
            print(f"Save & Shutdown API: Preparing to execute command: {' '.join(command)}")

            result = subprocess.run(command, capture_output=True, text=True)

            print(f"Save & Shutdown API: Command executed. Return code: {result.returncode}")
            if result.stdout:
                print(f"Save & Shutdown API: Command output (stdout):\n{result.stdout}")
            if result.stderr:
                print(f"Save & Shutdown API: Command error output (stderr):\n{result.stderr}")

        except Exception as e:
            print(f"Save & Shutdown API: An unexpected error occurred: {e}")
        finally:
            SHUTDOWN_IN_PROGRESS = False 
        
        return web.Response(status=200, text="Shutdown initiated")
    else:
        print(f"Save & Shutdown API: Triggered, but {remaining_tasks} items still in queue. Shutdown aborted.")
        return web.Response(status=200, text="OK, but queue not empty")

class SaveWorkflowAndShutdown:
    @classmethod
    def INPUT_TYPES(cls):
        return { "required": {
                "trigger": (any_typ, {}),
                "enabled": ("BOOLEAN", {"default": False}),
                "delay_seconds": ("INT", {"default": 60, "min": 10, "max": 600, "step": 10}),
                "save_workflow": ("BOOLEAN", {"default": True}),
                "save_mode": (["Overwrite Existing File", "Save as New Timestamped File"],),
                "filename_prefix": ("STRING", {"default": "workflow_autosave.json"}),
            }
        }

    RETURN_TYPES = (any_typ, "STRING",)
    RETURN_NAMES = ("passthrough", "status",)
    FUNCTION = "execute"
    OUTPUT_NODE = False 
    CATEGORY = "utils"

    def execute(self, trigger, enabled, delay_seconds, save_workflow, save_mode, filename_prefix):
        system = platform.system() 
        prompt_queue = server.PromptServer.instance.prompt_queue
        queue_remaining = prompt_queue.get_tasks_remaining()
        
        status = "Status: Disabled"
        if enabled:
            if queue_remaining <= 1: 
                status = f"Status: Final job. Triggering shutdown on {system}."
            else:
                jobs_after_this = queue_remaining - 1
                status = f"Status: {jobs_after_this} item(s) queued after this. Waiting..."

        ui_data = {
            "enabled": [enabled], "delay": [delay_seconds], "save_workflow": [save_workflow],
            "save_mode": [save_mode], "filename_prefix": [filename_prefix]
        }

        return {"ui": ui_data, "result": (trigger, status)}