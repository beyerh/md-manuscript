# Scientific Manuscript Template (Markdown → PDF & DOCX)

Write scientific manuscripts in Markdown with Obsidianand export to Word and PDF documents using a build script.

**Key Features:**
- Unified configuration for consistent output
- Automatic cross-referencing for figures, tables, and citations
- Supporting Information with proper numbering (Figure S1, Table S1)
- Optional unified bibliography (include SI references in main text)
- Interactive build script with wizard

---

## Prerequisites

### Arch Linux

```bash
# Install Pandoc, pandoc-crossref, ImageMagick, Tectonic, and Linux Libertine fonts
sudo pacman -S pandoc pandoc-crossref imagemagick tectonic ttf-linux-libertine
```

### macOS

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required packages
brew install pandoc pandoc-crossref imagemagick tectonic

# Download and install Linux Libertine fonts from https://sourceforge.net/projects/linuxlibertine/
```

### Windows

1. **Install Pandoc:** Download from [pandoc.org](https://pandoc.org/installing.html)
2. **Install pandoc-crossref:** Download from [GitHub releases](https://github.com/lierdakil/pandoc-crossref/releases)
3. **Install ImageMagick:** Download from [imagemagick.org](https://imagemagick.org/script/download.php#windows)
4. **Install Tectonic:** Download from [tectonic-typesetting.github.io](https://tectonic-typesetting.github.io/install.html)
5. **Install Linux Libertine fonts:** Download from [sourceforge.net](https://sourceforge.net/projects/linuxlibertine/)

**Note:** On Windows, use Git Bash, WSL, or PowerShell to run the build script

---

## Project Structure

```
├── 00_frontmatter.md       # Common frontmatter (authors, affiliations)
├── 01_maintext.md          # Main manuscript content
├── 02_supp_info.md         # Supporting Information content
├── build.sh                # Build script (interactive wizard)
├── export/                 # Output folder (created automatically)
├── figures/                # Images (PDF format recommended)
└── resources/
    ├── config.yaml         # Pandoc configuration
    ├── references.json     # Zotero bibliography (auto-updated)
    ├── citation_style.csl  # Citation style file
    ├── reference_doc.docx  # Word template
    └── pdf2png.lua         # Figure conversion filter
```

**Frontmatter Workflow:** The build script automatically merges `00_frontmatter.md` with both `01_maintext.md` and `02_supp_info.md` during each build. This ensures consistent author information across both documents. You can disable this with the `--no-frontmatter` option.

**Note:** If you rename manuscript files, update the filenames at the top of `build.sh` in the `# --- Configuration ---` section.

---

## Zotero Setup (Auto-Updating References)

