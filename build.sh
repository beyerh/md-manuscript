#!/bin/bash

# Usage: ./build.sh [input_file.md] [mode]
# Mode: pdf | safe | native

# --- Configuration ---
CONFIG="config.yaml"
LUA_FILTER="pdf2png.lua"

# Save original args to check if we are in interactive mode later
ORIG_ARG1="$1"

# --- 1. Select Input File ---
INPUT_FILE="$1"

# If no file provided, start Wizard
if [[ -z "$INPUT_FILE" ]]; then
    clear
    echo "=========================================="
    echo "   Select Source File"
    echo "=========================================="
    
    # Create array of md files
    files=(*.md)
    if [ ${#files[@]} -eq 0 ]; then
        echo "No Markdown files found!"
        exit 1
    fi

    # List files
    for i in "${!files[@]}"; do 
        echo "$((i+1))) ${files[$i]}"
    done

    echo "=========================================="
    read -p "Select file number: " file_idx
    
    # Validate selection
    file_idx=$((file_idx-1))
    if [[ -z "${files[$file_idx]}" ]]; then
        echo "Invalid selection."
        exit 1
    fi
    INPUT_FILE="${files[$file_idx]}"
fi

# --- 2. Select Build Mode ---
MODE="$2"

if [[ -z "$MODE" ]]; then
    echo ""
    echo "=========================================="
    echo "   Select Output Format for: $INPUT_FILE"
    echo "=========================================="
    echo "1) PDF Document"
    echo "2) Word (Safe Mode - PNG Figures)"
    echo "3) Word (Native Mode - PDF Figures)"
    echo "=========================================="
    read -p "Select option [1-3]: " mode_choice

    case $mode_choice in
        1) MODE="pdf" ;;
        2) MODE="safe" ;;
        3) MODE="native" ;;
        *) echo "Invalid choice"; exit 1 ;;
    esac
fi

# --- 3. Build Logic ---
# Calculate output filename (input.md -> input.pdf)
BASENAME=$(basename "$INPUT_FILE" .md)

if [[ "$MODE" == "pdf" ]]; then
    echo ">> Building PDF ($BASENAME.pdf)..."
    pandoc "$INPUT_FILE" -o "$BASENAME.pdf" --defaults=$CONFIG
    echo "PDF Build Complete."

elif [[ "$MODE" == "safe" ]]; then
    echo ">> Converting figures to PNG..."
    mogrify -density 300 -format png figures/*.pdf
    
    echo ">> Building Word Safe ($BASENAME.docx)..."
    pandoc "$INPUT_FILE" -o "$BASENAME.docx" --defaults=$CONFIG --lua-filter=$LUA_FILTER
    echo "Word Build Complete."

elif [[ "$MODE" == "native" ]]; then
    echo ">> Building Word Native ($BASENAME.docx)..."
    pandoc "$INPUT_FILE" -o "$BASENAME.docx" --defaults=$CONFIG
    echo "Word Build Complete."
else
    echo "Unknown mode: $MODE"
    exit 1
fi

# --- 4. Pause if Interactive ---
# Only pause if the user didn't provide arguments initially
if [[ -z "$ORIG_ARG1" ]]; then
    echo ""
    read -p "Press Enter to close..."
fi
