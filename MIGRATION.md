# Migrating to the Forked WFRP3e System

Because both the main author's system and this fork share the same system ID (`wfrp3e`), you can seamlessly switch between them without needing to modify your game worlds. 

Foundry VTT handles system updates by overwriting the contents of the `Data/systems/wfrp3e` folder. Here is how you can easily swap between the two versions.

## Switching to this Fork

To install and use your customized fork:
1. Open Foundry VTT and navigate to the **Game Systems** tab.
2. Click **Install System**.
3. In the "Manifest URL" field at the bottom, paste the link to your fork's `system.json`. Because of the newly updated workflow, your manifest URL will be:
   `https://github.com/<YOUR_GITHUB_USERNAME>/wfrp3e/releases/latest/download/system.json`
   *(Replace `<YOUR_GITHUB_USERNAME>` with your actual GitHub username).*
4. Click **Install**. Foundry will warn you that the system already exists. Proceed to overwrite it.

## Switching back to the Main Author's System

If you ever need to revert to the official version:
1. In Foundry VTT, go to the **Game Systems** tab.
2. Click **Install System**.
3. Paste the main author's manifest URL:
   `https://github.com/McGregor777/wfrp3e/releases/latest/download/system.json`
4. Click **Install** and proceed to overwrite the fork.

## Note on Worlds
Since both versions use the exact same ID (`wfrp3e`), any worlds created with the main author's version will open perfectly on your fork (and vice versa). You do **not** need to edit your `world.json` files or migrate your world data just to switch systems. 

> [!TIP]
> Make sure to fully restart your Foundry server or close the application completely when switching system manifests to ensure the new files are loaded properly.
