import sys
import subprocess
from pathlib import Path

# First arg is the prompt file, rest are passed to generate_image.py
prompt_file = sys.argv[1]
rest_args = sys.argv[2:]

prompt_text = Path(prompt_file).read_text(encoding="utf-8")

generate_script = str(Path(__file__).parent / "generate_image.py")

cmd = [sys.executable, generate_script, "--prompt", prompt_text] + rest_args
result = subprocess.run(cmd, capture_output=False)
sys.exit(result.returncode)