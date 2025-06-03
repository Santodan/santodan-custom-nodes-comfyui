# santodan Custom Nodes for ComfyUI

This is a work in progress repo. 

## Randomize LoRAs Node
The Randomize LoRAs node randomly loads LoRAs based on a predefined selection with also randomized weights. This enables users to experiment with different artistic effects on their generated images.

__insertImage__

### How It Works
Connect the **model** and **clip** outputs from this node to your KSampler or other processing nodes. The output, **chosen loras**, provides a textual representation detailing which LoRAs and corresponding weights were applied during the generation.

You can also provide the **trigger words** for each lora. They will be outputted as a formatted text separated by commas. Useful for you to concatenate the trigger words into your prompts.

### Configuration Fields
- **max_random**: Limits the maximum number of LoRAs to apply. Even if you select up to 10, you can choose to apply fewer.
- **lora_x**: Specifies the LoRA file to use.
- **min_str_x** and **max_str_x**: Defines the minimum and maximum strengths for each LoRA, allowing for a range of intensities.
- **trigger_words_x**: The trigger words for the selected lora.


## Installation
You can use the [ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager). Search for "santodan" or "santodan-nodes".

Or you can install it manually:

1. Open your terminal and navigate to your `ComfyUI/custom_nodes` directory.
2. Clone the repository using:
   ```
   git clone https://github.com/Santodan/santodan-custom-nodes
   ```
3. Restart ComfyUI to apply the changes.  

### Uninstallation
To remove the custom node:
1. Delete the `santodan-nodes-comfyui` directory from `ComfyUI/custom_nodes`.
2. Restart ComfyUI to apply the changes. 

### Updates
To update the node:

1. Navigate to `ComfyUI/custom_nodes/santodan-nodes-comfyui` in your terminal.
2. Run the following command: `git pull`
3. Restart ComfyUI to apply the changes.

# Credits
Suzie1 / [Comfyroll_CustomNodes](https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes) - got the randomize idea from it
jitcoder / [lora-info](https://github.com/jitcoder/lora-info) - the trigger_words extraction is all from this node, just implemented in mine
