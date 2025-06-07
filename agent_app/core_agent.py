# core_agent.py
import os
import subprocess
import tempfile
import re
from git import Repo
from langchain.agents import AgentExecutor, create_react_agent
from langchain.llms import LlamaCpp
from langchain.tools import Tool
from langchain_core.prompts import PromptTemplate
from llm_utils import ask_llm_for_fix
import time

MODEL_PATH = "C:\\Users\\karth\\models\\Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf"


def create_agent_executor():
    llm = LlamaCpp(
        model_path=MODEL_PATH,
        n_ctx=4096,
        temperature=0.5,
        verbose=True,
    )

    tools = [
        Tool(
            name="UpdateDependency",
            func=update_dependency,
            description="Updates the dependency version in gradle.properties"
        ),
        Tool(
            name="GradleBuild",
            func=run_gradle_build,
            description="Runs gradle build and returns output"
        ),
        Tool(
            name="FixBuild",
            func=apply_fix,
            description="Parses build error and applies fix in build.gradle or gradle.properties"
        ),
    ]

    prompt = PromptTemplate.from_template("""
You are a Gradle Build Fixing Agent. Your task is to help fix Gradle build issues by managing dependencies and analyzing build errors.

Available tools:
{tools}

Tool names: {tool_names}

For each step, follow this format:
Thought: What you're thinking about doing
Action: The tool to use
Action Input: The input for the tool
Observation: The result of the action

Example:
Thought: I need to update the Spring version in gradle.properties
Action: UpdateDependency
Action Input: {{"github_url": "https://github.com/user/repo.git", "dependency_name": "spring.version", "dependency_version": "5.3.0"}}
Observation: Dependency spring.version updated to version 5.3.0

Thought: Now I should run the build to check for errors
Action: GradleBuild
Action Input: {{"github_url": "https://github.com/user/repo.git"}}
Observation: Build failed with error: Could not resolve dependencies...

Thought: I need to analyze the error and apply a fix
Action: FixBuild
Action Input: Error: Could not resolve dependencies...
Observation: Fix applied to build.gradle

Remember to:
- Always check the build output for specific error messages
- Look for version conflicts in the error messages
- Consider compatibility between dependencies
- Verify your fixes by running the build again
- Log your thinking process at each step

{agent_scratchpad}
""")

    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=prompt,
    )

    return AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True
    )


def update_dependency(inputs):
    github_url = inputs.get("github_url")
    name = inputs.get("dependency_name")
    version = inputs.get("dependency_version")
    
    # Create temp directory in agent_app folder
    project_temp_dir = os.path.join(os.path.dirname(__file__), "temp")
    os.makedirs(project_temp_dir, exist_ok=True)
    
    # Create a unique directory for this repo
    repo_name = github_url.split("/")[-1].replace(".git", "")
    repo_dir = os.path.join(project_temp_dir, repo_name)
    
    print(f"\n[Step 1] Checking repository at {repo_dir}")
    
    # Clone repository only if it doesn't exist
    if not os.path.exists(repo_dir):
        print(f"[Step 1.1] Cloning repository {github_url}")
        try:
            Repo.clone_from(github_url, repo_dir)
            print(f"[Step 1.2] Successfully cloned repository to {repo_dir}")
        except Exception as e:
            print(f"[Step 1] Error during repository setup: {str(e)}")
            raise
    else:
        print(f"[Step 1.1] Repository already exists at {repo_dir}")

    print(f"[Step 2] Updating dependency {name} to version {version}")
    
    # Update dependency in gradle.properties
    gradle_props_path = os.path.join(repo_dir, "gradle.properties")
    if os.path.exists(gradle_props_path):
        with open(gradle_props_path, "r") as f:
            lines = f.readlines()
        
        updated = False
        with open(gradle_props_path, "w") as f:
            for line in lines:
                if line.strip().startswith(f"{name}="):
                    f.write(f"{name}={version}\n")
                    updated = True
                    print(f"[Step 3] Updated existing dependency in gradle.properties")
                else:
                    f.write(line)
            if not updated:
                f.write(f"\n{name}={version}\n")
                print(f"[Step 3] Added new dependency to gradle.properties")
    else:
        # Create gradle.properties if it doesn't exist
        with open(gradle_props_path, "w") as f:
            f.write(f"{name}={version}\n")
        print(f"[Step 3] Created new gradle.properties with dependency")

    return f"Dependency {name} updated to version {version} in {repo_dir}"


