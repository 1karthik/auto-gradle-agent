# agent_app/gradle_utils.py
import subprocess
from pathlib import Path
from typing import Tuple, Dict, Optional

def update_gradle_property(file_path: Path, property_name: str, property_value: str) -> bool:
    """
    Updates or adds a property in a .properties file (like gradle.properties).
    """
    if not file_path.exists():
        print(f"Warning: {file_path} not found. Creating a new one.")
        with open(file_path, "w") as f:
            f.write(f"{property_name}={property_value}\n")
        return True

    lines = []
    updated = False
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip().startswith(f"{property_name}="):
                lines.append(f"{property_name}={property_value}\n")
                updated = True
            else:
                lines.append(line)
    
    if not updated:
        lines.append(f"\n{property_name}={property_value}\n") # Add if not found

    try:
        with open(file_path, 'w') as f:
            f.writelines(lines)
        return True
    except IOError as e:
        print(f"Error updating {file_path}: {e}")
        return False

def run_gradle_build(project_path: Path) -> Tuple[bool, str]:
    """
    Runs the Gradle build command in the specified project directory.
    Returns (success_boolean, output_string).
    """
    gradle_wrapper = "./gradlew" if (project_path / "gradlew").exists() else "gradle"
    
    try:
        # Use subprocess.run for better control, capturing output and checking return code
        result = subprocess.run(
            [gradle_wrapper, "build", "--stacktrace"], # --stacktrace for more error info
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False # Do not raise CalledProcessError for non-zero exit codes
        )
        success = result.returncode == 0
        return success, result.stdout + result.stderr
    except FileNotFoundError:
        return False, "Gradle or gradlew command not found. Ensure Gradle is installed or gradlew is executable."
    except Exception as e:
        return False, f"An unexpected error occurred during Gradle build: {e}"

def read_gradle_properties(file_path: Path) -> str:
    """Reads the content of gradle.properties."""
    if not file_path.exists():
        return ""
    with open(file_path, 'r') as f:
        return f.read()

def read_build_gradle(file_path: Path) -> str:
    """Reads the content of build.gradle."""
    if not file_path.exists():
        return ""
    with open(file_path, 'r') as f:
        return f.read()