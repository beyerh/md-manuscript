# Scientific Manuscript Template

Write scientific manuscripts in Markdown and export to Word and PDF using a build script.

## Quick Start

```bash
python build.py
```

The interactive wizard guides you through:
- Document type (Main Text / Supporting Information / Both)
- Output format (Word / PDF)
- Journal-specific formats
- Font and citation style options

## Installation

### Required Tools
- **Python 3.6+** (to run the build script)
- **Pandoc** (document conversion)
- **pandoc-crossref** (figure/table cross-references)
- **ImageMagick** (figure conversion)
- **Tectonic** (PDF engine, lightweight alternative to TeX Live)

### Platform Installation

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
sudo apt install python3 pandoc pandoc-crossref imagemagick fonts-libertinus

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
- **Linux:** `sudo apt install fonts-libertinus` (Debian/Ubuntu) or install from [GitHub releases](https://github.com/alerque/libertinus/releases)
- **Windows:** Download from [GitHub releases](https://github.com/alerque/libertinus/releases)

</details>

<details>
<summary>TeX Gyre (Times, Palatino, Helvetica)</summary>

- **macOS/Linux:** Included with most TeX distributions (TeX Live, MacTeX)
- **Windows:** Included with MiKTeX/TeX Live, or install from [TeX Gyre project](http://www.gust.org.pl/projects/e-foundry/tex-gyre/)

</details>

<details>
<summary>Arial/Helvetica</summary>

- **macOS:** Pre-installed
- **Linux:** Install `msttcorefonts` package or use Liberation fonts as alternatives
- **Windows:** Pre-installed

</details>

<details>
<summary>Charter</summary>

- **macOS/Linux:** Install via package manager or from [XCharter project](https://github.com/khaledhosny/xcharter)
- **Windows:** Install from [XCharter project](https://github.com/khaledhosny/xcharter)

</details>

<details>
<summary>Latin Modern (Computer Modern alternative)</summary>

- **macOS/Linux:** Included with most TeX distributions
- **Windows:** Included with MiKTeX/TeX Live

</details>

## Obsidian Setup

The included hidded `.obsidian` folder contains all settings and plugins and should work out of the box. Just adjust the path to `references.json` in the Pandoc Reference List plugin.
### Details on Required Plugins
- **Terminal** - Run build script with interactive wizard
- **Zotero Integration** - Insert citations from Zotero
- **Pandoc Reference List** - View formatted references
Recommended: **Editing Toolbar** (text formatting), **Commentator** (Track Changes), **LanguageTool Integration** (improved spell check), **Git** (version control)

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
- **`00_frontmatter.md`** - Title, authors, affiliations, abstract
- **`01_maintext.md`** - Main manuscript content
- **`02_supp_info.md`** - Supporting Information (optional)
- **`figures/`** - Place all figures here (PDF format)

### Build System
- **`build.py`** - Interactive build script
- **Main Menu Options:**
  1. Build Document - Full guided setup
  2. Quick Build - Repeat last build with confirmation
  3. Configure Defaults - Set font, size, citation style

### Output Formats
- **Word Document** - For journal submissions
- **PDF Profiles:**
  - Default - Clean single-column
  - Draft - Double-spaced with line numbers
  - Two-Column - Compact layout
  - Thesis - Formal thesis format
  - Nature/Cell - Journal-specific formats

## Writing Guide

### Figures
- Use **PDF format** (auto-converted to PNG for Word)
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

The build script has a "Configure Defaults" option to set:
- **Font** (default: Libertinus)
- **Font Size** (default: 11pt)
- **Citation Style** (default: Vancouver)

Once configured, these settings are used for all builds unless you reconfigure them.

### Citation Styles

Built-in citation styles:
- ACS Synthetic Biology, Angewandte Chemie, APA 7th Edition
- Cell, Chicago Author-Date, Nature
- Nucleic Acids Research, PLOS, PNAS, Science, Vancouver

**Download additional styles:** Find styles at [zotero.org/styles](https://www.zotero.org/styles)

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

**Option 1: From pandoc default**
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
