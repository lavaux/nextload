# Nextload - Nextcloud Share Downloader

A command-line tool to download files from Nextcloud share links.

## Installation

### Using Poetry (recommended)

```bash
# Install poetry if you don't have it
pip install poetry

# Install dependencies
poetry install
```

### Using pip

```bash
pip install click requests beautifulsoup4 tqdm
```

## Usage

```bash
# Download files
python nextload.py download --url "https://your-nextcloud.example.com/s/your-share-token" [--password "your-password"] [--output-dir "./downloads"] [--include "*.hdf5"] [--exclude "*.txt"]

# List files
python nextload.py list --url "https://your-nextcloud.example.com/s/your-share-token" [--password "your-password"] [--include "*.hdf5"] [--exclude "*.txt"]
```

### Commands

#### `download` command
Downloads files from a Nextcloud share.

#### `list` command  
Lists files from a Nextcloud share with sizes (no download).

### Common Arguments (for both commands)

- `--url`: Nextcloud share URL (required)
- `--password`: Share password (if the share is password-protected)
- `--include`: File pattern to include (can be used multiple times, e.g., `*.hdf5`, `losx*`) 
- `--exclude`: File pattern to exclude (can be used multiple times, e.g., `*.txt`, `temp*`)

### Download-only Arguments

- `--output-dir`: Local directory to save files (default: current directory)

## Examples

### Basic usage
```bash
python nextload.py --url "https://cloud.example.com/s/ABC123XYZ" --password "secret123" --output-dir "./my_files"
```

### Download only HDF5 files
```bash
python nextload.py --url "https://cloud.example.com/s/ABC123XYZ" --include "*.hdf5"
```

### Download files starting with "losx"
```bash
python nextload.py --url "https://cloud.example.com/s/ABC123XYZ" --include "losx*"
```

### Exclude text files
```bash
python nextload.py --url "https://cloud.example.com/s/ABC123XYZ" --exclude "*.txt"
```

### Multiple include patterns
```bash
python nextload.py --url "https://cloud.example.com/s/ABC123XYZ" --include "*.hdf5" --include "*.csv"
```

### Multiple exclude patterns
```bash
python nextload.py --url "https://cloud.example.com/s/ABC123XYZ" --exclude "*.txt" --exclude "temp*"
```

### Download with combined include and exclude
```bash
python nextload.py download --url "https://cloud.example.com/s/ABC123XYZ" --include "*.hdf5" --exclude "temp*.hdf5"
```

### List files with sizes (no download)
```bash
python nextload.py list --url "https://cloud.example.com/s/ABC123XYZ"
```

### List files with filtering
```bash
python nextload.py list --url "https://cloud.example.com/s/ABC123XYZ" --include "*.hdf5"
```

### List files with size filtering and exclusion
```bash
python nextload.py list --url "https://cloud.example.com/s/ABC123XYZ" --include "*.hdf5" --exclude "temp*.hdf5"
```

### Download with output directory
```bash
python nextload.py download --url "https://cloud.example.com/s/ABC123XYZ" --output-dir "./my_files"
```

### Download with password protection
```bash
python nextload.py download --url "https://cloud.example.com/s/ABC123XYZ" --password "secret123" --output-dir "./my_files"
```

## Features

- Download files from Nextcloud public shares
- Support for password-protected shares
- Resume interrupted downloads
- Progress bars for download status
- Recursive directory downloading
- Color-coded output for better visibility
- File pattern filtering (include/exclude patterns)
- Multiple pattern support for flexible filtering
- List files with sizes without downloading
- Human-readable file size formatting

## Requirements

- Python 3.8+
- Click
- Requests
- BeautifulSoup4
- tqdm

## License

MIT
