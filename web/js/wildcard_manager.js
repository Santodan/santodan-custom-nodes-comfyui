import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";
import { ComfyDialog, $el } from "/scripts/ui.js";

// Changed version to v21 to confirm the fix is loaded
console.log("✅ Santodan Wildcard Manager JS loaded (v21 - Added Insert Button).");

const style = `
.santodan-preview-container { width: 100%; max-height: 300px; overflow-y: auto; overflow-x: hidden; display: flex; flex-direction: column; gap: 4px; padding: 8px; margin-top: 4px; background-color: var(--bg-color, #1a1a1a); border: 1px solid var(--border-color, #444); border-radius: 4px; box-sizing: border-box; }
.santodan-preview-box { width: 100%; padding: 8px; background-color: var(--input-bg-color, #222); border-radius: 4px; font-family: monospace; font-size: 12px; color: var(--input-text-color, #ccc); box-sizing: border-box; white-space: pre-wrap; word-break: break-all; margin: 0; }
.santodan-wildcard-editor-dialog .comfy-modal-content { display: flex; flex-direction: column; height: 90%; }
.santodan-wildcard-editor-dialog textarea { width: 100%; flex-grow: 1; min-height: 300px; }
`;
document.head.appendChild($el("style", { textContent: style }));

class WildcardEditorDialog extends ComfyDialog {
	constructor() { super(); this.element.classList.add("santodan-wildcard-editor-dialog"); }
	show(filename, content, saveCallback) {
		this.title = `Editing: ${filename}.txt`;
        const initialContent = (content === undefined || content === null) ? "" : content;
		this.textElement = $el("textarea");
        this.textElement.value = initialContent;
		const buttons = $el("div.comfy-modal-buttons", [
            $el("button", { type: "button", textContent: "Save & Close", onclick: () => { if (saveCallback) saveCallback(filename, this.textElement.value); this.close(); }, }),
			$el("button", { type: "button", textContent: "Cancel", onclick: () => this.close() }),
		]);
		this.element.replaceChildren($el("div.comfy-modal-content", [ $el("h2", { textContent: this.title }), this.textElement, buttons, ]));
		super.show();
	}
}

async function refreshWildcardList(node) {
    const wildcardsDropdown = node.widgets.find((w) => w.name === "wildcards_list");
    if (!wildcardsDropdown) return;
    const currentValue = wildcardsDropdown.value;
    try {
        const response = await api.fetchApi("/santodan/wildcards");
        if (!response.ok) throw new Error("Failed to fetch wildcard list.");
        const newList = await response.json();
        const fullList = ["[Create New]", ...newList];
        wildcardsDropdown.options.values = fullList;
        if (fullList.includes(currentValue)) { wildcardsDropdown.value = currentValue; } 
        else { wildcardsDropdown.value = "[Create New]"; }
        if(app.canvas) app.canvas.draw(true, true);
    } catch (error) { console.error("Wildcard Manager: Failed to refresh wildcard list.", error); }
}

