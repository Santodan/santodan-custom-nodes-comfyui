import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";
import { ComfyDialog, $el } from "/scripts/ui.js";

const style = `
.santodan-preview-container {
    width: 100%;
    max-height: 300px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px;
    margin-top: 4px;
    background-color: var(--bg-color, #1a1a1a);
    border: 1px solid var(--border-color, #444);
    border-radius: 4px;
    box-sizing: border-box;
}
.santodan-preview-box {
    width: 100%;
    padding: 8px 10px;
    background-color: var(--input-bg-color, #222);
    border-radius: 4px;
    font-family: monospace;
    font-size: 12px;
    color: var(--input-text-color, #ccc);
    white-space: pre-wrap !important;
    overflow-wrap: break-word !important;
}
.santodan-wildcard-editor-dialog textarea {
    width: 100% !important;
    min-height: 300px;
    background: #111;
    color: #fff;
    font-family: monospace;
}
`;
document.head.appendChild($el("style", { textContent: style }));

class WildcardEditorDialog extends ComfyDialog {
	constructor() { super(); this.element.classList.add("santodan-wildcard-editor-dialog"); }
	show(filename, content, saveCallback) {
		this.title = `Editing: ${filename}`;
		this.textElement = $el("textarea", { value: content || "" });
		const buttons = $el("div.comfy-modal-buttons", [
            $el("button", { type: "button", textContent: "Save & Close", onclick: () => { if (saveCallback) saveCallback(filename, this.textElement.value); this.close(); }, }),
			$el("button", { type: "button", textContent: "Cancel", onclick: () => this.close() }),
		]);
		this.element.replaceChildren($el("div.comfy-modal-content", [ $el("h2", { textContent: this.title }), this.textElement, buttons ]));
		super.show();
	}
}

async function refreshWildcardList(node) {
    const dropdown = node.widgets.find((w) => w.name === "wildcards_list");
    if (!dropdown) return;
    try {
        const response = await api.fetchApi("/santodan/wildcards");
        const newList = await response.json();
        dropdown.options.values = ["[Create New]", ...newList];
    } catch (error) { console.error("Failed to refresh list", error); }
}

app.registerExtension({
    name: "santodan.WildcardManager",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "WildcardManager") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                onNodeCreated?.apply(this, arguments);

                // --- 1. Insertion Logic (Robust search for the text field) ---
                const handleInsert = () => {
                    const dropdown = this.widgets.find((w) => w.name === "wildcards_list");
                    
                    // Look for the widget by name "text" OR "input_text" OR by its multiline type
                    const target = this.widgets.find((w) => w.name === "text" || w.name === "input_text") 
                                 || this.widgets.find((w) => w.type === "customtext" || w.options?.multiline);
                    
                    if (!dropdown || !target) {
                        console.error("Wildcard Manager: Could not find the text widget to insert into.");
                        return;
                    }

                    const val = dropdown.value;
                    if (!val || val === "[Create New]" || val.startsWith("(")) return;
                    
                    const wildcard = `__${val}__`;
                    
                    // Modern ComfyUI usually puts the textarea in inputEl
                    const textarea = target.inputEl || target.element?.querySelector('textarea');
                    
                    if (textarea) {
                        const start = textarea.selectionStart;
                        const end = textarea.selectionEnd;
                        const oldText = textarea.value;
                        
                        textarea.value = oldText.substring(0, start) + wildcard + oldText.substring(end);
                        target.value = textarea.value;
                        
                        // Refocus and set cursor
                        textarea.setSelectionRange(start + wildcard.length, start + wildcard.length);
                        textarea.focus();
                        
                        // This event is CRITICAL for ComfyUI to acknowledge the change
                        textarea.dispatchEvent(new Event('input', { bubbles: true }));
                        textarea.dispatchEvent(new Event('change', { bubbles: true }));
                    } else {
                        // Fallback if no textarea is found (updates data but not UI visually)
                        target.value += wildcard;
                    }
                    this.setDirtyCanvas(true, true);
                };

                // --- 2. Edit Logic ---
                const saveCallback = async (filename, content) => {
                    await api.fetchApi("/santodan/wildcard-save", {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ filename, content }),
                    });
                    await refreshWildcardList(this);
                };

                const handleEdit = async () => {
                    const dropdown = this.widgets.find((w) => w.name === "wildcards_list");
                    let filename = dropdown ? dropdown.value : null;
                    if (!filename || filename === "[Create New]") {
                        filename = prompt("Enter filename:");
                        if (!filename) return;
                    }
                    const res = await api.fetchApi(`/santodan/wildcard-content?filename=${encodeURIComponent(filename)}`);
                    const data = await res.json();
                    new WildcardEditorDialog().show(filename, data.content, saveCallback);
                };

                // --- 3. Delete Logic ---
                const handleDelete = async () => {
                    const dropdown = this.widgets.find((w) => w.name === "wildcards_list");
                    const filename = dropdown ? dropdown.value : null;
                    if (!filename || filename === "[Create New]") return;
                    if (confirm(`Delete ${filename}?`)) {
                        await api.fetchApi("/santodan/wildcard-delete", {
                            method: "DELETE", headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ filename }),
                        });
                        await refreshWildcardList(this);
                    }
                };

                // --- 4. Add Buttons (serialize: false is key) ---
                this.addWidget("button", "Insert Selected", "insert", handleInsert, { serialize: false });
                this.addWidget("button", "Edit/Create Wildcard", "edit", handleEdit, { serialize: false });
                this.addWidget("button", "Delete Selected", "delete", handleDelete, { serialize: false });

                // --- 5. Positioning ---
                const dropdown = this.widgets.find((w) => w.name === "wildcards_list");
                const dropdownIdx = this.widgets.indexOf(dropdown);
                if (dropdownIdx !== -1) {
                    const btns = this.widgets.splice(this.widgets.length - 3, 3);
                    this.widgets.splice(dropdownIdx + 1, 0, ...btns);
                }

                // --- 6. Preview ---
                this.previewContainer = $el("div.santodan-preview-container");
                this.addDOMWidget("preview_output", "preview", this.previewContainer);
                
                this.setSize(this.computeSize());
            };

            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                onExecuted?.apply(this, arguments);
                if (message?.preview_list && this.previewContainer) {
                    this.previewContainer.replaceChildren();
                    message.preview_list.forEach(line => {
                        this.previewContainer.appendChild($el("div.santodan-preview-box", { textContent: line }));
                    });
                }
            };
        }
    },
});