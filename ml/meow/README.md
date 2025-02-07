# Meow

Meow is a tool for stitching videos together.

## Usage

Due to relative imports, meow must be run from the root directory.

```bash
python3 -m ml.meow.meow [arguments]
```

### Arguments

Available arguments:

| Category | Argument | Description | Default |
|----------|----------|-------------|---------|
| **Input** |
| | `-l, --left-videos` | Path to a single left camera video file | Required* |
| | `-ld, --left-directory` | Path to directory with left camera videos | Required* |
| | `-r, --right-videos` | Path to a single right camera video file | Required* |
| | `-rd, --right-directory` | Path to directory with right camera videos | Required* |
| | `-o, --output` | Path of the output video file | `meow_output.mp4` |
| **Processing Mode** |
| | `-m, --mixer` | Use video mixer mode | `False` |
| | `-p, --panorama` | Use panorama stitching mode | `False` |
| | `-mt, --mixer-type` | Mixer type: "farneback" or "abs_diff" | `farneback` |
| **Video Options** |
| | `-st, --start-time` | Start time as HH:MM:SS | Full video |
| | `-et, --end-time` | End time as HH:MM:SS | Full video |
| | `-t, --file-type` | Video file type (without dot) | `mp4` |
| | `--use-logo` | Add logo overlay | `False` |
| **Output Options** |
| | `-YT, --upload-YT` | Upload to Youtube | `False` |
| | `-s, --save` | Save intermediate files | `False` |
| | `-od, --output-directory` | Output directory path | System temp |
| **Other** |
| | `--make-sample` | Create 2-minute sample | `False` |
| | `-v, --verbose` | Show debug output | `False` |

\* Input Requirements:
- For single videos: Use `-l` and `-r`
- For multiple videos in folders: Use `-ld` and `-rd`
- Cannot mix single files and directories



