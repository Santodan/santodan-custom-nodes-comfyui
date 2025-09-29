import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

// --- Helper Functions ---
function getWidget(node, name) {
    return node.widgets.find((w) => w.name === name);
}

async function refreshTemplateList(node) {
    const templateWidget = getWidget(node, "template_file");
    if (!templateWidget) return;

    try {
        const res = await api.fetchApi("/easyuse/get_prompt_lists");
        if (!res.ok) {
            throw new Error(`Failed to fetch: ${res.status} ${res.statusText}`);
        }
        const files = await res.json();
        const currentValue = templateWidget.value;
        templateWidget.options.values = files;
        templateWidget.value = files.includes(currentValue) ? currentValue : "None";
    } catch (error) {
        console.error("Failed to refresh prompt list templates:", error);
        // Backwards compatibility check for notifications
        if (api.showErrorMessage) {
            api.showErrorMessage("Could not refresh prompt templates. See console for details.");
        } else {
            alert("Could not refresh prompt templates. See console for details.");
        }
    }
}

// --- Main Extension Logic ---
app.registerExtension({
    name: "EasyUse.PromptListWithTemplates",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "PromptListWithTemplates") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                onNodeCreated?.apply(this, arguments);

                // --- Define Callbacks for Buttons ---

                const handleSave = async () => {
                    const saveFilenameWidget = getWidget(this, "save_filename");
                    if (!saveFilenameWidget || !saveFilenameWidget.value) {
                        if (api.showInfoMessage) api.showInfoMessage("Please enter a save filename.");
                        else alert("Please enter a save filename.");
                        return;
                    }

                    const prompts = {};
                    for (let i = 1; i <= 5; i++) {
                        const widget = getWidget(this, `prompt_${i}`);
                        if (widget) prompts[`prompt_${i}`] = widget.value;
                    }

                    try {
                        await api.fetchApi("/easyuse/save_prompt_list", {
                            method: "POST",
                            body: JSON.stringify({ filename: saveFilenameWidget.value, prompts: prompts }),
                        });
                        if (api.showSuccessMessage) api.showSuccessMessage(`Template '${saveFilenameWidget.value}' saved!`);
                        else alert(`Template '${saveFilenameWidget.value}' saved!`);
                        await refreshTemplateList(this);
                    } catch (error) {
                        if (api.showErrorMessage) api.showErrorMessage("Error saving template: " + error);
                        else alert("Error saving template: " + error);
                    }
                };

                const handleLoad = async () => {
                    const templateWidget = getWidget(this, "template_file");
                    if (!templateWidget || templateWidget.value === "None") {
                        if (api.showInfoMessage) api.showInfoMessage("Please select a template to load.");
                        else alert("Please select a template to load.");
                        return;
                    }

                    try {
                        const res = await api.fetchApi(`/easyuse/view_prompt_list?filename=${encodeURIComponent(templateWidget.value)}`);
                        const data = await res.json();
                        for (let i = 1; i <= 5; i++) {
                            const widget = getWidget(this, `prompt_${i}`);
                            if (widget) widget.value = data[`prompt_${i}`] || "";
                        }
                        const saveFilenameWidget = getWidget(this, "save_filename");
                        if (saveFilenameWidget) saveFilenameWidget.value = templateWidget.value;
                        /*if (api.showSuccessMessage) api.showSuccessMessage(`Template '${templateWidget.value}' loaded!`);
                        else alert(`Template '${templateWidget.value}' loaded!`);*/
                    } catch (error) {
                        if (api.showErrorMessage) api.showErrorMessage("Error loading template: " + error);
                        else alert("Error loading template: " + error);
                    }
                };

                const handleDelete = async () => {
                    const templateWidget = getWidget(this, "template_file");
                    if (!templateWidget || templateWidget.value === "None") {
                        if (api.showInfoMessage) api.showInfoMessage("Please select a template to delete.");
                        else alert("Please select a template to delete.");
                        return;
                    }

                    if (!confirm(`Are you sure you want to delete "${templateWidget.value}"? This cannot be undone.`)) {
                        return;
                    }

                    try {
                        await api.fetchApi("/easyuse/delete_prompt_list", {
                            method: "POST",
                            body: JSON.stringify({ filename: templateWidget.value }),
                        });
                        if (api.showSuccessMessage) api.showSuccessMessage(`Template '${templateWidget.value}' deleted!`);
                        else alert(`Template '${templateWidget.value}' deleted!`);
                        await refreshTemplateList(this);
                    } catch (error) {
                        if (api.showErrorMessage) api.showErrorMessage("Error deleting template: " + error);
                        else alert("Error deleting template: " + error);
                    }
                };

                // --- Add Widgets Natively ---
                this.addWidget("button", "Save Template", "save_template", handleSave);
                this.addWidget("button", "Load Template", "load_template", handleLoad);
                this.addWidget("button", "Delete Template", "delete_template", handleDelete);
                
                // Refresh the list once when the node is created
                setTimeout(() => refreshTemplateList(this), 100);
            };
        }
    },
});

console.log("✅ Santodan PromptList w/ Templates JS loaded (v2 - compatibility fix).");
