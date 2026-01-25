# Manuscript Build Plugin for Obsidian

Build academic manuscripts to PDF and DOCX directly from Obsidian using Pandoc. This plugin provides a graphical interface for the manuscript build system, replacing the command-line workflow with an intuitive modal dialog.

## Features

- **Build Modal** - Complete UI for all build options:
  - Source file selection
  - Frontmatter file selection
  - Output format (PDF/DOCX)
  - Profile selection with categories
  - Typography settings (font, size)
  - Citation style selection
  - SI reference integration
  - SI formatting options

- **Commands**:
  - `Build Manuscript: Open Build Dialog` - Full build options
  - `Build Manuscript: Quick Build (Repeat Last)` - Repeat previous build
  - `Build Manuscript: Build Current File` - Build active file with defaults

- **Ribbon Icon** - One-click access to the build dialog

- **Settings Panel** - Configure:
  - Python path
  - Build script location
  - Default profile, font, size, citation style
  - Notification preferences
  - Auto-open export folder

- **Build Output** - Real-time build progress with success/error status

## Requirements

- [Python 3](https://www.python.org/) installed and accessible
- [Pandoc](https://pandoc.org/) installed
- The `build.py` script in your vault root
- LaTeX distribution (for PDF output) - e.g., TeX Live, MiKTeX

## Installation

### From Source (Development)

1. Clone or copy the `obsidian-manuscript-build` folder to your vault's `.obsidian/plugins/` directory

2. Install dependencies:
   ```bash
   cd .obsidian/plugins/obsidian-manuscript-build
   npm install
   ```

3. Build the plugin:
   ```bash
   npm run build
   ```

4. Enable the plugin in Obsidian Settings → Community Plugins

### Manual Installation

1. Download the latest release (`main.js`, `manifest.json`, `styles.css`)
2. Create a folder: `YOUR_VAULT/.obsidian/plugins/manuscript-build/`
3. Copy the files into the folder
4. Enable the plugin in Obsidian Settings

## Usage

### Quick Start

1. Click the **document icon** in the ribbon, or use `Cmd/Ctrl+P` → "Build Manuscript: Open Build Dialog"
2. Select your source file and options
3. Click **Build**
4. View the build output in the modal

### Keyboard Shortcuts

You can assign hotkeys to the build commands in Obsidian Settings → Hotkeys:
- `Build Manuscript: Open Build Dialog`
- `Build Manuscript: Quick Build (Repeat Last)`
- `Build Manuscript: Build Current File`

### Settings

Access settings via Obsidian Settings → Manuscript Build:

| Setting | Description |
|---------|-------------|
| Python Path | Path to Python executable (`python3`, `python`, or full path) |
| Build Script Path | Path to `build.py` relative to vault root |
| Default Profile | Default output profile for new builds |
| Default Font | Default typeface for PDF builds |
| Default Font Size | Default font size for PDF builds |
| Default Citation Style | Default bibliography format |
| Show Notifications | Display build status notifications |
| Auto-open Export Folder | Open export folder after successful builds |

## Available Profiles

### General
- **Word Manuscript** (DOCX)
- **PDF Default** - Standard single-column
- **PDF Draft** - With line numbers
- **PDF Two Column** - Journal-style

### Thesis
- **PDF Thesis** - Modern thesis format
- **PDF Thesis Classic** - Traditional thesis format

### Journals
- **Nature Style** - Nature journal format
- **Cell Style** - Cell journal format

## Available Fonts

- Libertinus (Default)
- Times/TeX Gyre Termes
- Palatino/TeX Gyre Pagella
- Arial
- Helvetica-like (TeX Gyre Heros)
- Charter
- Computer Modern (LaTeX default)

## Citation Styles

Citation styles are **loaded dynamically** from `resources/citation_styles/`. Any `.csl` file you add will automatically appear in the plugin dropdown.

**To add a new citation style:**
1. Download a CSL file from [zotero.org/styles](https://www.zotero.org/styles)
2. Place it in `resources/citation_styles/`
3. Reload Obsidian or reopen the build dialog

The plugin will generate a display name from the filename (e.g., `acs-nano.csl` → "ACS Nano"). Common styles like Vancouver, Nature, Cell, etc. have pre-defined friendly names.

## Troubleshooting

### "Python not found"
- Verify Python is installed: `python3 --version`
- Update the Python Path in settings
- Use the "Test Python" button in settings

### Build fails
- Check the build output modal for error messages
- Verify Pandoc is installed: `pandoc --version`
- Ensure LaTeX is installed for PDF output
- Check that `build.py` exists at the configured path

### No markdown files shown
- Files starting with `_` are excluded
- `README.md` is excluded
- Ensure files are in the vault root

## Development

```bash
# Install dependencies
npm install

# Development mode (watch for changes)
npm run dev

# Production build
npm run build
```

## License

MIT License
