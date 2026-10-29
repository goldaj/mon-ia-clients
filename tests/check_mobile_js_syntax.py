"""Extract embedded PWA JavaScript and syntax-check it with Node in CI."""
import ast
import subprocess
import sys
import tempfile
from pathlib import Path

source = Path(__file__).resolve().parents[1] / "mobile" / "app.py"
tree = ast.parse(source.read_text(encoding="utf-8"))
index = None
worker = None
for node in tree.body:
    if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
        continue
    for target in node.targets:
        if isinstance(target, ast.Name):
            if target.id == "INDEX":
                index = node.value.value
            if target.id == "SERVICE_WORKER":
                worker = node.value.value

if index is None or worker is None or index.count("<script>") != 1:
    raise SystemExit("Embedded JavaScript structure unavailable")
javascript = index.split("<script>", 1)[1].split("</script>", 1)[0]
with tempfile.TemporaryDirectory() as folder:
    for name, code in (("inline.js", javascript), ("worker.js", worker)):
        path = Path(folder) / name
        path.write_text(code, encoding="utf-8")
        subprocess.run(["node", "--check", str(path)], check=True)
print("PASS: mobile inline script and service worker parse as JavaScript")
