# Scientific Manuscript Template

Write scientific manuscripts in Markdown and export to Word and PDF using a  build script.

## Quick Start

```bash
python build.py
```

The interactive wizard guides you through:
- Document type (Main Text /### Supporting Information
- Use same syntax as main text
- Automatically numbered as S1, S2, etc.
- Build with `python build.py si`

## Obsidian Setup

All configuration is included in the hidden .obsidian folder, and it should all work out of the box. However, you should update the path to the `references.json` file in the settings of the Pandoc Reference List plugin.

**Details:**

### Required Plugins
- **Terminal** - Run build script with interactive wizard 
- **Zotero Integration** - Insert citations from Zotero
- **Pandoc Reference List** - View formatted references
**Recommended:**
- **Editing Toolbar** - Text formatting
- **Commentator** - Track changes
- **LanguageTool Integration** - Improved spell checking

### Configuration
**Zotero Integration:**
- Citation Format: **Pandoc/Scrivener** (`@AuthorYear`)
- Import Format: **Better BibTeX JSON**
- Set hotkey (e.g., `Alt+Z`) for quick citation insertion

**Pandoc Reference List:**
- Set path to: `your/path/to/resources/references.json`
- Enable "Show citations in sidebar"

**Terminal:**
- Open terminal from ribbon icon, select integrated terminal
- Run: `python build.py`

## Installation

### Required Tools
- **Python 3.6+** (to run the build script)
- **Pandoc** (document conversion)
- **pandoc-crossref** (figure/table cross-references)
- **ImageMagick** (figure conversion)
- **Tectonic** (PDF engine, lightweight alternative to TeX Live)

## Zotero Setup (References)

1. Install **Better BibTeX** plugin from [GitHub](https://github.com/retorquere/zotero-better-bibtex/releases)
2. Set up auto-export:
   - Right-click collection → Export Collection
   - Format: **BetterBibTeX JSON**
   - ✓ **Keep updated**
   - Save as `resources/references.json`

**Citation syntax:** `[@smith2023]` or `[@smith2023; @jones2024]`
Use the Zotero Integration plugin for automatization
### Install Commands

**macOS:**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required packages
brew install pandoc pandoc-crossref imagemagick tectonic font-libertinus`
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt install python3 pandoc pandoc-crossref imagemagick fonts-libertinus`
# Install Tectonic: https://tectonic-typesetting.github.io/install.html
```

**Linux (Arch):**
```bash
sudo pacman -S python pandoc pandoc-crossref imagemagick tectonic otf-libertinus
```

**Windows:**
1. Install Python from [python.org](https://www.python.org/downloads/)
2. Install Pandoc from [pandoc.org](https://pandoc.org/installing.html)
3. Install pandoc-crossref from [GitHub releases](https://github.com/lierdakil/pandoc-crossref/releases)
4. Install ImageMagick from [imagemagick.org](https://imagemagick.org/script/download.php#windows)
5. Install Tectonic from [tectonic-typesetting.github.io](https://tectonic-typesetting.github.io/install.html)

## Font Installation

The template supports several font presets. Install the fonts you want to use:

### Libertinus (Default)
- **macOS:** `brew install --cask font-libertinus`
- **Linux:** `sudo apt install fonts-libertinus` (Debian/Ubuntu) or install from [GitHub releases](https://github.com/alerque/libertinus/releases)
- **Windows:** Download from [GitHub releases](https://github.com/alerque/libertinus/releases)

### TeX Gyre (Times, Palatino, Helvetica)
- **macOS/Linux:** Included with most TeX distributions (TeX Live, MacTeX)
- **Windows:** Included with MiKTeX/TeX Live, or install from [TeX Gyre project](http://www.gust.org.pl/projects/e-foundry/tex-gyre/)

### Arial/Helvetica
- **macOS:** Pre-installed
- **Linux:** Install `msttcorefonts` package or use Liberation fonts as alternatives
- **Windows:** Pre-installed

### Charter
- **macOS/Linux:** Install via package manager or from [XCharter project](https://github.com/khaledhosny/xcharter)
- **Windows:** Install from [XCharter project](https://github.com/khaledhosny/xcharter)

### Latin Modern (Computer Modern alternative)
- **macOS/Linux:** Included with most TeX distributions
- **Windows:** Included with MiKTeX/TeX Live

## Advanced Usage

### Command Line
```bash
# Basic usage
python build.py main --profile=pdf-default
python build.py main --profile=docx-manuscript

# With options
python build.py main --profile=pdf-default --font=libertinus --fontsize=11pt
python build.py main --profile=pdf-default --csl=nature
python build.py main --profile=docx-manuscript --png  # Convert PDF figures to PNG
```

**Options:**
- `--profile=NAME` - Output format (pdf-default, pdf-nature, pdf-cell, docx-manuscript, etc.)
- `--font=NAME` - Font preset (libertinus, times, palatino, arial, helvetica, charter, computer-modern)
- `--fontsize=SIZE` - Font size (9pt, 10pt, 11pt, 12pt)
- `--csl=STYLE` - Citation style (nature, science, cell, apa, vancouver, or Zotero style ID)
- `--png` - Convert PDF figures to PNG for Word documents
- `--include-si-refs` - Include SI references in main bibliography
- `--no-frontmatter` - Skip merging frontmatter
- `--list` - Show all available profiles

## Output Formats

- `docx-manuscript` - Word document for submissions
- `pdf-default` - Clean single-column PDF
- `pdf-draft` - Double-spaced with line numbers for review
- `pdf-two-column` - Compact two-column layout
- `pdf-thesis` - Formal thesis format
- `pdf-nature` - Nature journal format
- `pdf-cell` - Cell Press journal format

## Writing Tips

### Figures
- Use **PDF format** (auto-converted to PNG for Word)
- Reference with `**@Fig:label**`
- Caption goes below figure

```markdown
![**Figure Title.** Legend text.](figures/image.pdf){#fig:label}
```

### Tables
- Caption goes **above** table
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

### Two-Column Layouts (Full-width elements)

For two-column profiles (`pdf-two-column`), use raw LaTeX for full-width figures and tables:

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

**Notes:**
- Use `figure*` and `table*` environments for full-width
- Standard markdown figures/tables work but appear in single-column width
- Reference with `**@Fig:label**` and `**@Tbl:label**` as usual

## Project Structure

```
├── 00_frontmatter.md       # Title, authors, affiliations
├── 01_maintext.md          # Main manuscript content
├── 02_supp_info.md         # Supporting Information
├── build.py                # Build script
├── figures/                # Images (PDF format recommended)
├── export/                 # Generated documents
└── resources/
    ├── profiles/           # Output format settings
    ├── citation_styles/    # Downloaded citation styles
    ├── citation_style.csl  # Default citation style
    └── references.json     # Zotero bibliography
```

## Advanced Features

- **Math equations:** `$E = mc^2$` (inline) or `$$...$$` (display)
- **Footnotes:** `Text with footnote^[Footnote content.]`
- **Highlighting:** `==highlighted text==` (yellow background)
- **Custom profiles:** Edit YAML files in `resources/profiles/`

## Citation Styles

Built-in styles: `nature`, `science`, `cell`, `plos`, `pnas`, `apa`, `vancouver`, `chicago`

Download additional styles from [zotero.org/styles](https://www.zotero.org/styles) and use with `--csl=style-id`.

---

**Output:** All documents are created in the `export/` folder.
