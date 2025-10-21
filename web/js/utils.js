import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

app.registerExtension({
    name: "Santodan.ListSelector.AutoReset",
    
    // The setup function runs once when ComfyUI starts.
    setup() {
        // We listen for the 'executed' event, which the ComfyUI backend sends
        // after a prompt has finished running.
        api.addEventListener("executed", (event) => {
            console.log("✅ [Santodan] Workflow executed. Checking for ListSelector widgets to auto-reset.");

            // Get all the ListSelector nodes currently on the canvas.
            const listSelectorNodes = app.graph.findNodesByType("ListSelector");

            if (!listSelectorNodes || listSelectorNodes.length === 0) {
                return; // No ListSelector nodes found.
            }

            // Loop through each ListSelector node we found.
            for (const node of listSelectorNodes) {
                // Find the specific 'reset_counter' widget on the node.
                const resetWidget = node.widgets.find(w => w.name === "reset_counter");

                // If the widget exists and its current value is true (meaning it was on)...
                if (resetWidget && resetWidget.value === true) {
                    console.log(`- Auto-flipping reset switch for Node ${node.id}`);
                    // ...then programmatically set its value back to false.
                    resetWidget.value = false;

                    // Redraw the node to show the updated widget state visually
                    app.graph.setDirtyCanvas(true, true);
                }
            }
        });
    },
});