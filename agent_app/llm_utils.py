# agent_app/llm_utils.py
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.llms import LlamaCpp
import re

def create_llm_chain(llm: LlamaCpp) -> LLMChain:
    """
    Creates a LangChain LLMChain with a generic prompt for ReAct-style interaction.
    """
    # This prompt needs to be carefully designed for the LLM to understand ReAct steps.
    # The actual prompt used in core_agent.py will be more specific.
    prompt = PromptTemplate(
        input_variables=["error_output", "gradle_properties_content", "build_gradle_content"],
        template="" # The template will be provided dynamically in core_agent.py
    )
    return LLMChain(llm=llm, prompt=prompt)

def parse_gradle_error_for_llm(build_output: str) -> str:
    """
    Parses the Gradle build output to extract relevant error messages for the LLM.
    This is a simplification and would need more sophisticated parsing in a real scenario.
    """
    # Look for common error patterns
    error_patterns = [
        r"(?s)FAILURE: Build failed with an exception\.",
        r"(?s)\* What went wrong:(.*?)\* Try:",
        r"(?s)Could not resolve all dependencies for configuration ':(.*?)'",
        r"(?s)Execution failed for task '(.*?)'",
        r"(?s)Caused by:(.*?)(?:\n\n|\Z)",
        r"(?s)Error:(.*?)(?:\n\n|\Z)"
    ]

    extracted_errors = []
    for pattern in error_patterns:
        matches = re.findall(pattern, build_output, re.DOTALL | re.IGNORECASE)
        for match in matches:
            extracted_errors.append(match.strip())
            # Limit the amount of error output fed to the LLM to save context window
            if len("\n".join(extracted_errors)) > 1500: # Arbitrary limit
                break
        if len("\n".join(extracted_errors)) > 1500:
            break
            
    if extracted_errors:
        return "\n".join(extracted_errors)
    else:
        # If no specific patterns found, return a snippet of the end of the output
        lines = build_output.splitlines()
        return "\n".join(lines[-50:]) if len(lines) > 50 else build_output