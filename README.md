# Scientific Paper Template (Markdown -> Word & PDF)

This project provides a unified workflow for writing scientific manuscripts in Markdown. It uses a **shared configuration file** (`config.yaml`) to ensure identical output whether you export from **Obsidian** (supporting Track Changes), **Zettlr** (simpler workflow), or any other editor and the **Terminal**.

It generates:
1.  **Submission-Ready Word Doc (`.docx`):** Using a reference *.docx document with formatted styles.
2.  **Review PDF (`.pdf`):** LaTeX rendered professional PDF.

---

## 1. Prerequisites (Arch Linux)

You must install Pandoc, the cross-reference filter, the LaTeX environment, and ImageMagick (for figure conversion).

```bash
# 1. Install Pandoc, Cross-ref, and ImageMagick (Required for PNG conversion)
sudo pacman -S pandoc pandoc-crossref imagemagick

# 2a. Install a minimal LaTeX (Required for PDF)
# Note: You can also use 'tectonic' if you prefer a smaller install.
sudo pacman -S texlive-basic texlive-latexextra texlive-fontsrecommended texlive-xetex

# 2b. Alternatively, install full LaTeX
# sudo pacman -S texlive-meta

# 3. Install Fonts (Crucial for PDF export)
sudo pacman -S ttf-linux-libertine
```

---

## 2. Project Structure

Ensure your folder contains these files:

* `template.md`: Your manuscript file.
* `references.json`: Exported from Zotero (BetterBibTeX).
* `citation_style.csl`: The journal style file.
* `reference_doc.docx`: The Word styling template.
* `config.yaml`: The master configuration file (fonts, margins, citations).
* `build.sh`: The automation script (Wizard & Build logic).
* `pdf2png.lua`: Helper script to swap PDF images for PNGs in Word.
* `figures/`: Folder for images (PDFs recommended for source).

---

## 3. Zotero Setup (References)

To keep your `references.json` file automatically updated, you must use Zotero with the **Better BibTeX** plugin.

