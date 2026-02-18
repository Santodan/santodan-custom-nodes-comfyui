import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";
import { ComfyDialog, $el } from "/scripts/ui.js";


console.log("✅ Santodan Wildcard Manager JS loaded.");

const style = `
.santodan-preview-container {
    width: 100%;
    max-height: 300px;
    overflow-y: auto;
    overflow-x: hidden !important;
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
    margin: 0;
    padding: 8px 10px;
    background-color: var(--input-bg-color, #222);
    border-radius: 4px;
    font-family: monospace;
    font-size: 12px;
    color: var(--input-text-color, #ccc);
    box-sizing: border-box;
    
    /* Core wrapping rules - override defaults */
    white-space: pre-wrap !important;
    overflow-wrap: break-word !important;
    word-wrap: break-word !important;
    word-break: break-word !important;     /* softer than break-all */
    
    /* Prevent horizontal scroll at all costs */
    overflow-x: hidden !important;
    max-width: 100% !important;
}

/* Optional: make long words break more gracefully if needed */
.santodan-preview-box code, 
.santodan-preview-box span {
    white-space: pre-wrap !important;
    overflow-wrap: break-word !important;
}

/* Editor textarea (for completeness, if you still want to fix it too) */
.santodan-wildcard-editor-dialog textarea {
    width: 100% !important;
    flex-grow: 1;
    min-height: 300px;
    white-space: pre-wrap !important;
    overflow-wrap: break-word !important;
    word-wrap: break-word !important;
    word-break: break-word !important;
    resize: vertical;
}
`;
document.head.appendChild($el("style", { textContent: style }));

class WildcardEditorDialog extends ComfyDialog {
	constructor() { super(); this.element.classList.add("santodan-wildcard-editor-dialog"); }
	show(filename, content, saveCallback) {
		this.title = `Editing: ${filename}`;
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

					// ────────────────────────────────────────────────
					// NEW: Sync font size from a native ComfyUI textarea
					const syncPreviewFontSize = () => {
						// Look for any existing multiline input on the canvas
						const nativeTextarea = document.querySelector(
							'.comfy-multiline-input, textarea.multiline-widget, .comfyui-prompt-textarea'
						);

						if (nativeTextarea) {
							const computedStyle = window.getComputedStyle(nativeTextarea);
							const fontSize = computedStyle.fontSize;  // e.g. "14px"

							// Apply to container (affects all children unless overridden)
							if (this.previewContainer) {
								this.previewContainer.style.fontSize = fontSize;
							}

							// Also apply directly to each preview box for safety
							document.querySelectorAll('.santodan-preview-box').forEach(box => {
								box.style.fontSize = fontSize;
							});

							console.log("[WildcardManager] Preview font size synced to:", fontSize);
						}
					};

					// Run it once right after attaching
					syncPreviewFontSize();

					// Optional: re-sync if user changes setting while node is open
					// (MutationObserver on body is lightweight and catches most UI updates)
					const observer = new MutationObserver(syncPreviewFontSize);
					observer.observe(document.body, { childList: true, subtree: true, attributes: true });

					// Cleanup when node is removed (optional but good practice)
					const originalOnRemoved = this.onRemoved;
					this.onRemoved = () => {
						observer.disconnect();
						originalOnRemoved?.apply(this);
					};
				}, 0);
				
				const wildcardsDropdown = this.widgets.find((w) => w.name === "wildcards_list");
				const textWidget = this.widgets.find((w) => w.name === "text");

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
                    } catch (error) { console.error("Failed to save wildcard:", error); alert(`Error saving ${filename}: ${error.message}`); }
                };

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

                const handleEditOrCreate = async () => {
                    let filename = wildcardsDropdown.value;
                    if (filename === "[Create New]") {
                        const newFilename = prompt("Enter a name for the new file (e.g., 'new_wildcard' or 'subfolder/new_wildcard', it can also support.yaml files):");
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
					} catch (error) { console.error("Failed to load wildcard content:", error); alert(`Error loading ${filename}: ${error.message}`); }
                };

				const deleteWildcard = async () => {
                    const filename = wildcardsDropdown.value;
					if (!filename || filename === "[Create New]" || filename.startsWith("(")) { return alert("Please select a valid wildcard file to delete."); }
                    if (confirm(`Are you sure you want to permanently delete "${filename}"?\nThis cannot be undone.`)) {
                        try {
                            const response = await api.fetchApi("/santodan/wildcard-delete", {
                                method: "DELETE", headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ filename }),
                            });
                            if (!response.ok) throw new Error(await response.text());
                            console.log("Wildcard deleted:", filename);
                            await refreshWildcardList(this);
                        } catch (error) { console.error("Failed to delete wildcard:", error); alert(`Error deleting ${filename}: ${error.message}`); }
                    }
                };

                const insertButton = this.addWidget("button", "Insert Selected", "insert", handleInsert);
                const editButton = this.addWidget("button", "Edit/Create Wildcard", "edit_create", handleEditOrCreate);
                const deleteButton = this.addWidget("button", "Delete Selected", "delete", deleteWildcard);

                const dropdownIndex = this.widgets.findIndex((w) => w.name === "wildcards_list");
                if (dropdownIndex !== -1) {
                    const buttons = this.widgets.splice(this.widgets.length - 3, 3);
                    this.widgets.splice(dropdownIndex + 1, 0, ...buttons);
                }

                const dropdownEl = wildcardsDropdown.element; 
                if (dropdownEl) {
                    dropdownEl.after(
                        insertButton.element, 
                        editButton.element, 
                        deleteButton.element
                    );
                }
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
