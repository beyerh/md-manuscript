# Manuscript Build Plugin for Obsidian

Graphical interface for building academic manuscripts to PDF/DOCX from Obsidian using Pandoc.

## Requirements

- Python 3 (accessible via PATH)
- Pandoc (for document conversion)
- LaTeX distribution (for PDF output):
  - **Recommended**: [Tectonic](https://tectonic-typesetting.github.io/) - Modern LaTeX engine with:
    - Automatic package installation (no manual management)
    - Small footprint (~200MB vs 4GB+ for full TeX Live)
    - Self-contained (no system-wide installation)
    - Reliable compilation with pre-built bundles
  - Alternatives: TeX Live, MiKTeX (full distributions)
- `build.py` script in vault root

## Installation

### From Source
```bash
cd .obsidian/plugins/obsidian-manuscript-build
npm install
npm run build
```
Then enable in Obsidian Settings → Community Plugins

### LaTeX Options
For PDF output, ensure:
1. Full LaTeX installation OR Tectonic
2. Required packages:
   - `latexmk` (for compilation)
   - `texlive-fonts-extra` (for special fonts)
   - `texlive-science` (for math packages)

## Development
```bash
npm install       # Install dependencies
npm run dev       # Development mode (watch)
npm run build     # Production build
```

## Troubleshooting

### Common Issues
- **Missing Python**: Set correct path in plugin settings
- **LaTeX errors**:
  - Check `tectonic.log` or latexmk output
  - Ensure all required packages installed
- **Build failures**:
  - Verify Pandoc is installed (`pandoc --version`)
  - Check build.py exists at configured path
