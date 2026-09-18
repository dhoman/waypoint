import subprocess
import sys


def test_strict_process_denies_model_import_and_external_network():
    process = subprocess.run(
        [sys.executable, "-m", "waypoint.app.isolation", "--self-test"],
        capture_output=True,
        text=True,
    )
    assert process.returncode == 0, process.stderr
    assert '"provider_import": "blocked"' in process.stdout
    assert '"external_connection": "blocked"' in process.stdout
