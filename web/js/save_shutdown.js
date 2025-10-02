import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

console.log("✅ Santodan shutdown JS loaded.");

app.registerExtension({
    name: "Comfy.SaveWorkflowAndShutdown",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "SaveWorkflowAndShutdown") {
            console.log("✅ Matched 'SaveWorkflowAndShutdown' node. Attaching onExecuted callback.");
            
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                onExecuted?.apply(this, arguments);

                // Check if the message contains our data structure
                if (message?.enabled && Array.isArray(message.enabled)) {
                    
                    // THE JAVASCRIPT FIX IS HERE:
                    // We extract the single value from the list using [0]
                    const params = {
                        enabled: message.enabled[0],
                        delay: message.delay[0],
                        save_workflow: message.save_workflow[0],
                        save_mode: message.save_mode[0],
                        filename_prefix: message.filename_prefix[0],
                    };

                    console.log("Save & Shutdown (JS): Found params:", params);
                    
                    if (params.enabled) {
                        console.log("Save & Shutdown (JS): Node is enabled. Preparing to call API.");
                        
                        const current_workflow = app.graph.serialize();
                        const current_filepath = app.graph._filename;

                        const body = {
                            workflow: current_workflow,
                            filepath: current_filepath,
                            params: params // Send the unpacked params
                        };

                        console.log("Save & Shutdown (JS): Sending API request to /save_and_shutdown/trigger");

                        api.fetchApi("/save_and_shutdown/trigger", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify(body),
                        })
                        .then(response => {
                             console.log("Save & Shutdown (JS): API Response:", response.status, response.statusText);
                             if (!response.ok) {
                                console.error("Save & Shutdown (JS): API call failed with status", response.status);
                             }
                        })
                        .catch(error => {
                            console.error("Save & Shutdown (JS): Error calling API:", error);
                        });
                    } else {
                        console.log("Save & Shutdown (JS): Node is disabled. No action taken.");
                    }
                }
            };
        }
    },
});
