const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

// Track opened diff tabs by their preview file path
const openDiffTabs = new Map();

async function configureTerminalTitle() {
    try {
        const config = vscode.workspace.getConfiguration('terminal.integrated.tabs');
        const currentTitle = config.get('title');

        // Configure VS Code to use escape sequences for terminal titles
        // This allows the CLI to set the tab name via \033]0;title\007
        if (!currentTitle || !currentTitle.includes('${sequence}')) {
            await config.update('title', '${sequence}', vscode.ConfigurationTarget.Global);
            console.log('Configured terminal tabs to use escape sequences');
        }
    } catch (error) {
        console.error('Error configuring terminal title:', error);
    }
}

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    console.log('KK-Code VSC extension is now active');

    // Configure VS Code to respect terminal title escape sequences
    configureTerminalTitle();

    // Watch for command files in all workspace folders
    const watchers = [];

    function setupWatcher(workspaceFolder) {
        const commandsDir = path.join(workspaceFolder.uri.fsPath, '.kkcode', '.vscode-commands');
        const pattern = new vscode.RelativePattern(commandsDir, '*.json');

        const watcher = vscode.workspace.createFileSystemWatcher(pattern);

        watcher.onDidCreate(async (uri) => {
            await processCommandFile(uri);
        });

        watcher.onDidChange(async (uri) => {
            await processCommandFile(uri);
        });

        watchers.push(watcher);
        context.subscriptions.push(watcher);

        // Process any existing command files
        processExistingCommands(commandsDir);
    }

    // Setup watchers for current workspace folders
    if (vscode.workspace.workspaceFolders) {
        for (const folder of vscode.workspace.workspaceFolders) {
            setupWatcher(folder);
        }
    }

    // Watch for new workspace folders
    context.subscriptions.push(
        vscode.workspace.onDidChangeWorkspaceFolders((event) => {
            for (const folder of event.added) {
                setupWatcher(folder);
            }
        })
    );

    // Register commands for manual use
    context.subscriptions.push(
        vscode.commands.registerCommand('kkcode.openDiff', async (leftPath, rightPath, title) => {
            await openDiff(leftPath, rightPath, title || 'KKCode Diff');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('kkcode.closeDiff', async (previewPath) => {
            await closeDiff(previewPath);
        })
    );
}

async function processExistingCommands(commandsDir) {
    try {
        if (!fs.existsSync(commandsDir)) {
            return;
        }

        const files = fs.readdirSync(commandsDir);
        for (const file of files) {
            if (file.endsWith('.json')) {
                const filePath = path.join(commandsDir, file);
                await processCommandFile(vscode.Uri.file(filePath));
            }
        }
    } catch (error) {
        console.error('Error processing existing commands:', error);
    }
}

async function processCommandFile(uri) {
    try {
        // Small delay to ensure file is fully written
        await new Promise(resolve => setTimeout(resolve, 50));

        const content = fs.readFileSync(uri.fsPath, 'utf8');
        const command = JSON.parse(content);

        // Delete the command file after reading
        try {
            fs.unlinkSync(uri.fsPath);
        } catch (e) {
            // Ignore deletion errors
        }

        // Process the command
        switch (command.action) {
            case 'open-diff':
                await openDiff(command.leftPath, command.rightPath, command.title);
                break;
            case 'close-diff':
                await closeDiff(command.previewPath);
                break;
            case 'rename-terminal':
                await renameTerminal(command.name);
                break;
            default:
                console.warn('Unknown command action:', command.action);
        }
    } catch (error) {
        console.error('Error processing command file:', error);
    }
}

async function openDiff(leftPath, rightPath, title) {
    try {
        const leftUri = vscode.Uri.file(leftPath);
        const rightUri = vscode.Uri.file(rightPath);

        // Open diff with preserveFocus to keep terminal focused
        await vscode.commands.executeCommand(
            'vscode.diff',
            leftUri,
            rightUri,
            title || 'KKCode Diff',
            { preserveFocus: true }
        );

        // Track this diff by the right (preview) path
        openDiffTabs.set(rightPath, { leftPath, rightPath, title });

        console.log(`Opened diff: ${leftPath} <-> ${rightPath}`);
    } catch (error) {
        console.error('Error opening diff:', error);
    }
}

async function closeDiff(previewPath) {
    try {
        // Find and close the tab with this preview file
        for (const group of vscode.window.tabGroups.all) {
            for (const tab of group.tabs) {
                // Check if this is a diff tab
                if (tab.input && tab.input.modified) {
                    const modifiedPath = tab.input.modified.fsPath;
                    if (modifiedPath === previewPath) {
                        await vscode.window.tabGroups.close(tab, true);
                        openDiffTabs.delete(previewPath);
                        console.log(`Closed diff tab: ${previewPath}`);
                        return;
                    }
                }
            }
        }

        // Fallback: try matching by original path
        for (const group of vscode.window.tabGroups.all) {
            for (const tab of group.tabs) {
                if (tab.input && tab.input.original) {
                    const originalPath = tab.input.original.fsPath;
                    if (originalPath === previewPath) {
                        await vscode.window.tabGroups.close(tab, true);
                        openDiffTabs.delete(previewPath);
                        console.log(`Closed diff tab (by original): ${previewPath}`);
                        return;
                    }
                }
            }
        }

        console.log(`No diff tab found for: ${previewPath}`);
    } catch (error) {
        console.error('Error closing diff:', error);
    }
}

async function renameTerminal(name) {
    try {
        // Ensure VS Code respects escape sequences for terminal title
        const config = vscode.workspace.getConfiguration('terminal.integrated.tabs');
        const currentTitle = config.get('title');

        // If not already using sequence, update the setting
        if (currentTitle !== '${sequence}') {
            await config.update('title', '${sequence}', vscode.ConfigurationTarget.Global);
            console.log('Updated terminal.integrated.tabs.title to use escape sequences');
        }

        // The Python CLI will set the title via escape sequence
        // This just ensures VS Code is configured to display it
        console.log(`Terminal title setting configured for: ${name}`);
    } catch (error) {
        console.error('Error configuring terminal:', error);
    }
}

function deactivate() {
    openDiffTabs.clear();
}

module.exports = {
    activate,
    deactivate
};
