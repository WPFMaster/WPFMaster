#!/bin/bash

# --- 0. Pre-Setup --- EDIT THIS FOR YOUR WORKSPACE ---
DEFAULT_WORKSPACE_NAME="BASE"

# --- 1. Workspace & Path Logic (Works inside and outside git) ---
FULL_PATH=$(pwd)

# Attempt to get the Git top-level directory
if GIT_TOPLEVEL=$(git rev-parse --show-toplevel 2>/dev/null); then
    # We are inside a Git repository
    WORKSPACE_NAME=$(basename "$GIT_TOPLEVEL")
    
    # Reliably strip the git root from the full path to get the relative path
    RELATIVE_PATH="${FULL_PATH#"$GIT_TOPLEVEL"}"
    RELATIVE_PATH="${RELATIVE_PATH#/}" # Remove leading slash
else
    # We are OUTSIDE a Git repository
    WORKSPACE_NAME="$DEFAULT_WORKSPACE_NAME"
    
    # Leave relative path empty so it defaults cleanly to the base workspace name
    RELATIVE_PATH="" 
fi

echo "Workspace is: $WORKSPACE_NAME"

# --- 2. Input/Output Setup ---
INPUT_DIR="./src"
OUTPUT_DIR="./enc"

# CHECK: Ensure input directory exists
if [ ! -d "$INPUT_DIR" ]; then
    echo "❌ Error: Input directory '$INPUT_DIR' not found."
    echo "   Please create the folder and place files inside it."
    exit 1
fi

# CHECK: Ensure input directory is not empty
if [ -z "$(ls -A "$INPUT_DIR" 2>/dev/null)" ]; then
   echo "❌ Error: Input directory '$INPUT_DIR' is empty."
   exit 1
fi

mkdir -p "$OUTPUT_DIR"

# --- 3. Dynamic Key File Logic ---
# Keep symmetric passkeys in a dedicated, secure subfolder
KEY_DIR="$HOME/.ssh/passkeys"
mkdir -p "$KEY_DIR"
chmod 700 "$KEY_DIR"

FALLBACK_KEY="$KEY_DIR/$WORKSPACE_NAME"

# Construct specific key name, replacing slashes '/' with dots '.'
if [ -n "$RELATIVE_PATH" ]; then
    CLEAN_PATH="${RELATIVE_PATH//\//.}"
    SPECIFIC_FILENAME="${WORKSPACE_NAME}.${CLEAN_PATH}"
else
    # If we are at the root of a repo, or outside a workspace entirely
    SPECIFIC_FILENAME="$WORKSPACE_NAME"
fi

SPECIFIC_KEY="$KEY_DIR/$SPECIFIC_FILENAME"
ENCRYPTION_PASSKEY=""
USED_MANUAL_INPUT=false

# --- 4. Input Passkey Logic ---

# CASE 1: Specific Key exists
if [ "$SPECIFIC_FILENAME" != "$WORKSPACE_NAME" ] && [ -f "$SPECIFIC_KEY" ]; then
    echo "🔑 Specific key found: $SPECIFIC_FILENAME"
    read -p "   Do you want to use this key? (y/n): " USER_CHOICE
    
    if [[ "$USER_CHOICE" =~ ^[Yy]$ ]]; then
        echo "   Using specific key."
        ENCRYPTION_PASSKEY=$(< "$SPECIFIC_KEY")
    else
        echo "   Skipping specific key."
    fi
fi

# CASE 2: Base / Fallback Key exists (Only ask if we don't have a key yet)
if [ -z "$ENCRYPTION_PASSKEY" ] && [ -f "$FALLBACK_KEY" ]; then
    echo "❓ Base key found ($WORKSPACE_NAME)."
    read -p "   Do you want to use this key? (y/n): " USER_CHOICE
    
    if [[ "$USER_CHOICE" =~ ^[Yy]$ ]]; then
        echo "   Using base key."
        ENCRYPTION_PASSKEY=$(< "$FALLBACK_KEY")
    else
        echo "   Skipping base key."
    fi
fi

# CASE 3: Manual Input (If user skipped found keys, or none existed)
if [ -z "$ENCRYPTION_PASSKEY" ]; then
    USED_MANUAL_INPUT=true
    echo "------------------------------------------------"
    echo "Enter NEW encryption passkey (will not display):"
    read -s ENCRYPTION_PASSKEY
    echo 

    if [ -z "$ENCRYPTION_PASSKEY" ]; then
        echo "❌ Error: Passkey cannot be empty."
        exit 1
    fi

    echo "Enter encryption passkey again:"
    read -s ENCRYPTION_PASSKEY_2
    echo 
    echo "------------------------------------------------"

    if [ "$ENCRYPTION_PASSKEY" != "$ENCRYPTION_PASSKEY_2" ]; then
        echo "❌ Error: The passkeys don't match."
        exit 1
    fi
fi

echo "Starting encryption..."

# --- 5. Encryption Loop ---
for file in "$INPUT_DIR"/*; do
    if [ -f "$file" ]; then
        filename_only="${file##*/}"
        echo "Encrypting $filename_only..."
        
        # Modern syntax matching the decryption script
        openssl enc -aes-256-cbc -salt -pbkdf2 \
            -in "$file" \
            -out "$OUTPUT_DIR/$filename_only.enc" \
            -pass "pass:$ENCRYPTION_PASSKEY"
            
        if [ $? -ne 0 ]; then
            echo "❌ Error encrypting $filename_only"
            exit 1
        fi
    fi
done

echo "✅ Encryption complete."

# --- 6. Save Key Logic ---
if [ "$USED_MANUAL_INPUT" = true ]; then
    echo "------------------------------------------------"
    echo "Would you like to save this new passkey for future use?"
    echo "It will be saved as: $SPECIFIC_KEY"
    read -p "(y/n): " SAVE_CHOICE

    if [[ "$SAVE_CHOICE" =~ ^[Yy]$ ]]; then
        # Save the key securely
        echo -n "$ENCRYPTION_PASSKEY" > "$SPECIFIC_KEY"
        chmod 600 "$SPECIFIC_KEY"
        
        echo "✅ Passkey saved successfully."
    else
        echo "ℹ️  Passkey was NOT saved."
    fi
fi