app.registerExtension({
	name: "santodan.WildcardManager",
	async beforeRegisterNodeDef(nodeType, nodeData) {
		if (nodeData.name === "WildcardManager") {
			const onNodeCreated = nodeType.prototype.onNodeCreated;
			nodeType.prototype.onNodeCreated = function () {
				onNodeCreated?.apply(this, arguments);
				const previewContainer = $el("div.santodan-preview-container");
				this.previewContainer = previewContainer;
				setTimeout(() => {
					const previewWidget = this.widgets.find((w) => w.name === "processed_text_preview");
					if (previewWidget?.inputEl?.parentNode) {
						previewWidget.inputEl.style.display = "none";
						previewWidget.inputEl.parentNode.appendChild(previewContainer);
					}
				}, 0);
				
				const wildcardsDropdown = this.widgets.find((w) => w.name === "wildcards_list");
				const textWidget = this.widgets.find((w) => w.name === "text");

                // We no longer need the dropdown callback for insertion.
				wildcardsDropdown.callback = () => {};

				const saveCallback = async (filename, content) => {
                    try {
                        const response = await api.fetchApi("/santodan/wildcard-save", {
                            method: "POST", headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ filename, content }),
                        });
                        if (!response.ok) throw new Error(await response.text());
                        console.log("Wildcard saved:", filename);
                        await refreshWildcardList(this);
                        wildcardsDropdown.value = filename;
                    } catch (error) { console.error("Failed to save wildcard:", error); alert(`Error saving ${filename}.txt: ${error.message}`); }
                };

                // ========= NEW FUNCTIONALITY START =========
                const handleInsert = () => {
                    const value = wildcardsDropdown.value;
                    if (!value || value === "[Create New]" || value.startsWith("(")) {
                        return; // Do nothing if the selection is not a valid wildcard
                    }
					const wildcardToInsert = `__${value}__`;
					const textarea = textWidget.inputEl;
					const start = textarea.selectionStart, end = textarea.selectionEnd;
					const newText = textarea.value.substring(0, start) + wildcardToInsert + textarea.value.substring(end);
					textWidget.value = newText;
                    this.setDirtyCanvas(true, true);
					setTimeout(() => { textarea.selectionStart = textarea.selectionEnd = start + wildcardToInsert.length; textarea.focus(); }, 0);
                };
                // ========= NEW FUNCTIONALITY END =========

                const handleEditOrCreate = async () => {
                    let filename = wildcardsDropdown.value;
                    if (filename === "[Create New]") {
                        const newFilename = prompt("Enter a name for the new wildcard file (without .txt):");
                        if (newFilename && newFilename.trim()) { new WildcardEditorDialog().show(newFilename.trim(), "", saveCallback); }
                        return;
                    }
					if (!filename || filename.startsWith("(")) { return alert("Please select a valid wildcard file to edit."); }
					try {
						const response = await api.fetchApi(`/santodan/wildcard-content?filename=${encodeURIComponent(filename)}`);
						if (!response.ok) throw new Error(await response.text());
						const data = await response.json();
                        if (data.error) { throw new Error(data.error); }
                        if (data.content === undefined) { throw new Error("API response did not contain the 'content' key."); }
						new WildcardEditorDialog().show(filename, data.content, saveCallback);
					} catch (error) { console.error("Failed to load wildcard content:", error); alert(`Error loading ${filename}.txt: ${error.message}`); }
                };

				const deleteWildcard = async () => {
                    const filename = wildcardsDropdown.value;
					if (!filename || filename === "[Create New]" || filename.startsWith("(")) { return alert("Please select a valid wildcard file to delete."); }
                    if (confirm(`Are you sure you want to permanently delete "${filename}.txt"?\nThis cannot be undone.`)) {
                        try {
                            const response = await api.fetchApi("/santodan/wildcard-delete", {
                                method: "DELETE", headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ filename }),
                            });
                            if (!response.ok) throw new Error(await response.text());
                            console.log("Wildcard deleted:", filename);
                            await refreshWildcardList(this);
                        } catch (error) { console.error("Failed to delete wildcard:", error); alert(`Error deleting ${filename}.txt: ${error.message}`); }
                    }
                };

                // Add the new button and re-order them for clarity
				this.addWidget("button", "Insert Selected", "insert", handleInsert);
				this.addWidget("button", "Edit/Create Wildcard", "edit_create", handleEditOrCreate);
				this.addWidget("button", "Delete Selected", "delete", deleteWildcard);
			};

			const onExecuted = nodeType.prototype.onExecuted;
			nodeType.prototype.onExecuted = function (message) {
				onExecuted?.apply(this, arguments);
				if (message.preview_list && this.previewContainer) {
					this.previewContainer.replaceChildren(); 
					message.preview_list.forEach(line => { this.previewContainer.appendChild($el("pre.santodan-preview-box", { textContent: line })); });
				}
			};
		}
	},
});
