# Scientific Manuscript Template

Write scientific manuscripts and theses in Markdown and export to Word and PDF using a custom Obsidian plugin or a script.

## Quick Start

**Using Obsidian (recommended):**
1. Open this folder as an Obsidian vault
2. Click the **Build** icon in the left ribbon
3. Configure options and click Build (Defaults in the plugin settings)
<img src="/figures/plugin_button.jpg" alt="drawing" width="500"/>

**Using the terminal in case you want to use a different editor:**
```bash
python build.py
```

Both methods support:
- Multiple output formats (Word / PDF)
- Journal-specific profiles (Nature, Cell, etc.)
- Templates/examples
- Custom fonts and citation styles

**Output:** All documents are created in the `export/` folder.

**Documentation:**
- **[WRITING.md](WRITING.md)**: Complete Markdown guide with syntax basics, scientific writing features, and template-specific use cases
- **Templates**: See `examples/` folder for ready-to-use templates (manuscripts, thesis, notes)

## Installation
[Download](https://github.com/beyerh/md-manuscript/archive/refs/heads/main.zip), extract, and open this folder as an Obsidian vault
### Required Tools
- **Obsidian** (Markdown editor)
- **Python 3.7+** (to run the build script)
- **Pandoc** (document conversion)
- **pandoc-crossref** (figure/table cross-references)
- **ImageMagick** (figure conversion)
- **Tectonic** (PDF engine, lightweight alternative to TeX Live)
- **Fonts** (below)
- **Zotero** with **Better BibTeX** plugin (for references, see extra chapter below)

### Platform Installation
Install [Obsidian](https://www.obsidian.md/) for your system and the required dependencies:

<details>
<summary>macOS</summary>

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required packages
brew install python3 pandoc pandoc-crossref imagemagick tectonic git

# Install Libertinus default font (or use install script below)
brew install --cask font-libertinus

# Install Obsidian (or download from https://obsidian.md/)
brew install --cask obsidian
```

</details>

<details>
<summary>Linux (Debian/Ubuntu)</summary>

```bash
sudo apt update
sudo apt install python3 pandoc imagemagick fonts-linuxlibertine git

# Install pandoc-crossref from GitHub (not available in apt)
wget https://github.com/lierdakil/pandoc-crossref/releases/download/v0.3.18.0/pandoc-crossref-Linux.tar.xz
tar -xf pandoc-crossref-Linux.tar.xz
sudo mv pandoc-crossref /usr/local/bin/
sudo chmod +x /usr/local/bin/pandoc-crossref

# Install Tectonic: https://tectonic-typesetting.github.io/install.html
```

</details>

<details>
<summary>Linux (Arch)</summary>

```bash
sudo pacman -S python pandoc pandoc-crossref imagemagick tectonic otf-libertinus git
```

</details>

<details>
<summary>Windows</summary>

We use **Scoop** to manage all dependencies.

### Install Scoop
If you don't have Scoop, open **PowerShell** and run:

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex
```
If you get an error regarding Administrator install, use:
```powershell
iex "& {$(irm get.scoop.sh)} -RunAsAdmin"
```

### Install Dependencies
Add bucket:
```powershell
scoop bucket add extras
```
Install packages:
```powershell
scoop install pandoc tectonic git python obsidian pandoc-crossref
```
</details>

### Font Installation

**Automated Installation (Recommended):**

The script provides an interactive wizard for easy font management on **Windows, macOS, and Linux**:
```bash
python resources/install-fonts.py
```

**Manual Installation:**

Alternatively, install fonts manually:

<details>
<summary>Libertinus (Default)</summary>

- **macOS:** `brew install --cask font-libertinus`
- **Linux (Debian/Ubuntu):** `sudo apt install fonts-linuxlibertine`
- **Linux (Arch):** `sudo pacman -S otf-libertinus`
- **Linux (Other):** Install from [GitHub releases](https://github.com/alerque/libertinus/releases)
- **Windows:** Download from [GitHub releases](https://github.com/alerque/libertinus/releases)

</details>

<details>
<summary>Inter (Notes profile default)</summary>

- **macOS:** `brew install --cask font-inter`
- **Linux (Debian/Ubuntu):** Install from [Inter releases](https://github.com/rsms/inter/releases)
- **Linux (Arch):** `sudo pacman -S inter-font`
- **Windows:** Install from [Inter releases](https://github.com/rsms/inter/releases)

</details>

<details>
<summary>IBM Plex (Sans/Mono)</summary>

- **macOS:** `brew install --cask font-ibm-plex-sans font-ibm-plex-mono`
- **Linux (Debian/Ubuntu):** Install from [IBM Plex releases](https://github.com/IBM/plex/releases)
- **Linux (Arch):** `sudo pacman -S otf-ibm-plex`
- **Windows:** Install from [IBM Plex releases](https://github.com/IBM/plex/releases)

</details>

<details>
<summary>Switzer</summary>

- **macOS:** Install manually (not available via Homebrew):
  1. Download from [Fontshare](https://www.fontshare.com/fonts/switzer)
  2. Install the `.otf` files (Font Book)
- **Linux:** Install from [Fontshare](https://www.fontshare.com/fonts/switzer)
- **Windows:** Install from [Fontshare](https://www.fontshare.com/fonts/switzer)

</details>

<details>
<summary>TeX Gyre Pagella (Classic Thesis profile)</summary>

- **macOS:** `brew install --cask font-tex-gyre-pagella`
- **Linux (Debian/Ubuntu):** `sudo apt install fonts-texgyre`
- **Linux (Arch):** `sudo pacman -S tex-gyre-fonts`
- **Linux (Other):** Install from [TeX Gyre project](http://www.gust.org.pl/projects/e-foundry/tex-gyre/)
- **Windows:** Download from [TeX Gyre project](http://www.gust.org.pl/projects/e-foundry/tex-gyre/)

</details>

<details>
<summary>Arial/Helvetica</summary>

- **macOS:** Pre-installed
- **Linux (Debian/Ubuntu):** Install `msttcorefonts` package or `ttf-liberation` for alternatives
- **Linux (Arch):** `sudo pacman -S ttf-liberation` (metric-compatible alternatives)
- **Windows:** Pre-installed

</details>

<details>
<summary>Charter</summary>

- **macOS:** Install from [XCharter project](https://github.com/khaledhosny/xcharter)
- **Linux (Arch):** `ttf-bitstream-charter` (AUR) or install from [XCharter project](https://github.com/khaledhosny/xcharter)
- **Linux (Other):** Install from [XCharter project](https://github.com/khaledhosny/xcharter)
- **Windows:** Install from [XCharter project](https://github.com/khaledhosny/xcharter)

</details>

<details>
<summary>Latin Modern (Computer Modern alternative)</summary>

- **macOS:** Included with most TeX distributions
- **Linux (Arch):** `sudo pacman -S otf-latin-modern` or included with TeX distributions
- **Linux (Other):** Included with most TeX distributions
- **Windows:** Included with MiKTeX/TeX Live

</details>

## Obsidian Setup

The folder `obsidian-manuscript-build` is for development and can be deleted. The included hidden `.obsidian` folder contains all plugins and settings, and a custom AnuPpuccin theme. The **Manuscript Build Plugin** should work out of the box. You might want to update the path to `resources/references.json` in the `pandoc-crossref` plugin settings.

### Using the Build Plugin

The **Build Manuscript** button is available in the left ribbon as a button in Obsidian. You can also access it via `Cmd/Ctrl + P`. Alternatively, use `python build.py` in a terminal from the plugin folder.

### Adding Citation Styles

Citation styles are stored in `resources/citation_styles/`. Add new styles in the plugin settings:
1. Visit [zotero.org/styles](https://www.zotero.org/styles) (or use the button in Settings)
2. Download the `.csl` file
3. Place it in `resources/citation_styles/` (you can use "Open Folder" in the plugin settings)
4. Reopen the build dialog - the new style appears automatically

## Configuration
***
**The plugins are included in this repository and pre-configured. However, you still have to install and configure Zotero***

- **Zotero Integration** - Insert citations from Zotero
- **Pandoc Reference List** - View formatted references
- **Editing Toolbar** - Text formatting
- **Commentator** - Track Changes
- **LanguageTool Integration** - Improved spell check
- **Git** - Version control

**Zotero Integration:**
- Citation Format: Set e.g. as `Cite` with **Pandoc** output format
- Set hotkey (e.g., `Alt+Z`) for quick citation insertion

**Pandoc Reference List:**
- Set path to: `your/path/to/resources/references.json`
- Enable "Show citations in sidebar"

**Terminal:**
- Open integrated terminal from ribbon icon
- Here you can run: `python build.py`

## Zotero Setup (References)

1. Install **Zotero** and then the **Better BibTeX** plugin from [GitHub](https://github.com/retorquere/zotero-better-bibtex/releases)
2. Set up auto-export:
   - Right-click collection → Export Collection
   - Format: **BetterBibTeX JSON**
   - ✓ **Keep updated**
   - Save as `resources/references.json`

**Citation syntax:** `[@smith2023]` or `[@smith2023; @jones2024]` or use the Zotero Integraion plugin 

### Configure Defaults

The manuscript build plugin and the build script have a "Configure Defaults" option to set:
- **Font** (default: Libertinus)
- **Font Size** (default: 11pt)
- **Citation Style** (default: Vancouver)

Once configured, these settings are used for all builds unless you reconfigure them.

### Word Customization

**Using the included template:**
1. Open `resources/reference_doc.docx` in Word
2. Modify styles (Normal, Heading 1-3, Figure Caption, Table Caption)
3. Save changes

**Generating a fresh reference document:**

**Option 1: From the Pandoc default**
```bash
pandoc --print-default-data-file reference.docx > custom-reference.docx
```
Then:
1. Open `custom-reference.docx` in Word
2. **Important:** Create a `FrontMatter` style for author information
3. Adjust other styles as needed (Normal, Heading 1-3, Figure Caption, Table Caption)
4. Save as `resources/reference_doc.docx`

**Option 2: From existing output**
1. Build a document once with the provided `reference_doc.docx`
2. Open the generated Word document
3. Format all styles as desired (Normal, Heading 1-3, Figure Caption, Table Caption)
4. **Important:** Create a `FrontMatter` style for author information
5. Save as `resources/reference_doc.docx`

### PDF Customization

The template uses **profiles** (YAML files in `resources/profiles/`) to define output formats:
- `_base.yaml` - Shared defaults inherited by all profiles
- `pdf-*.yaml` - PDF-specific profiles
- `docx-manuscript.yaml` - Word document profile

### Portable LaTeX Export

You can export LaTeX (`.tex`) from any PDF profile in three modes.

**1) LaTeX Source (profile exact)**

Exports a `.tex` file that aims to reproduce the PDF output of the selected profile as closely as possible (including profile fonts and other LaTeX variables).

```bash
python build.py --source=01_maintext.md --profile=pdf-nature --tex-source
```

**2) Portable LaTeX**

Exports a `.tex` file intended to be portable across LaTeX environments for journal submission workflows.

- The output is written to `export/<name>.tex`.
- For portability, the exporter strips profile font settings (`mainfont`, `sansfont`, `monofont`) so the `.tex` does not depend on system fonts.

```bash
python build.py --source=01_maintext.md --profile=pdf-nature --tex
```

**3) LaTeX Body-only (for journal templates)**

Exports only the content between `\begin{document}` and `\end{document}`. This is useful if a journal provides a class/template and you want to paste the manuscript content into their `.tex`.

```bash
python build.py --source=01_maintext.md --profile=pdf-nature --tex-body
```

**Compiling the exported `.tex`:**
- Recommended (typical journal toolchain): `pdflatex` / `latexmk`.
- If you use `tectonic`, it should compile as well; any reproducibility warnings about system font paths indicate local font discovery and do not affect journal compilation.

**Create custom PDF profiles:**
1. Copy `pdf-default.yaml` to `pdf-my-journal.yaml`
2. Edit settings (fonts, margins, spacing)
3. The build script will automatically show it in the profile list

---
## Development
If you modify the plugin source code:
```bash
cd obsidian-manuscript-build
npm install
npm run build
```

Then copy `main.js`, `manifest.json`, and `styles.css` to `.obsidian/plugins/manuscript-build/`.

