#!/bin/bash

# Simplified Build Script for Scientific Manuscripts
# Usage: ./build.sh [main|si] [pdf|docx] [--png] [--include-si-refs]

set -e  # Exit on error

# --- Configuration ---
# IMPORTANT: If you rename your manuscript files, update these paths:
MAINTEXT="01_maintext.md"           # Main manuscript file
SUPPINFO="02_supp_info.md"          # Supporting Information file
CONFIG="resources/config.yaml"      # Pandoc configuration
LUA_FILTER="resources/pdf2png.lua"  # PDF to PNG conversion filter
SI_HEADER="_si_header.tex"          # Temporary SI header (auto-generated)
EXPORT_DIR="export"                 # Output directory

# Create export directory if it doesn't exist
mkdir -p "$EXPORT_DIR"

# --- Parse Arguments ---
DOC_TYPE=""
FORMAT=""
USE_PNG=false
INCLUDE_SI_REFS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        main|si) DOC_TYPE="$1" ;;
        pdf|docx) FORMAT="$1" ;;
        --png) USE_PNG=true ;;
        --include-si-refs) INCLUDE_SI_REFS=true ;;
        *) echo "Usage: ./build.sh [main|si] [pdf|docx] [--png] [--include-si-refs]"; exit 1 ;;
    esac
    shift
done

# --- Interactive Menu ---
if [[ -z "$DOC_TYPE" ]]; then
    echo "=========================================="
    echo "   Manuscript Build System"
    echo "=========================================="
    echo "1) Main Text"
    echo "2) Supporting Information"
    echo "=========================================="
    read -p "Select document [1-2]: " doc_choice
    case $doc_choice in
        1) DOC_TYPE="main" ;;
        2) DOC_TYPE="si" ;;
        *) echo "Invalid choice"; exit 1 ;;
    esac
fi

if [[ -z "$FORMAT" ]]; then
    echo "Select output format:"
    echo "1) PDF"
    echo "2) DOCX (Word)"
    read -p "Format [1-2]: " format_choice
    case $format_choice in
        1) FORMAT="pdf" ;;
        2) FORMAT="docx" ;;
        *) echo "Invalid choice"; exit 1 ;;
    esac
fi

if [[ "$FORMAT" == "docx" && "$USE_PNG" == false ]]; then
    read -p "Convert PDF figures to PNG? [y/n]: " png_choice
    [[ "$png_choice" == "y" || "$png_choice" == "Y" ]] && USE_PNG=true
fi

if [[ "$DOC_TYPE" == "main" && "$INCLUDE_SI_REFS" == false ]]; then
    read -p "Include SI references in bibliography? [y/n]: " si_refs_choice
    [[ "$si_refs_choice" == "y" || "$si_refs_choice" == "Y" ]] && INCLUDE_SI_REFS=true
fi

# --- Functions ---
create_si_header() {
    cat > "$SI_HEADER" << 'EOF'
\usepackage{lineno}
\setcounter{page}{1}
\renewcommand{\thefigure}{S\arabic{figure}}
\renewcommand{\thetable}{S\arabic{table}}
\renewcommand{\thepage}{S\arabic{page}}
EOF
}

convert_figures_to_png() {
    if ls figures/*.pdf 1> /dev/null 2>&1; then
        echo "   Converting PDF figures to PNG..."
        mogrify -density 300 -format png figures/*.pdf 2>/dev/null || true
    fi
}

build_main() {
    local output_file="$EXPORT_DIR/01_maintext.${FORMAT}"
    local input_file="$MAINTEXT"
    local temp_merged="_temp_merged.md"
    
    echo ">> Building Main Text ($FORMAT)..."
    
    if [[ "$INCLUDE_SI_REFS" == true ]]; then
        echo "   Including SI references in bibliography..."
        cat "$MAINTEXT" > "$temp_merged"
        
        # Extract only literature citations, exclude figure/table cross-references
        # Add them in a hidden paragraph using markdown citation syntax
        local si_cites=$(grep -o '@[a-zA-Z][a-zA-Z0-9_:-]*' "$SUPPINFO" | grep -v '@Fig:' | grep -v '@Tbl:' | grep -v '@email' | sort -u | paste -sd '; ' -)
        
        if [[ -n "$si_cites" ]]; then
            # Add before References section using pandoc's nocite metadata
            sed -i '1i ---\nnocite: |\n  '"$si_cites"'\n---\n' "$temp_merged"
        fi
        
        input_file="$temp_merged"
    fi
    
    if [[ "$FORMAT" == "docx" && "$USE_PNG" == true ]]; then
        convert_figures_to_png
    fi
    
    if [[ "$FORMAT" == "docx" ]]; then
        pandoc "$input_file" -o "$output_file" --defaults="$CONFIG" --lua-filter="$LUA_FILTER"
    else
        pandoc "$input_file" -o "$output_file" --defaults="$CONFIG" 2>/dev/null
    fi
    
    rm -f "$temp_merged"
    echo "   ✓ $output_file created"
}

build_si() {
    local output_file="$EXPORT_DIR/02_supp_info.${FORMAT}"
    
    echo ">> Building Supporting Information ($FORMAT)..."
    
    create_si_header
    
    if [[ "$FORMAT" == "docx" && "$USE_PNG" == true ]]; then
        convert_figures_to_png
    fi
    
    if [[ "$FORMAT" == "docx" ]]; then
        pandoc "$SUPPINFO" -o "$output_file" \
            --defaults="$CONFIG" \
            --metadata figPrefix='["Fig.","Figs."]' \
            --metadata tblPrefix='["Table","Tables"]' \
            --include-in-header="$SI_HEADER" \
            --lua-filter="$LUA_FILTER"
    else
        pandoc "$SUPPINFO" -o "$output_file" \
            --defaults="$CONFIG" \
            --metadata figPrefix='["Fig.","Figs."]' \
            --metadata tblPrefix='["Table","Tables"]' \
            --include-in-header="$SI_HEADER" 2>/dev/null
    fi
    
    rm -f "$SI_HEADER"
    echo "   ✓ $output_file created"
}

# --- Main ---
echo ""
echo "=========================================="
echo "   Document: ${DOC_TYPE^^}"
echo "   Format: ${FORMAT^^}"
[[ "$FORMAT" == "docx" ]] && echo "   PNG Conversion: $USE_PNG"
[[ "$DOC_TYPE" == "main" ]] && echo "   Include SI Refs: $INCLUDE_SI_REFS"
echo "=========================================="
echo ""

case $DOC_TYPE in
    main) build_main ;;
    si) build_si ;;
    *) echo "Error: Unknown document type"; exit 1 ;;
esac

echo ""
echo "Build complete!"
echo ""
