# agent_app/core_agent.py
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from langchain_community.llms import LlamaCpp
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from gradle_utils import (
    update_gradle_property,
    run_gradle_build,
    read_gradle_properties,
    read_build_gradle
)
from llm_utils import create_llm_chain, parse_gradle_error_for_llm


class GradleBuildFixingAgent:
    def __init__(self, project_path: Path, llm_model_path: str):
        self.project_path = project_path
        self.llm_model_path = llm_model_path
        self.llm = self._initialize_llm()
        self.llm_chain = create_llm_chain(self.llm) # LLMChain for ReAct reasoning

    def _initialize_llm(self):
        # Ensure the model exists
        if not Path(self.llm_model_path).exists():
            raise FileNotFoundError(f"LLM model not found at: {self.llm_model_path}")
        
        return LlamaCpp(
            model_path=self.llm_model_path,
            temperature=0.7,
            max_tokens=2048,
            n_ctx=4096, # Context window size
            n_gpu_layers=-1, # Uncomment and set to number of GPU layers if you have GPU and llama-cpp-python is built with GPU support
            n_batch=512,
            verbose=False,
        )

    def update_gradle_properties(self, name: str, value: str) -> bool:
        """
        Updates a property in gradle.properties.
        """
        gradle_properties_path = self.project_path / "gradle.properties"
        return update_gradle_property(gradle_properties_path, name, value)

    async def run_and_fix_build(self) -> Dict[str, Any]:
        """
        Runs the Gradle build, and if it fails, attempts to fix it using the LLM.
        """
        max_attempts = 3
        for attempt in range(max_attempts):
            print(f"Attempt {attempt + 1}: Running Gradle build...")
            build_success, build_output = run_gradle_build(self.project_path)

            if build_success:
                print("Gradle build successful!")
                return {"success": True, "output": build_output, "attempts": attempt + 1}
            else:
                print(f"Gradle build failed. Attempting to fix (Attempt {attempt + 1})...")
                error_details_for_llm = parse_gradle_error_for_llm(build_output)

                # ReAct-style prompt for the LLM
                current_gradle_properties = read_gradle_properties(self.project_path / "gradle.properties")
                current_build_gradle = read_build_gradle(self.project_path / "build.gradle")

                # Construct the prompt for the LLM
                # This is a simplified ReAct prompt. A real one would be more sophisticated
                # and involve a proper LangChain Agent with tools.
                prompt_template = PromptTemplate(
                    template="""
                    You are an expert Gradle build engineer and a helpful AI assistant.
                    A Gradle build has failed with the following error:
                    --- ERROR ---
                    {error_output}
                    --- END ERROR ---

                    Here is the current content of gradle.properties:
                    --- GRADLE.PROPERTIES ---
                    {gradle_properties_content}
                    --- END GRADLE.PROPERTIES ---

                    Here is the current content of build.gradle:
                    --- BUILD.GRADLE ---
                    {build_gradle_content}
                    --- END BUILD.GRADLE ---

                    Your task is to identify the problem and provide a precise fix.
                    Think step-by-step.
                    If the fix involves modifying `gradle.properties`, provide the exact new line or modified line.
                    If the fix involves modifying `build.gradle`, provide the exact new or modified block/line.
                    If no change is needed or you can't fix it, state "NO_FIX".

                    Response format:
                    Observation: <What you observe from the error>
                    Thought: <Your reasoning process>
                    Action: <The action you will take, e.g., "MODIFY_GRADLE_PROPERTIES" or "MODIFY_BUILD_GRADLE" or "NO_FIX">
                    Action_Input_File: <gradle.properties or build.gradle (if Action is MODIFY_*)>
                    Action_Input_Content: <The exact content to update/add/replace (if Action is MODIFY_*). Be precise with line numbers if applicable or just the content for replacement/addition.>
                    """,
                    input_variables=["error_output", "gradle_properties_content", "build_gradle_content"]
                )
                
                # Execute the LLM chain
                llm_response = self.llm_chain.run(
                    error_output=error_details_for_llm,
                    gradle_properties_content=current_gradle_properties,
                    build_gradle_content=current_build_gradle
                )
                
                print(f"LLM Response:\n{llm_response}")

                # Parse LLM's action and apply fix
                parsed_action = self._parse_llm_response(llm_response)

                if parsed_action and parsed_action["action"] != "NO_FIX":
                    fix_applied = False
                    if parsed_action["action"] == "MODIFY_GRADLE_PROPERTIES":
                        print("Applying fix to gradle.properties...")
                        # This part needs sophisticated logic to apply the specific change from LLM
                        # For now, a very basic "append or replace" is shown.
                        # A real solution might need line-by-line replacement or regex.
                        gradle_properties_path = self.project_path / "gradle.properties"
                        content_to_apply = parsed_action["content"]
                        # This is highly simplified. A real solution needs to intelligently merge/replace.
                        with open(gradle_properties_path, "a") as f: # Appending for simplicity
                             f.write(f"\n# LLM suggested fix:\n{content_to_apply}\n")
                        fix_applied = True
                        
                    elif parsed_action["action"] == "MODIFY_BUILD_GRADLE":
                        print("Applying fix to build.gradle...")
                        build_gradle_path = self.project_path / "build.gradle"
                        content_to_apply = parsed_action["content"]
                        # This is highly simplified. A real solution needs to intelligently merge/replace.
                        with open(build_gradle_path, "a") as f: # Appending for simplicity
                            f.write(f"\n// LLM suggested fix:\n{content_to_apply}\n")
                        fix_applied = True
                    
                    if fix_applied:
                        print("Fix applied. Retrying build...")
                        continue # Retry the build
                    else:
                        print("LLM suggested a fix but it couldn't be applied programmatically.")
                        return {"success": False, "output": build_output, "reason": "LLM fix parsing/application failed."}
                else:
                    print("LLM indicated no fix or could not determine one.")
                    return {"success": False, "output": build_output, "reason": "LLM could not provide a fix."}
        
        print("Max attempts reached. Build still failing.")
        return {"success": False, "output": build_output, "reason": "Max build attempts reached."}

    def _parse_llm_response(self, response: str) -> Optional[Dict[str, str]]:
        """
        Parses the LLM's ReAct-style response to extract the action and its input.
        This needs robust regex parsing based on the prompt's expected format.
        """
        action_match = re.search(r"Action:\s*(.+)", response)
        action_input_file_match = re.search(r"Action_Input_File:\s*(.+)", response)
        action_input_content_match = re.search(r"Action_Input_Content:\s*([\s\S]+)", response)

        if action_match and action_input_file_match and action_input_content_match:
            action = action_match.group(1).strip()
            action_input_file = action_input_file_match.group(1).strip()
            action_input_content = action_input_content_match.group(1).strip()
            return {
                "action": action,
                "file": action_input_file,
                "content": action_input_content
            }
        elif action_match and action_match.group(1).strip() == "NO_FIX":
             return {"action": "NO_FIX"}
        else:
            print("Warning: Could not fully parse LLM response.")
            return None