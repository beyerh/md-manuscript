#!/usr/bin/env python3
"""
Cross-platform Build Script for Scientific Manuscripts
Usage: python build.py [main|si] [pdf|docx] [--png] [--include-si-refs] [--no-frontmatter]
"""

import subprocess
import sys
import os
import re
import shutil
from pathlib import Path

# --- Configuration ---
# IMPORTANT: If you rename your manuscript files, update these paths:
FRONTMATTER = "00_frontmatter.md"      # Common frontmatter file
MAINTEXT = "01_maintext.md"            # Main manuscript file
SUPPINFO = "02_supp_info.md"           # Supporting Information file
CONFIG = "resources/config.yaml"       # Pandoc configuration
LUA_FILTER = "resources/pdf2png.lua"   # PDF to PNG conversion filter
SI_HEADER = "_si_header.tex"           # Temporary SI header (auto-generated)
EXPORT_DIR = "export"                  # Output directory


def create_export_dir():
    """Create export directory if it doesn't exist."""
    Path(EXPORT_DIR).mkdir(exist_ok=True)


def parse_arguments():
    """Parse command line arguments."""
    doc_type = ""
    fmt = ""
    use_png = False
    include_si_refs = False
    include_frontmatter = True

    args = sys.argv[1:]
    for arg in args:
        if arg in ("main", "si"):
            doc_type = arg
        elif arg in ("pdf", "docx"):
            fmt = arg
        elif arg == "--png":
            use_png = True
        elif arg == "--include-si-refs":
            include_si_refs = True
        elif arg == "--no-frontmatter":
            include_frontmatter = False
        else:
            print("Usage: python build.py [main|si] [pdf|docx] [--png] [--include-si-refs] [--no-frontmatter]")
            sys.exit(1)

    return doc_type, fmt, use_png, include_si_refs, include_frontmatter


def interactive_menu(doc_type, fmt, use_png, include_si_refs, include_frontmatter):
    """Display interactive menu for missing options."""
    interactive_mode = False

    if not doc_type:
        interactive_mode = True
        print("==========================================")
        print("   Manuscript Build System")
        print("==========================================")
        print("1) Main Text")
        print("2) Supporting Information")
        print("==========================================")
        doc_choice = input("Select document [1-2]: ").strip()
        if doc_choice == "1":
            doc_type = "main"
        elif doc_choice == "2":
            doc_type = "si"
        else:
            print("Invalid choice")
            sys.exit(1)

    if not fmt:
        interactive_mode = True
        print("Select output format:")
        print("1) PDF")
        print("2) DOCX (Word)")
        format_choice = input("Format [1-2]: ").strip()
        if format_choice == "1":
            fmt = "pdf"
        elif format_choice == "2":
            fmt = "docx"
        else:
            print("Invalid choice")
            sys.exit(1)

    if interactive_mode:
        if fmt == "docx" and not use_png:
            png_choice = input("Convert PDF figures to PNG? [y/n]: ").strip().lower()
            if png_choice == "y":
                use_png = True

        if doc_type == "main" and not include_si_refs:
            si_refs_choice = input("Include SI references in bibliography? [y/n]: ").strip().lower()
            if si_refs_choice == "y":
                include_si_refs = True

        frontmatter_choice = input(f"Include frontmatter from {FRONTMATTER}? [Y/n]: ").strip().lower()
        if frontmatter_choice == "n":
            include_frontmatter = False

    return doc_type, fmt, use_png, include_si_refs, include_frontmatter


def create_si_header():
    """Create the SI header file for LaTeX."""
    content = r"""\usepackage{lineno}
\setcounter{page}{1}
\renewcommand{\thefigure}{S\arabic{figure}}
\renewcommand{\thetable}{S\arabic{table}}
\renewcommand{\thepage}{S\arabic{page}}
"""
    with open(SI_HEADER, "w") as f:
        f.write(content)


def convert_figures_to_png():
    """Convert PDF figures to PNG using ImageMagick."""
    figures_dir = Path("figures")
    if figures_dir.exists():
        pdf_files = list(figures_dir.glob("*.pdf"))
        if pdf_files:
            print("   Converting PDF figures to PNG...")
            try:
                subprocess.run(
                    ["mogrify", "-density", "300", "-format", "png", "figures/*.pdf"],
                    shell=False,
                    capture_output=True
                )
            except Exception:
                pass  # Silently ignore conversion errors


def extract_si_citations():
    """Extract literature citations from SI file, excluding cross-references."""
    if not Path(SUPPINFO).exists():
        return ""
    
    with open(SUPPINFO, "r") as f:
        content = f.read()
    
    # Find all citations
    citations = set(re.findall(r"@[a-zA-Z][a-zA-Z0-9_:-]*", content))
    
    # Exclude figure/table cross-references and email
    excluded = {"@Fig:", "@Tbl:", "@email"}
    filtered = [c for c in citations if not any(c.startswith(e.rstrip(":")) for e in excluded)]
    
    return "; ".join(sorted(filtered))


