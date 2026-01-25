# Scientific Manuscript Template

Write scientific manuscripts and theses in Markdown and export to Word and PDF using a custom Obsidian plugin or a script.

## Quick Start

**Using Obsidian (recommended):**
1. Open this folder as an Obsidian vault
2. Click the **Build** icon in the left ribbon (or use Quick Build ⚡)
3. Configure options and click Build (Defaults in the plugin settings)
<img src="/figures/plugin_button.png" alt="drawing" width="500"/>

**Using the terminal in case you want to use a different editor:**
```bash
python build.py
```

Both methods support:
- Multiple output formats (Word / PDF)
- Journal-specific profiles (Nature, Cell, etc.)
- Templates/examples
- Custom fonts and citation styles

## Installation

### Required Tools
- **Python 3.6+** (to run the build script)
- **Pandoc** (document conversion)
- **pandoc-crossref** (figure/table cross-references)
- **ImageMagick** (figure conversion)
- **Tectonic** (PDF engine, lightweight alternative to TeX Live)
- **Fonts** (below)

### Platform Installation
Install Obsidian for your system and the following dependencies:

<details>
<summary>macOS</summary>

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required packages
brew install python3 pandoc pandoc-crossref imagemagick tectonic

# Install Libertinus font (default font)
brew install --cask font-libertinus
```

</details>

<details>
<summary>Linux (Debian/Ubuntu)</summary>

```bash
sudo apt update
sudo apt install python3 pandoc imagemagick fonts-linuxlibertine

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
sudo pacman -S python pandoc pandoc-crossref imagemagick tectonic otf-libertinus
```

</details>

<details>
<summary>Windows</summary>

1. Install Python from [python.org](https://www.python.org/downloads/)
2. Install Pandoc from [pandoc.org](https://pandoc.org/installing.html)
3. Install pandoc-crossref from [GitHub releases](https://github.com/lierdakil/pandoc-crossref/releases)
4. Install ImageMagick from [imagemagick.org](https://imagemagick.org/script/download.php#windows)
5. Install Tectonic from [tectonic-typesetting.github.io](https://tectonic-typesetting.github.io/install.html)
6. Download and install Libertinus font from [GitHub releases](https://github.com/alerque/libertinus/releases)

</details>

### Font Installation

<details>
<summary>Libertinus (Default)</summary>

- **macOS:** `brew install --cask font-libertinus`
- **Linux (Debian/Ubuntu):** `sudo apt install fonts-linuxlibertine`
- **Linux (Arch):** `sudo pacman -S otf-libertinus`
- **Linux (Other):** Install from [GitHub releases](https://github.com/alerque/libertinus/releases)
- **Windows:** Download from [GitHub releases](https://github.com/alerque/libertinus/releases)

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

Download the repository. The folder `obsidian-manuscript-build` is for development and can be deleted. The included `.obsidian` folder contains all plugins and settings, and a custom AnuPpuccin theme. The **Manuscript Build Plugin** should work out of the box. You might want to update the path to `resources/ferences.json`.

### Using the Build Plugin

The custom build plugin is included in this repository. Two ribbon icons are available in the left sidebar:
- **Build** (hammer icon) - Opens the build dialog with all options
- **Quick Build** (lightning icon) - Repeats last build with confirmation

**Build options include:**
- Source file and frontmatter selection
- Output profile (PDF, Word, journal-specific)
- Font and font size (PDF only)
- Citation style
- SI formatting options

**Settings** (Settings → Manuscript Build):
- Configure default profile, font, and citation style
- Add new citation styles via the Settings panel

### Adding Citation Styles

Citation styles are stored in `resources/citation_styles/`. To add new styles:
1. Visit [zotero.org/styles](https://www.zotero.org/styles) (or use the button in Settings)
2. Download the `.csl` file
3. Place it in `resources/citation_styles/` (you can use "Open Folder" in the plugin settings)
4. Reopen the build dialog - the new style appears automatically

### Rebuilding the Plugin (Development)

If you modify the plugin source code:
```bash
cd obsidian-manuscript-build
npm install
npm run build
```
Then copy `main.js`, `manifest.json`, and `styles.css` to `.obsidian/plugins/manuscript-build/`.

### Other Recommended Plugins
- **Zotero Integration** - Insert citations from Zotero
- **Pandoc Reference List** - View formatted references
- **Editing Toolbar** - Text formatting
- **Commentator** - Track Changes
- **LanguageTool Integration** - Improved spell check
- **Git** - Version control

### Configuration

**Zotero Integration:**
- Citation Format: Set e.g. as `Cite` with **Pandoc** output format
- Set hotkey (e.g., `Alt+Z`) for quick citation insertion

**Pandoc Reference List:**
- Set path to: `your/path/to/resources/references.json`
- Enable "Show citations in sidebar"

**Terminal:**
- Open integrated terminal from ribbon icon
- Run: `python build.py`

## Zotero Setup (References)

1. Install Zotero and then the **Better BibTeX** plugin from [GitHub](https://github.com/retorquere/zotero-better-bibtex/releases)
2. Set up auto-export:
   - Right-click collection → Export Collection
   - Format: **BetterBibTeX JSON**
   - ✓ **Keep updated**
   - Save as `resources/references.json`

**Citation syntax:** `[@smith2023]` or `[@smith2023; @jones2024]` or use the Zotero Integraion plugin 

## Features and Structure

### Working Files

**Manuscripts** (use with `pdf-default`, `pdf-draft`, `pdf-nature`, `pdf-cell`, or `docx-manuscript`):
- **`01_frontmatter.md`** - Title page with authors and affiliations
- **`02_maintext.md`** - Main manuscript content (template)
- **`03_supp_info.md`** - Supporting Information (optional)

**Thesis** (use with `pdf-thesis` or `pdf-thesis-classic`):
- **`05_example_thesis.md`** - Complete thesis template with custom title page

**Notes & Scripts** (use with `pdf-notes`):
- **`06_example_notes_technical.md`** - Technical docs, API references, tutorials
- **`07_example_notes_narrative.md`** - Lecture notes, essays (includes figures, citations, markdown features)

**Resources:**
- **`figures/`** - Place all figures here (PDF format recommended)

### Build System

The Obsidian plugin is the recommended way to build documents (see [Obsidian Setup](#obsidian-setup)).

**Alternative: Command-line script**

The `build.py` script can be used independently without Obsidian:
```bash
python build.py           # Interactive mode
python build.py --last    # Repeat last build
python build.py --help    # Show all options
```

**Script menu options:**
1. Build Document - Full guided setup
2. Quick Build - Repeat last build with confirmation  
3. Configure Defaults - Set font, size, citation style (downloads styles from Zotero)

### Output Formats
- **Word Document** - For journal submissions
- **PDF Profiles:**
  - Default - Clean single-column layout
  - Draft - Double-spaced with line numbers
  - Two-Column - Compact two-column layout
  - Notes & Scripts - Modern digital-friendly style for teaching materials
  - Thesis - Formal thesis format
  - Classic Thesis - Elegant book-style with Palatino
  - Nature/Cell - Journal-specific formats

## Writing Guide

### Figures
- Use **PDF format** (auto-converted to PNG for Word)
- You can drag&drop the file and adjust
- Reference with `**@Fig:label**`
- Caption goes below the figure

```markdown
![**Figure Title.** Legend text.](figures/image.pdf){#fig:label}
```

### Tables
- Caption goes **above** the table
- Reference with `**@Tbl:label**`

```markdown
Table: **Table Title.** Description. {#tbl:label}

| Column A | Column B |
|----------|----------|
| Value 1  | Value 2  |
```

### Cross-References
- Figures: `**@Fig:results**` → "Figure 1"
- Tables: `**@Tbl:data**` → "Table 1"
- Citations: `[@smith2023]` → "(Smith 2023)"

### Highlighting and Colored Text

**Yellow Background Highlighting:**
- Use Obsidian-style syntax: `==highlighted text==`
- Works in both PDF and DOCX outputs (yellow background by default)

```markdown
The results show ==significant improvement== in all metrics.
```

**Colored Text (Red, Blue, etc.):**
- Use HTML font tags from Obsidian's editing toolbar (works in **PDF only**):

```markdown
This is <font color="red">red text</font>.
This is <font color="#0000ff">blue text</font>.
This is <font color="green">green text</font>.
```

**Note:** Colored text works in PDF but **not in DOCX** due to Pandoc limitations. For DOCX, you can manually apply colors in Word after generating the document, or use the highlighting feature (`==text==`) which works in both formats.

### Supporting Information
- Use same syntax as main text
- Automatically numbered as S1, S2, etc.
- Build with "Both" option or select "Supporting Information"

### Full-width Elements (Two-Column Layout)

For two-column profiles, use raw LaTeX for full-width figures and tables:

```latex
\begin{figure*}[t]
\centering
\includegraphics[width=0.9\textwidth]{figures/image.pdf}
\caption{**Figure Title.** Legend text.}
\label{fig:label}
\end{figure*}
```

```latex
\begin{table*}[t]
\centering
\caption{**Table Title.** Description.}
\label{tbl:label}
\begin{tabular}{ll}
Column A & Column B \\
\hline
Value 1  & Value 2
\end{tabular}
\end{table*}
```

## Customization

### Configure Defaults

The manuscript build plugin and the build script have a "Configure Defaults" option to set:
- **Font** (default: Libertinus)
- **Font Size** (default: 11pt)
- **Citation Style** (default: Vancouver)

Once configured, these settings are used for all builds unless you reconfigure them.

### PDF Customization

The template uses **profiles** (YAML files in `resources/profiles/`) to define output formats:
- `_base.yaml` - Shared defaults inherited by all profiles
- `pdf-*.yaml` - PDF-specific profiles
- `docx-manuscript.yaml` - Word document profile

**Create custom PDF profiles:**
1. Copy `pdf-default.yaml` to `pdf-my-journal.yaml`
2. Edit settings (fonts, margins, spacing)
3. The build script will automatically show it in the profile list

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

---

**Output:** All documents are created in the `export/` folder.
Templates: See `example/` folder.
