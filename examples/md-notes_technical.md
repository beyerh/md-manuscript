---
title: "Technical Documentation Template"
subtitle: "API Reference & Code Examples"
author: "Your Name"
date: "2024"
toc: true
---
\newpage

> **Profile:** Use with `pdf-notes` (Notes & Scripts) for digital sharing.
> Also compatible with `pdf-default` for print.

# Overview

This template is for **technical documentation**: API references, coding tutorials, software guides, or lab protocols. It emphasizes code blocks, structured information, and quick reference tables.

# Quick Reference

| Command | Description |
| --- | --- |
| `python build.py` | Run interactive build wizard |
| `python build.py --last` | Repeat last build |
| `python build.py --help` | Show all options |

# Installation

## Requirements

- Python 3.8+
- Pandoc 2.19+
- Tectonic (for PDF output)

## Setup

```bash
# Clone the repository
git clone https://github.com/user/project.git
cd project

# Install dependencies
pip install -r requirements.txt
```

# API Reference

## `build(source, profile)`

Build a document with the specified profile.

**Parameters:**

- `source` (str): Path to the source markdown file
- `profile` (str): Name of the profile (e.g., `pdf-default`)

**Returns:** Path to the generated output file.

**Example:**

```python
from build import build

output = build("02_maintext.md", "pdf-notes")
print(f"Created: {output}")
```

# Configuration

Settings are stored in YAML files under `resources/profiles/`.

```yaml
# Example profile structure
profile:
  name: "My Profile"
  format: pdf

variables:
  documentclass: article
  fontsize: 11pt
```

# Troubleshooting

## Common errors

**"Undefined control sequence"**
: Usually caused by raw LaTeX in markdown. Check that `raw_tex` is enabled in the profile's reader settings.

**"Font not found"**
: Install the required fonts or switch to a different font preset in the build options.

# See also

- Project documentation: [@smithDeepTissueImaging2024]
- Statistical methods: [@wilsonStatisticalMethods2023]