1.  **Install Better BibTeX (BBT):**
    * Download the latest `.xpi` file from the [Better BibTeX GitHub](https://github.com/retorquere/zotero-better-bibtex/releases).
    * In Zotero, go to **Tools -> Add-ons**, click the gear icon, and "Install Add-on From File".
2.  **Set Citation Key Format:**
    * Go to **Edit -> Settings -> Better BibTeX**.
    * Set the "Citation key formula" to: `auth.lower + year` (e.g., `smith2023`).
3.  **Setup Auto-Export:**
    * Right-click your project collection in the left sidebar -> **Export Collection**.
    * Format: **BetterBibTeX JSON**.
    * Check **Keep updated** (This is crucial!).
    * Save the file as `references.json` inside your project folder.
4.  **How to Cite:**
    * In your Markdown file, use the citation key: `text text text [@smith2023]`.
    * For multiple citations: `[@smith2023; @jones2024]`. 
    * Juse Zotero plugins for automatic insertions.

---

### A. Obsidian Setup

**Note:** All plugins and settings are already included in the hidden `.obsidian` folder and Obsidian should work out of the box. Read below how to configure it or change settings.

**Required Plugins:**
1.  **Shell commands** (Community Plugin) – To run the build script.
2.  **Zotero Integration** (Community Plugin) – To insert citations.
3. **Pandoc plugin** (Community Plugin) – For export.
4.  **Pandoc Reference List** (Community Plugin) – To view formatted references in the sidebar.
5.  **Commentator** (Community Plugin) – For "Track Changes" (Suggest Mode).
6. Consider: **Editing Toolbar, Git, Advanced Tables** (Community Plugin) – optional. 

**Configuration:**

**1. Shell Commands:**
Go to **Settings -> Shell commands** and add these three distinct commands.
*Note: We use specific arguments (`pdf`, `safe`, `native`) to bypass the wizard menu for one-click builds.* You can assign an alias in the settings of each command.

* **Command 1:** `Export Journal PDF`
    * Command: `bash {{folder_path:absolute}}/build.sh {{file_path:absolute}} pdf`
* **Command 2:** `Export Journal Word (PNG figures)`
    * Command: `{{folder_path:absolute}}/build.sh {{file_path:absolute}} safe`
    * *Description: Converts figures to PNG. Best for sharing with Windows/LibreOffice users.*
* **Command 3:** `Export Journal Word (PDF figures)`
    * Command: `{{folder_path:absolute}}/build.sh {{file_path:absolute}} native`
    * *Description: Keeps PDF vectors. Best for macOS Word users.*

**2. Zotero Integration (Citation Insertion):**
* Go to **Settings -> Zotero Integration**.
* **Citation Format:** Select "Pandoc/Scrivener" (`@AuthorYear`).
* **Import Format:** Select "Better BibTeX JSON".
* **Usage:** Set a hotkey (e.g., `Alt+Z`) -> Press hotkey -> Search paper -> Enter.

**3. Pandoc Reference List (Sidebar View):**
* Go to **Settings -> Pandoc Reference List**.
* **Bibliography files:** Enter `references.json`.
* **Show citations:** Enable "Show citations in sidebar".

**4. Commentator:**
* Enable "Suggest Mode" via the ribbon icon to track edits.

---

### B. Terminal / Manual Usage
The `build.sh` script includes an interactive wizard if run without arguments.

1.  Open your terminal.
2.  Navigate to the project folder.
3.  Run:
    ```bash
    ./build.sh
    ```
4.  Follow the on-screen menu to select your output format and figure handling.

---

## 4. Application Setup (Zettlr)
Instructions on how to configure Zettlr to use the `config.yaml` file.

1.  Open **Assets Manager** (`Ctrl+M`).
2.  **Create Profile 1 (PDF):**
    * Category: **PDF Document**
    * Name: `Shared Config PDF`
    * Content:
        ```yaml
        defaults: "config.yaml"
        reader: markdown
        writer: pdf
        ```
3.  **Create Profile 2 (Word):**
    * Category: **Word / Docx**
    * Name: `Shared Config Word`
    * Content:
        ```yaml
        defaults: "config.yaml"
        reader: markdown
        writer: docx
        ```
*Note: Zettlr's built-in exporter does not currently support the `safe` mode image conversion logic. Use the Terminal or Obsidian for complex figure handling.*

---

## 5. Customizing the Word Template (`reference_doc.docx`)

If you need to adapt this template for a different journal:

1.  **Generate a generic base file:**
    ```bash
    pandoc -o new_reference.docx --print-default-data-file reference.docx
    ```
2.  **Edit Styles in Word:**
    Open `new_reference.docx` and open the **Styles Pane** (`Alt+Ctrl+Shift+S`). Modify **Normal**, **Headings 1-3**, and **Table Caption**.
3.  **Create the "FrontMatter" Style (Crucial):**
    * **New Style** -> Name: `FrontMatter` -> Based on: `Normal`.
    * Settings: **Left Aligned** (prevents title page distortion).
4.  **Save:** Save as `reference_doc.docx` overwriting the old file.

---

## 6. Writing Rules (The "Air Gap")

To avoid layout bugs, follow these spacing rules strictly.

**1. Title Page (FrontMatter)**
Use the `FrontMatter` custom style block for authors/affiliations.

```markdown
# Manuscript Title

::: {custom-style="FrontMatter"}
**Author Name**^1^
^1^ Department, University
:::
```

**2. Figures (`@Fig:id`)**
Always put an empty line after the image. **Use PDF figures** in your markdown (`image.pdf`); the build script will handle conversion for Word automatically.

```markdown
As seen in **@Fig:results**...

![**Title.** Legend text.](figures/image.pdf){#fig:results}

```

**3. Tables (`@Tbl:id`)**
Caption goes **ABOVE**. Empty line between Caption and Table is **mandatory**.

```markdown
See **@Tbl:stats** for details.

Table: **Title.** Description text. {#tbl:stats}

| Col A | Col B |
| :--- | :--- |
| Val 1 | Val 2 |
```

**4. Track Changes**
Use **Commentator** in Obsidian (Suggest Mode).

**5. Highlighting**
Use `==highlighted text==` for <mark style="background:#fff88f">drafting</mark> notes.