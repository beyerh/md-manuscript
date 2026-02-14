# Scientific Manuscript Template

Write scientific manuscripts and theses in Markdown and export to PDF, Word, LaTeX, and web-ready Markdown using a custom Obsidian plugin or a script.

## Quick Start

**Option 1: Obsidian (Easiest)**
1. Download and extract this folder
2. Open in Obsidian
3. Click the **Build** button in the left sidebar
4. Choose your document type and click **Build**

<img src="/figures/plugin_button.jpg" alt="drawing" width="500"/>


**Option 2: Terminal**
```bash
python .obsidian/plugins/obsidian-md-manuscript/resources/build.py
```

Both methods support:
- Multiple output formats (PDF, Word, LaTeX, Flattened Markdown)
- Style/journal-specific profiles
- Templates/examples
- Custom fonts, citation styles, formatting options
- Web-ready markdown export for digital gardens (Vercel, GitHub Pages, etc.)

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

The plugin provides an interactive wizard for easy font management on **Windows, macOS, and Linux**. In the plugin settings, click "Copy Command" next to "Install Fonts" and paste it in your terminal.

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

The folder `obsidian-manuscript-build` is for development and can be deleted. The included hidden `.obsidian` folder contains all plugins and settings, including the **md-markdown** plugin, and a custom AnuPpuccin theme. The plugin should work out of the box. The internal build scripts automatically adjust paths, assuming the repository root is the vault root.

### Using the Build Plugin

The **Build Manuscript** button is available in the left ribbon as a button in Obsidian. You can also access it via `Cmd/Ctrl + P`.

### Adding Citation Styles

Citation styles are handled automatically by the plugin. Use the "Open Styles Folder" button in the plugin settings to manually add `.csl` files to the plugin's `.obsidian/plugins/obsidian-md-manuscript/resources/citation_styles/` folder.
### Installation Actions

The plugin settings now include two buttons under "Actions" to help with external dependencies:
1. **Install CSS Snippets**: Copies the necessary figure/table CSS files to `.obsidian/snippets/`. Remember to enable them in `Settings -> Appearance -> CSS Snippets`.
2. **Install Fonts**: Copies the necessary terminal command to run `python resources/install-fonts.py` to your clipboard, as this interactive script must be run outside of Obsidian.

## Configuration
***
**The plugins are included in this repository and pre-configured. However, you still have to install and configure Zotero***.

**Selected included plugins in this vault:**

- **Scientific Manuscript** - md-manuscript custom plugin (included)
- **Zotero Integration** - Insert citations from Zotero
- **Pandoc Reference List** - View formatted references
- **Editing Toolbar** - Text formatting
- **Templater** - Insert tables, figures, etc.
- **Commentator** - Track Changes
- **Harper** - AI-free and local spell/grammar checker. You can consider LanguageTool as an non-local alternative that supports many languages.
- **Style Settings** - Allows the included customized theme derived from the [template](https://www.linkingyourthinking.com/thank-you/lyt-anuppucin-style-settings) of Nick Milo
- **Git** - Version control
- **Sort & Permute lines** - Sort and permute lines in whole text or selection
- **Terminal** - open a terminal in obsidian (e.g. to execute scripts/commands)

**Zotero Integration:**
- In the plugin settings, Citation Format: Set e.g. as `Cite` with **Pandoc** output format
- Set hotkey (e.g., `Alt+Z`) or use `Cmd/Ctrl + P` for quick citation insertion

**Pandoc Reference List:**
- Set path to: `your/path/to/references.json` (now in root directory)
- Enable "Show citations in sidebar"

## Zotero Setup (References)

1. Install **Zotero** and then the **Better BibTeX** plugin from [GitHub](https://github.com/retorquere/zotero-better-bibtex/releases)
2. Set up auto-export:
   - Right-click collection → Export Collection
   - Format: **Better CSL JSON**
   - ✓ **Keep updated**
   - Save as `references.json` in the vault root directory

**Citation syntax:** `[@smith2023]` or `[@smith2023; @jones2024]` or use the Zotero Integraion plugin 

### Word Customization

**Using the included template:**
1. Open `.obsidian/plugins/obsidian-md-manuscript/resources/reference_doc.docx` in Word
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
4. Save as `.obsidian/plugins/obsidian-md-manuscript/resources/reference_doc.docx`

**Option 2: From existing output**
1. Build a document once with the provided `reference_doc.docx`
2. Format all styles as desired (Normal, Heading 1-3, Figure Caption, Table Caption)
3. Save as `.obsidian/plugins/obsidian-md-manuscript/resources/reference_doc.docx`

### PDF Customization

The template uses **profiles** (YAML files in `.obsidian/plugins/obsidian-md-manuscript/resources/profiles/`) to define output formats:
- `_base.yaml` - Shared defaults inherited by all profiles
- `pdf-*.yaml` - PDF-specific profiles
- `docx-manuscript.yaml` - Word document profile

**Create custom PDF profiles:**
1. Copy `.obsidian/plugins/obsidian-md-manuscript/resources/profiles/pdf-default.yaml` to a new file in the same directory, e.g., `pdf-my-journal.yaml`
2. Edit settings (fonts, margins, spacing)
3. The build script will automatically show it in the profile list

### Portable LaTeX Export

You can export LaTeX (`.tex`) from any PDF profile in three modes.

**1) LaTeX Source (profile exact)**

Exports a `.tex` file that aims to reproduce the PDF output of the selected profile as closely as possible (including profile fonts and other LaTeX variables).

**2) Portable LaTeX**

Exports a `.tex` file intended to be portable across LaTeX environments for journal submission workflows.

- The output is written to `export/<name>.tex`.
- For portability, the exporter strips profile font settings (`mainfont`, `sansfont`, `monofont`) so the `.tex` does not depend on system fonts.

**3) LaTeX Body-only (for journal templates)**

Exports only the content between `\begin{document}` and `\end{document}`. This is useful if a journal provides a class/template and you want to paste the manuscript content into their `.tex`.

**Test-Compiling the exported `.tex`:**
- Recommended (typical journal toolchain): `pdflatex` / `latexmk`.
- If you use `tectonic`, it should compile as well; any reproducibility warnings about system font paths indicate local font discovery and do not affect journal compilation.

### Flattened Markdown Export (Digital Gardens)

Export web-ready markdown for digital gardens, static site generators (Vercel, GitHub Pages, etc.), or content management systems.

**Features:**
- Cross-references resolved to plain text (e.g., "**Figure 1**", "**Table 1**")
- Citations rendered with bibliography in selected style
- Figures/tables converted to standard markdown format
- PDF figures converted to PNG/WebP/JPEG with white or transparent background
- LaTeX-specific code removed
- Math equations preserved (`$...$` and `$$...$$`)
- Output includes both markdown file and converted figures in `export/figures/`


**Output:**
- `export/<filename>_flat.md` - Web-ready markdown file
- `export/figures/` - Converted figures (PNG/WebP/JPEG)

### Web Publishing (Digital Garden)

For publishing your manuscript as a digital garden, you can use the **Digital Garden** plugin for Obsidian. This allows you to publish your notes directly to the web, hosting them on Vercel or GitHub Pages.

**Resources:**
- **Documentation:** [dg-docs.ole.dev](https://dg-docs.ole.dev/)
- **Plugin Repository:** [oleeskild/digitalgarden](https://github.com/oleeskild/digitalgarden)
- **GitHub Pages Template:** [foxblock/digitalgarden_gh-pages](https://github.com/foxblock/digitalgarden_gh-pages) (allows publishing to GitHub Pages instead of Vercel)

---
## Development
See `obsidian-manuscript-build/README.md`
