#!/bin/bash

# Check if input file is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <input_file>"
    exit 1
fi

input_file="$1"

# Define video formats to check
video_formats=("mp4" "MOV" "mov" "MP4")

# Function to check for video files in directory and return the format found
check_video_files() {
    local dir="$1"
    local files=""
    local format_found=""
    
    echo "Checking directory: $dir" >&2
    
    for format in "${video_formats[@]}"; do
        echo "Looking for *.$format files..." >&2
        found_files=$(ls "$dir"/*."$format" 2>/dev/null)
        if [ ! -z "$found_files" ]; then
            echo "Found files with .$format extension" >&2
            echo "${found_files}|${format}"  # Use pipe as delimiter
            return 0
        fi
    done
    
    echo "No video files found" >&2
    echo "|"  # Return empty result with delimiter
}

# Function to get file extension
get_file_extension() {
    local filename="$1"
    local ext="${filename##*.}"
    echo "${ext,,}"  # Convert to lowercase
}

# Function to find video format in directory
find_video_format() {
    local dir="$1"
    local result=$(check_video_files "$dir")
    local format="${result#*|}"  # Get everything after the pipe
    echo "$format"
}

# Initialize arrays for tracking
declare -a successful_games=()
declare -a failed_games=()
declare -a skipped_games=()

# Function to process a game
process_game() {
    local game_name=$1
    local left_path=$2
    local right_path=$3
    local start_time=$4  
    
    # Check if output file already exists
    local output_path="$(dirname "$left_path")/$game_name.mp4"
    if [ -f "$output_path" ]; then
        echo "⏭️  Skipping $game_name - output file already exists: $output_path"
        echo "----------------------------------------"
        skipped_games+=("$game_name")
        return 0
    fi
    
    echo "Processing game: $game_name"
    echo "Start time: $start_time"
    echo "Output directory: $(dirname "$left_path")"

    # Determine if we're dealing with directories or single files
    if [ -d "$left_path" ]; then
        echo "Checking left directory for videos..."
        local format=$(find_video_format "$left_path")
        if [ -z "$format" ]; then
            echo "❌ Failed: No video files found in left directory"
            failed_games+=("$game_name")
            return 1
        fi
        echo "Left format found: '$format'"

        echo "Checking right directory for videos..."
        local right_format=$(find_video_format "$right_path")
        if [ -z "$right_format" ]; then
            echo "❌ Failed: No video files found in right directory"
            failed_games+=("$game_name")
            return 1
        fi
        echo "Right format found: '$right_format'"

        # Use directory mode with start time
        local cmd="python3 -m ml.meow.meow -ld \"$left_path\" -rd \"$right_path\""
    else
        # Use single file mode with start time
        local format="${left_path##*.}"
        local cmd="python3 -m ml.meow.meow -l \"$left_path\" -r \"$right_path\""
    fi

    # Add common parameters including start time
    local tmp_dir="$(dirname "$left_path")/meow_tmp_$game_name"
    cmd="$cmd -o \"$output_path\" -p --use-logo -s -od \"$tmp_dir\" -t \"$format\" -st \"$start_time\""
    
    echo "Executing: $cmd"
    echo "----------------------------------------"
    
    eval "$cmd"
    local status=$?
    
    if [ $status -ne 0 ]; then
        echo "❌ Failed: Error processing $game_name"
        echo "Command failed: $cmd"
        failed_games+=("$game_name")
        return 1
    else
        echo "✅ Success: Processed $game_name"
        echo "Output saved to: $output_path"
        echo "Removing temporary directory: $tmp_dir"
        rm -rf "$tmp_dir"
        echo "----------------------------------------"
        successful_games+=("$game_name")
        return 0
    fi
}

# Process each game
while true; do
    # Read 4 lines
    read -r game_name || break
    read -r left_path || break
    read -r right_path || break
    read -r start_time || break
    
    # Skip empty lines between entries
    read -r empty_line || break
    
    # Skip if game name is empty
    if [ -n "$game_name" ]; then
        process_game "$game_name" "$left_path" "$right_path" "$start_time"
    fi
done < "$input_file"

# Print summary
echo ""
echo "====== Processing Summary ======"
echo ""

if [ ${#successful_games[@]} -gt 0 ]; then
    echo "✅ Successfully processed games (${#successful_games[@]}):"
    for game in "${successful_games[@]}"; do
        echo "  - $game"
    done
    echo ""
fi

if [ ${#failed_games[@]} -gt 0 ]; then
    echo "❌ Failed games (${#failed_games[@]}):"
    for game in "${failed_games[@]}"; do
        echo "  - $game"
    done
    echo ""
fi

if [ ${#skipped_games[@]} -gt 0 ]; then
    echo "⏭️  Skipped games (${#skipped_games[@]}):"
    for game in "${skipped_games[@]}"; do
        echo "  - $game"
    done
    echo ""
fi

# Print final statistics
total=$((${#successful_games[@]} + ${#failed_games[@]} + ${#skipped_games[@]}))
echo "====== Final Statistics ======"
echo "Total games processed: $total"
echo "Successful: ${#successful_games[@]}"
echo "Failed: ${#failed_games[@]}"
echo "Skipped: ${#skipped_games[@]}"
echo "============================"
