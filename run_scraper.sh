#!/bin/bash
# Convenient wrapper to run the scraper with venv activated

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate venv
source "$DIR/venv/bin/activate"

# Run scraper with all passed arguments
python "$DIR/scripts/scraper.py" "$@"

# Deactivate when done
deactivate