def run_gradle_build(inputs):
    github_url = inputs.get("github_url")
    repo_name = github_url.split("/")[-1].replace(".git", "")
    repo_dir = os.path.join(os.path.dirname(__file__), "temp", repo_name)
    
    print(f"\n[Step 4] Running Gradle build in {repo_dir}")
    
    try:
        # Check if gradlew.bat exists
        gradlew_path = os.path.join(repo_dir, "gradlew.bat")
        if not os.path.exists(gradlew_path):
            print("[Step 4.1] gradlew.bat not found, checking for gradlew")
            gradlew_path = os.path.join(repo_dir, "gradlew")
            if not os.path.exists(gradlew_path):
                return "Error: Gradle wrapper not found in the repository"

        # Make gradlew executable if it's not .bat
        if not gradlew_path.endswith('.bat'):
            os.chmod(gradlew_path, 0o755)

        # Run the build
        result = subprocess.run(
            [gradlew_path, "clean", "build"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print("[Step 5] Build succeeded")
            return "Build succeeded."
        else:
            print("[Step 5] Build failed. Analyzing error output...")
            error_output = result.stdout + "\n" + result.stderr
            print(f"Error output:\n{error_output}")
            return error_output
    except FileNotFoundError as e:
        error_msg = f"Build error: Required file not found - {str(e)}"
        print(f"[Step 5] {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = f"Build exception: {str(e)}"
        print(f"[Step 5] {error_msg}")
        return error_msg


def apply_fix(build_output: str):
    print("\n[Step 6] Analyzing build error and suggesting fix...")
    suggestion = ask_llm_for_fix(build_output)
    github_url = extract_repo_url(build_output)
    repo_name = github_url.split("/")[-1].replace(".git", "")
    repo_dir = os.path.join(os.path.dirname(__file__), "temp", repo_name)

    print(f"[Step 7] Suggested fix: {suggestion}")

    # Parse the LLM response
    try:
        error_type = suggestion.split("ERROR_TYPE:")[1].split("\n")[0].strip()
        file_to_modify = suggestion.split("FILE_TO_MODIFY:")[1].split("\n")[0].strip()
        fix = suggestion.split("FIX:")[1].strip()
        
        print(f"[Step 7.1] Parsed fix: Type={error_type}, File={file_to_modify}, Fix={fix}")
        
        if file_to_modify == "build.gradle":
            build_gradle_path = os.path.join(repo_dir, "build.gradle")
            if os.path.exists(build_gradle_path):
                with open(build_gradle_path, 'r') as f:
                    content = f.read()
                
                # Apply the fix
                if "implementation" in fix:
                    # Add new implementation
                    with open(build_gradle_path, 'a') as f:
                        f.write(f"\n{fix}\n")
                else:
                    # Replace existing implementation
                    fixed_content = re.sub(r'(implementation\s+\"[^"]+):\d+\.\d+\.\d+\"', fix, content)
                    with open(build_gradle_path, 'w') as f:
                        f.write(fixed_content)
                
                print("[Step 8] Fix applied to build.gradle")
                return "Fix applied to build.gradle."
        
        elif file_to_modify == "gradle.properties":
            gradle_props_path = os.path.join(repo_dir, "gradle.properties")
            if os.path.exists(gradle_props_path):
                with open(gradle_props_path, 'a') as f:
                    f.write(f"\n{fix}\n")
                print("[Step 8] Fix applied to gradle.properties")
                return "Fix applied to gradle.properties."
        
        print("[Step 8] No fix applied - could not find appropriate file to update")
        return "No fix applied."
        
    except Exception as e:
        print(f"[Step 8] Error applying fix: {str(e)}")
        return f"Error applying fix: {str(e)}"


def extract_repo_url(output):
    # Extract github URL from the output or use a default
    # This is a simplified version - you might want to enhance this
    return "https://github.com/1karthik/gradle-transitive-conflict-demo.git"  # Replace with actual URL extraction logic