1. **Install Better BibTeX plugin** from [GitHub](https://github.com/retorquere/zotero-better-bibtex/releases)
2. **Setup auto-export:**
   - Right-click collection → Export Collection
   - Format: **BetterBibTeX JSON**
   - ✓ **Keep updated**
   - Save as `resources/references.json`

**Citation syntax:** `[@smith2023]` or `[@smith2023; @jones2024]`. Use Zotero plugins for automatization.

---

## Obsidian Setup

### Required Plugins
- **Terminal** - Run ./build.sh script with interactive wizard
- **Zotero Integration** - Insert citations
- **Pandoc Plugin** - PDF, DOCX export
- **Pandoc Reference List** - View formatted references

**Optional:** Editing Toolbar (text formatting), commentator (Track changes), Git (version control), languagetool (spellcheck)

### Terminal Plugin Configuration

1. Install **Terminal** plugin from Community Plugins
2. Open terminal in Obsidian (ribbon icon)
3. Run the build script: `./build.sh`
4. Follow the interactive wizard prompts

**Alternative: Direct commands** (see below)
### Zotero Integration

Settings → Zotero Integration:
- Citation Format: **Pandoc/Scrivener** (`@AuthorYear`)
- Import Format: **Better BibTeX JSON**
- Set hotkey (e.g., `Alt+Z`) for quick citation insertion

### Pandoc Reference List

Settings → Pandoc Reference List:
- Bibliography files: `full/path/to/resources/references.json`
- ✓ Show citations in sidebar

---

## Build Script Usage

### Interactive Wizard (Recommended in Obsidian)

```bash
./build.sh
```

Follow prompts to select:
1. Document type (Main text / Supporting Information)
2. Output format (PDF / DOCX)
3. Include frontmatter (default: yes)
4. Options (PDF to PNG conversion, include SI refs)

### Command-Line Arguments

```bash
./build.sh main pdf                      # Main text PDF (with frontmatter)
./build.sh main docx --png               # Main text DOCX with PNG figures
./build.sh si pdf                        # Supporting Information PDF
./build.sh main pdf --include-si-refs    # Unified bibliography
./build.sh main pdf --no-frontmatter     # Build without frontmatter
```

**Options:**
- `--png` - Convert PDF figures to PNG for Word compatibility
- `--include-si-refs` - Include SI citations in main text bibliography
- `--no-frontmatter` - Skip merging frontmatter (content files only)

**Output:** All files are created in `export/` folder

---

## Writing Guidelines

### Frontmatter Workflow (DRY Principle)

The repository uses a **single source of truth** for author information and frontmatter:

- **`00_frontmatter.md`** - Contains the complete manuscript with title, authors, affiliations, abstract, and all content
- **`01_maintext.md`** - Contains only the content (Abstract onwards, no title/authors)
- **`02_supp_info.md`** - Contains only the content (Supporting Information onwards, no title/authors)

During each build, the script automatically merges `00_frontmatter.md` with the content files:
- `00_frontmatter.md` + `01_maintext.md` → `export/01_maintext.pdf`
- `00_frontmatter.md` + `02_supp_info.md` → `export/02_supp_info.pdf`

**Benefits:**
- Update author information in one place only
- Consistent frontmatter across main text and SI
- Cleaner content files focused on writing

**To disable:** Use `--no-frontmatter` flag or answer "n" when prompted.

### Title Page (Authors & Affiliations)

```markdown
# Manuscript Title

::: {custom-style="FrontMatter"}
**Author Name**^1,2^, **Co-Author**^2^

^1^ Department, University, City, Country  
^2^ Institute, Organization
:::
```

### Figures

**Always use PDF format** - build script converts to PNG for Word automatically.

```markdown
As shown in **@Fig:results**...

![**Title.** Legend text.](figures/image.pdf){#fig:results}

Next paragraph...
```

**Important:** Empty line after figure is required.

### Tables

Caption goes **above** table. Empty line between caption and table is mandatory.

```markdown
See **@Tbl:stats** for details.

Table: **Title.** Description text. {#tbl:stats}

| Column A | Column B |
| :------- | :------- |
| Value 1  | Value 2  |
```

### Cross-References

**Within document:**
- Figures: `**@Fig:results**` → "Figure 1"
- Tables: `**@Tbl:data**` → "Table 1"
- Citations: `[@smith2023]` → "(Smith 2023)"

**Cross-document (SI from main text):**
- Use plain text: `**Figure S1**`, `**Table S1**`
- Cross-references only work within same document

---

## Supporting Information

The SI document (`02_supp_info.md`) automatically:
- Numbers figures as S1, S2, S3...
- Numbers tables as S1, S2, S3...
- Has its own bibliography

Use same syntax as main text:
```markdown
See **@Fig:s1** and **@Tbl:s1**...

![**Title.** Legend.](figures/si_image.pdf){#fig:s1}
```

### Unified Bibliography Option

Some journals require all references (main + SI) in the main text bibliography:

```bash
./build.sh main docx --png --include-si-refs
```

This automatically extracts literature citations from SI and includes them in main text bibliography.

---

## Customizing Word Template

To adapt `reference_doc.docx` for different journals:

1. **Generate base:** (fully compatible with Pandoc)
   ```bash
   pandoc -o custom_reference.docx --print-default-data-file reference.docx
   ```

2. **Edit styles in Word:**
   - Open Styles Pane (`Alt+Ctrl+Shift+S`)
   - Modify: Normal, Heading 1-3, Table Caption, Figure Caption

3. **Create FrontMatter style:**
   - New Style → Name: `FrontMatter`
   - Based on: Normal
   - Alignment: Left

4. **Save as:** `resources/reference_doc.docx`

---
## Advanced Features

### Math Equations
Inline: `$E = mc^2$`  
Display: `$$\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}$$`

### Footnotes
`Text with footnote^[This is the footnote content.]`

### Highlighting (for drafts)
`==highlighted text==` renders as yellow highlighted text.

### Definition Lists
```markdown
Term 1
:   Definition of term 1

Term 2
:   Definition of term 2
```

---