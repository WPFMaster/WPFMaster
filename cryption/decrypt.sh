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
INPUT_DIR="./enc"
OUTPUT_DIR="./dec"

# CHECK: Ensure input directory exists
if [ ! -d "$INPUT_DIR" ]; then
    echo "❌ Error: Input directory '$INPUT_DIR' not found."
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
FINAL_PASSKEY=""

# --- 4. Input Passkey Logic ---

# CASE 1: Specific Key (Trust immediately, no test needed)
if [ "$SPECIFIC_FILENAME" != "$WORKSPACE_NAME" ] && [ -f "$SPECIFIC_KEY" ]; then
    echo "🔑 Specific key found: $SPECIFIC_FILENAME"
    echo "Reading passkey from file..."
    FINAL_PASSKEY=$(< "$SPECIFIC_KEY")

# CASE 2: Base Key / Fallback (Test validity first)
elif [ -f "$FALLBACK_KEY" ]; then
    echo "❓ Base key found ($WORKSPACE_NAME). Testing validity..."
    
    # Read the candidate key
    CANDIDATE_KEY=$(< "$FALLBACK_KEY")
    
    # Find the first .enc file to run a test decryption
    TEST_FILE=$(ls "$INPUT_DIR"/*.enc 2>/dev/null | head -n 1)
    
    if [ -z "$TEST_FILE" ]; then
        echo "   ⚠️  No files to test. Assuming key is correct."
        FINAL_PASSKEY="$CANDIDATE_KEY"
    else
        # Try to decrypt to /dev/null just to check the exit code
        # FIX: Matches the exact syntax of the encryption script
        openssl enc -aes-256-cbc -d -salt -pbkdf2 \
            -in "$TEST_FILE" \
            -pass "pass:$CANDIDATE_KEY" \
            -out /dev/null 2>/dev/null
        
        if [ $? -eq 0 ]; then
            echo "   ✅  Test passed. Using base key."
            FINAL_PASSKEY="$CANDIDATE_KEY"
        else
            echo "   ❌  Test failed. Key in '$WORKSPACE_NAME' file is incorrect for these files."
            # We leave FINAL_PASSKEY empty so it falls through to manual input below
        fi
    fi
fi

# CASE 3: Manual Input (If no key found yet or test failed)
if [ -z "$FINAL_PASSKEY" ]; then
    echo 
    echo "Enter decryption passkey (will not display):"
    read -s FINAL_PASSKEY
    echo 
fi

# Final Validation
if [ -z "$FINAL_PASSKEY" ]; then
    echo "❌ Error: Passkey cannot be empty."
    exit 1
fi

echo "Starting decryption..."

# --- 5. Decryption Loop ---
for file in "$INPUT_DIR"/*.enc; do
    if [ -f "$file" ]; then
        full_filename="${file##*/}"
        original_filename="${full_filename%.enc}"
        
        echo "Decrypting $full_filename..."
        
        # FIX: Ensure we use the -d flag for decryption, matching the modern encryption syntax
        openssl enc -aes-256-cbc -d -salt -pbkdf2 \
            -in "$file" \
            -out "$OUTPUT_DIR/$original_filename" \
            -pass "pass:$FINAL_PASSKEY"
            
        if [ $? -ne 0 ]; then
            echo "❌ Error decrypting $full_filename"
        else
            echo "✅ Success"
        fi
    fi
done

echo "✅ Decryption complete."