def build_main(fmt, use_png, include_si_refs, include_frontmatter):
    """Build the main text document."""
    output_file = f"{EXPORT_DIR}/01_maintext.{fmt}"
    input_file = MAINTEXT
    temp_merged = "_temp_merged.md"

    print(f">> Building Main Text ({fmt})...")

    # Merge frontmatter if requested
    if include_frontmatter:
        print(f"   Merging frontmatter from {FRONTMATTER}...")
        with open(temp_merged, "w") as out:
            with open(FRONTMATTER, "r") as f:
                out.write(f.read())
            out.write("\n")
            with open(MAINTEXT, "r") as f:
                out.write(f.read())
        input_file = temp_merged

    if include_si_refs:
        print("   Including SI references in bibliography...")
        
        # If we haven't created temp_merged yet, create it now
        if not include_frontmatter:
            shutil.copy(MAINTEXT, temp_merged)
            input_file = temp_merged

        si_cites = extract_si_citations()
        if si_cites:
            # Prepend nocite metadata to the file
            with open(temp_merged, "r") as f:
                original_content = f.read()
            
            nocite_header = f"---\nnocite: |\n  {si_cites}\n---\n\n"
            with open(temp_merged, "w") as f:
                f.write(nocite_header + original_content)

    if fmt == "docx" and use_png:
        convert_figures_to_png()

    # Build pandoc command
    cmd = ["pandoc", input_file, "-o", output_file, f"--defaults={CONFIG}"]
    if fmt == "docx":
        cmd.append(f"--lua-filter={LUA_FILTER}")

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"   Error: {e.stderr.decode() if e.stderr else 'Unknown error'}")
        sys.exit(1)

    # Cleanup
    if Path(temp_merged).exists():
        os.remove(temp_merged)

    print(f"   ✓ {output_file} created")


def build_si(fmt, use_png, include_frontmatter):
    """Build the supporting information document."""
    output_file = f"{EXPORT_DIR}/02_supp_info.{fmt}"
    input_file = SUPPINFO
    temp_merged = "_temp_si_merged.md"

    print(f">> Building Supporting Information ({fmt})...")

    # Merge frontmatter if requested
    if include_frontmatter:
        print(f"   Merging frontmatter from {FRONTMATTER}...")
        with open(temp_merged, "w") as out:
            with open(FRONTMATTER, "r") as f:
                out.write(f.read())
            out.write("\n")
            with open(SUPPINFO, "r") as f:
                out.write(f.read())
        input_file = temp_merged

    create_si_header()

    if fmt == "docx" and use_png:
        convert_figures_to_png()

    # Build pandoc command
    cmd = [
        "pandoc", input_file, "-o", output_file,
        f"--defaults={CONFIG}",
        "--metadata", 'figPrefix=["Fig.","Figs."]',
        "--metadata", 'tblPrefix=["Table","Tables"]',
        f"--include-in-header={SI_HEADER}"
    ]
    if fmt == "docx":
        cmd.append(f"--lua-filter={LUA_FILTER}")

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"   Error: {e.stderr.decode() if e.stderr else 'Unknown error'}")
        sys.exit(1)

    # Cleanup
    if Path(SI_HEADER).exists():
        os.remove(SI_HEADER)
    if Path(temp_merged).exists():
        os.remove(temp_merged)

    print(f"   ✓ {output_file} created")


def main():
    """Main entry point."""
    create_export_dir()

    # Parse arguments
    doc_type, fmt, use_png, include_si_refs, include_frontmatter = parse_arguments()

    # Interactive menu for missing options
    doc_type, fmt, use_png, include_si_refs, include_frontmatter = interactive_menu(
        doc_type, fmt, use_png, include_si_refs, include_frontmatter
    )

    # Display build info
    print()
    print("==========================================")
    print(f"   Document: {doc_type.upper()}")
    print(f"   Format: {fmt.upper()}")
    print(f"   Include Frontmatter: {str(include_frontmatter).lower()}")
    if fmt == "docx":
        print(f"   PNG Conversion: {str(use_png).lower()}")
    if doc_type == "main":
        print(f"   Include SI Refs: {str(include_si_refs).lower()}")
    print("==========================================")
    print()

    # Build
    if doc_type == "main":
        build_main(fmt, use_png, include_si_refs, include_frontmatter)
    elif doc_type == "si":
        build_si(fmt, use_png, include_frontmatter)
    else:
        print("Error: Unknown document type")
        sys.exit(1)

    print()
    print("Build complete!")
    print()


if __name__ == "__main__":
    main()
