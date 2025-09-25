import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";
import { ComfyDialog, $el } from "/scripts/ui.js";

// Changed version to v12 to confirm the fix is loaded
console.log("✅ Santodan Wildcard Manager JS loaded (v12 - Scrollable Preview).");

// --- CSS CHANGES ARE HERE ---
const style = `
.santodan-preview-container {
    width: 100%;
    max-height: 300px; /* Set a maximum height */
    overflow-y: auto;   /* Enable vertical scrollbar only when needed */
    overflow-x: hidden; /* Hide horizontal scrollbar */
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px; /* Add some internal padding */
    margin-top: 4px; /* Add some space above the container */
    background-color: var(--bg-color, #1a1a1a); /* A slightly different bg for contrast */
    border: 1px solid var(--border-color, #444);
    border-radius: 4px;
    box-sizing: border-box; /* Ensure padding and border are included in the width/height */
}
.santodan-preview-box {
    width: 100%;
    padding: 8px;
    background-color: var(--input-bg-color, #222);
    border-radius: 4px;
    font-family: monospace;
    font-size: 12px;
    color: var(--input-text-color, #ccc);
    box-sizing: border-box;
    white-space: pre-wrap;
    word-break: break-all;
    margin: 0;
}
`;
document.head.appendChild($el("style", { textContent: style }));


class WildcardViewerDialog extends ComfyDialog {
	constructor() {
		super();
		this.element.classList.add("santodan-wildcard-viewer");
	}

	show(filename, content) {
		this.title = `Wildcard: ${filename}.txt`;
        const displayText = (content === undefined || content === null) ? "[Error: Could not load content]" : content;
		
		this.textElement = $el("textarea", {});
		this.textElement.value = displayText || "[File is empty]";
		
		const buttons = $el("div.comfy-modal-buttons", [
			$el("button", { type: "button", textContent: "Close", onclick: () => this.close() }),
		]);

		this.element.replaceChildren($el("div.comfy-modal-content", [
			$el("h2", { textContent: this.title }),
			this.textElement,
			buttons,
		]));

		this.textElement.style.width = '100%';
		this.textElement.style.minHeight = '300px';
		this.textElement.style.fontFamily = 'monospace';
		this.textElement.style.fontSize = '12px';
		this.textElement.readOnly = true;

		super.show();
	}
}

app.registerExtension({
	name: "santodan.WildcardManager",
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		if (nodeData.name === "WildcardManager") {
			
			const onNodeCreated = nodeType.prototype.onNodeCreated;
			nodeType.prototype.onNodeCreated = function () {
				onNodeCreated?.apply(this, arguments);

				const previewContainer = $el("div.santodan-preview-container");
				this.previewContainer = previewContainer;

				setTimeout(() => {
					const previewWidget = this.widgets.find((w) => w.name === "processed_text_preview");
					if (previewWidget && previewWidget.inputEl?.parentNode) {
						previewWidget.inputEl.style.display = "none";
						previewWidget.inputEl.parentNode.appendChild(previewContainer);
					} else {
						console.error("Wildcard Manager: Could not find the preview widget's parent element to attach to.");
					}
				}, 0);

				const wildcardsDropdown = this.widgets.find((w) => w.name === "wildcards_list");
				const textWidget = this.widgets.find((w) => w.name === "text");

				wildcardsDropdown.callback = (value) => {
					if (!value) return;
					const wildcardToInsert = `__${value}__`;
					const textarea = textWidget.inputEl;
					const start = textarea.selectionStart;
					const end = textarea.selectionEnd;
					const newText = textarea.value.substring(0, start) + wildcardToInsert + textarea.value.substring(end);
					textWidget.value = newText;
					setTimeout(() => {
						const newCursorPos = start + wildcardToInsert.length;
						textarea.selectionStart = textarea.selectionEnd = newCursorPos;
						textarea.focus();
					}, 0);
				};
				
				const loadWildcard = async () => {
					const filename = wildcardsDropdown.value;
					if (!filename) {
						return alert("Select a wildcard file to view its content.");
					}
					try {
						const response = await api.fetchApi(`/santodan/wildcard-content?filename=${encodeURIComponent(filename)}`);
						if (!response.ok) {
							throw new Error(`HTTP error! status: ${response.status}`);
						}
						const data = await response.json();
						new WildcardViewerDialog().show(filename, data.content);
					} catch (error) {
						console.error("Failed to load wildcard content:", error);
						alert(`Error loading ${filename}.txt. Check console for details.`);
						new WildcardViewerDialog().show(filename, `Failed to load content.\n\nError: ${error.message}`);
					}
				};
				
				const saveWildcard = async () => {
                    alert("Save functionality is not yet implemented.");
                };
				const deleteWildcard = async () => {
                    alert("Delete functionality is not yet implemented.");
                };

				this.addWidget("button", "View Content", "view", loadWildcard);
				this.addWidget("button", "Save Content", "save", saveWildcard);
				this.addWidget("button", "Delete Selected", "delete", deleteWildcard);
			};
			
			const onExecuted = nodeType.prototype.onExecuted;
			nodeType.prototype.onExecuted = function (message) {
				onExecuted?.apply(this, arguments);

				if (message.preview_list && this.previewContainer) {
					this.previewContainer.replaceChildren(); 
					
					message.preview_list.forEach(line => {
						const previewBox = $el("pre.santodan-preview-box", {
							textContent: line,
						});
						this.previewContainer.appendChild(previewBox);
					});
				}
			};
		}
	},
});

