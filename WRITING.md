# Markdown Writing Guide

This guide will help you write scientific manuscripts, theses, and notes using Markdown. Here you will find general Markdown guidelines and template-specific tips.

---

## Part 1: Introduction to Markdown

### What is Markdown?

Markdown is a simple way to format text that can be converted to PDF, Word, HTML, and more. It's designed to be easy to read and write.

### Basic Formatting

#### Headers

Create headers using hash symbols (`#`). More hashes = smaller heading:

```markdown
# Heading 1 (largest)
## Heading 2
### Heading 3
#### Heading 4
```

**Result:** Creates hierarchical section headings in your document.

#### Text Formatting

```markdown
*italic text* or _italic text_
**bold text** or __bold text__
***bold and italic***
~~strikethrough~~
==highlighted text==
```

**Examples:**
- *This is italic*
- **This is bold**
- ***This is bold and italic***
- ~~This is crossed out~~
- ==highlighted text==

#### Lists

**Unordered lists** use asterisks, plus signs, or hyphens:

```markdown
* Item 1
* Item 2
  * Sub-item 2.1
  * Sub-item 2.2
* Item 3
```

**Ordered lists** use numbers:

```markdown
1. First item
2. Second item
3. Third item
```

#### Links and Images

```markdown
[Link text](https://www.example.com)
![Image alt text](path/to/image.png)
```

#### Block Quotes

```markdown
> This is a quote.
> It can span multiple lines.
```

**Result:**
> This is a quote.
> It can span multiple lines.

#### Code

**Inline code** uses single backticks:
```markdown
The `print()` function outputs text.
```

**Code blocks** use triple backticks:
````markdown
```python
def hello():
    print("Hello, world!")
```
````

#### Paragraphs and Line Breaks

- **New paragraph:** Leave a blank line between paragraphs
- **Line break:** End a line with two spaces or use `\` (backslash)

```markdown
This is paragraph one.

This is paragraph two.
```

---

## Part 2: Scientific Writing using md-manuscript
### Figures

**Easiest method:** Use the **Templater** plugin (click the `< %` icon in Obsidian's left ribbon). It inserts a ready-to-use template.

The templates live in `resources/templater/` and look like this:

```markdown
> [!figure] #fig:yourfigurelabel width=100% align=center
> ![](figures/yourfigure.pdf)
>
> **Figure Title.** Caption text.
```

**How to use:**
1. Click the `< %` icon and select the figure template
2. Change `yourfigurelabel` to something descriptive (e.g., `results`)
3. Change `yourfigure.pdf` to your actual file name
4. Write your title and caption
5. (Optional) Adjust size/alignment if needed

**Reference in text:** `See **@Fig:yourfigurelabel**` → automatically becomes "See Figure 1"

**Tips:**
- Use PDF figures when possible (automatically converted to PNG for Word if needed)
- Keep figures in the `figures/` folder
- The options (width, align) are optional - defaults work fine and you can delete them if you want

**Advanced Placement Options:**
- **Position (LaTeX only):** Use `pos=h|t|b|p|H` to control float placement.
  - `h` (here), `t` (top), `b` (bottom), `p` (page), `H` (forced here).
  - Example: `> [!figure] #fig:myfig pos=b` forces figure to bottom of page.
- **Text Wrapping:** Use `wrap=l|r` to wrap text around the figure.
  - `l` (left), `r` (right), `o` (outer), `i` (inner).
  - Example: `> [!figure] #fig:myfig wrap=r width=50%` places figure on right with text wrapping around it.

### Tables

**Easiest method:** Use the **Templater** plugin (click the `< %` icon) for a ready-to-use template.

The table template looks like this:

```markdown
> [!table] #tbl:yourtablelabel width=100% align=center columns=0.25,0.45,0.30 colsep=4pt fontsize=footnotesize spacing=1.1
>
> **Table Title.** Caption text.

| Column A | Column B | Column C |
|---|---|---|
|   |   |   |
```

**How to use**
1. Insert the template via Templater.
2. Change `yourtablelabel` to your label.
3. Write your caption.
4. Edit the Markdown table (Obsidian’s table editor works).
5. (Optional) Adjust options or delete them if you want:
   - `width=80%` or `width=\textwidth`
   - `align=left|center|right`
   - `span=full` for full-width tables in two-column layouts
   - `fontsize=small` or `footnotesize`
   - `columns=0.3,0.7` (relative widths)
   - `colsep=4pt` (column spacing)
   - `spacing=1.2` (row spacing)

**Reference in text:** `**@Tbl:yourtablelabel**` → “Table 1”

