# Markdown Writing Guide

This guide will help you write scientific manuscripts, theses, and notes using Markdown. Here you will find general Markdown guidelines and template-specific tips.

---

## Part 1: Introduction to Markdown

### What is Markdown?

Markdown is a lightweight markup language that uses plain text formatting syntax. It's easy to read and write, and can be converted to beautifully formatted documents (PDF, Word, HTML, etc.).

### Basic Syntax

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

- Use **PDF format** (auto-converted to PNG for Word)
- Store in `figures/` folder
- Caption goes **below** the figure
- Reference with `**@Fig:label**`

```markdown
![**Figure Title.** Legend text describing the figure.](figures/image.pdf){#fig:label}
```

**To reference:** Use `**@Fig:label**` in text → renders as "Figure 1"

### Tables

- Caption goes **above** the table
- Reference with `**@Tbl:label**`
- Use pipe (`|`) to separate columns
- Use colons (`:`) to align columns

```markdown
Table: **Table Title.** Description of the table. {#tbl:label}

| Column A | Column B | Column C |
|:---------|:--------:|---------:|
| Left     | Center   | Right    |
| Value 1  | Value 2  | Value 3  |
```

**Alignment:**
- `:---` = left-aligned
- `:---:` = centered
- `---:` = right-aligned

**To reference:** Use `**@Tbl:label**` in text → renders as "Table 1"

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

**Colored text** (PDF only):
```markdown
This is <font color="red">red text</font>.
This is <font color="#0000ff">blue text</font>.
This is <font color="green">green text</font>.
```

**Note:** Colored text works in PDF but **not in DOCX**. For Word documents, apply colors manually after export, or use highlighting which works in both formats.

### Footnotes

```markdown
This statement needs clarification^[This is the footnote text.].
```

---

## Part 3: Template-Specific Use Cases

The `examples/` folder contains ready-to-use templates for different document types. Each template is optimized for specific use cases and profiles.

# 4. Full-width Elements (Two-Column Layouts)

For for two-column profiles if you want to include full-width figures or tables that span both columns, use raw LaTeX as follows:

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