**Tips**
- Column alignment in the table uses `:---` (left), `:---:` (center), `---:` (right).
- Options are optional; defaults work fine and you could delete them.

### Cross-References

```markdown
**@Fig:results**  → "Figure 1"
**@Tbl:data**     → "Table 1"
[@smith2023]      → "(Smith 2023)"
```

### Mathematical Equations

**Inline math** uses single dollar signs:
```markdown
The p-value was $p < 0.05$.
```

**Display equations** use double dollar signs:
```markdown
$$
E = mc^2
$$
```

**More complex example:**
```markdown
$$
\sigma = \sqrt{\frac{\sum(x_i - \mu)^2}{N}}
$$
```

### Subscripts and Superscripts

```markdown
H~2~O          → H₂O
E=mc^2^        → E=mc²
CO~2~ levels   → CO₂ levels
```

### Special Typography

**Non-breaking spaces:** Use backslash + space (`\ `) to keep numbers and units together:
```markdown
10\ kg, p\ <\ 0.05, 25\ °C
```

**En-dash for ranges:** Use double hyphens:
```markdown
10--20%   → 10–20%
2020--2024 → 2020–2024
```

### Citations

Use Zotero citation keys in square brackets:
```markdown
Previous studies [@smith2023] showed that...
Multiple citations [@smith2023; @jones2024] demonstrate...
Smith et al. [-@smith2023] reported...
```

### Highlighting and Colored Text

**Yellow highlighting** (works in PDF and DOCX):
```markdown
The results show ==significant improvement== in all metrics.
```
You can use the Toolbar button to apply highlighting.

**Colored text** (PDF only):
```markdown
This is <font color="red">red text</font>.
This is <font color="#0000ff">blue text</font>.
This is <font color="green">green text</font>.
```
You can use the Toolbar button to apply colors.

**Note:** Colored text works in PDF/LaTeX but **not in DOCX**. For Word documents, apply colors manually after export, or use highlighting which works in both formats.

### Footnotes

```markdown
This statement needs clarification^[This is the footnote text.].
```

---

## Part 3: Template-Specific Use Cases

The `examples/` folder contains ready-to-use templates for different document types. Each template is optimized for specific use cases and profiles.

# Full-width Elements (Two-Column Layouts)

For two-column profiles, add `span=full` to make figures or tables span both columns:

```markdown
> [!figure] #fig:label span=full width=90% align=center
> ![](figures/image.pdf)
>
> **Figure Title.** Caption.
```

```markdown
> [!table] #tbl:label span=full align=center
>
> **Table Title.** Caption.

| A | B |
|---|---|
| 1 | 2 |
```

---

## Part 4: Managing Large Projects

For theses, dissertations, or books, you might want to split your work into multiple files (e.g., one file per chapter). This plugin supports a **Master File** approach.

### Master File Structure

Create a "Master" Markdown file (e.g., `Master.md`) that serves as the backbone of your manuscript. Use Obsidian's **transclusion** syntax (`![[filename]]`) to include other files.

**Example `Master.md`:**

```markdown
# Introduction
![[01-Introduction.md]]

# Methods
![[02-Methods.md]]

# Results
![[03-Results.md]]

# Discussion
![[04-Discussion.md]]
```

When you build this `Master.md` file using the plugin, it will automatically:
1.  **Resolve Transclusions:** Replace `![[01-Introduction.md]]` with the actual content of that file.
2.  **Adjust Heading Levels:** (Optional) If your chapters start with H1 (`#`), you can structure your Master file to respect that or shift levels if needed.
3.  **Merge Bibliography:** Collect citations from all included files into a single reference list.

### Single File Export (PDF/DOCX)

You can use the same `Master.md` to generate a standard single-file output (PDF or Word):

1.  Open `Master.md`.
2.  Open the **Command Palette** (`Cmd/Ctrl + P`) and run `MD Manuscript: Build current file`.
3.  Select a profile (e.g., `pdf-default` or `docx-manuscript`).
4.  The plugin will merge all chapters and produce a single `Master.pdf` or `Master.docx`.

### Digital Garden Export (HTML/Web)

If you want to publish your notes as a **Digital Garden** (e.g., using Obsidian Publish or a static site generator), you might want to keep the files separate but updated with the correct links.

Use the **"Digital Garden Mode"**:

1.  Enable the plugin `Digital Garden Mode`
2.  The plugin will:
    *   Process each included file independently.
    *   Resolve internal links between chapters.
    *   Generate individual HTML-ready Markdown files in the `export/` folder.
    *   Preserve the file structure for web navigation.

