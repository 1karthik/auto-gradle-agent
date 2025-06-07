# llm_utils.py
from langchain_community.llms import LlamaCpp

MODEL_PATH = "C:\\Users\\karth\\models\\Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf"

llm = LlamaCpp(
    model_path=MODEL_PATH,
    n_ctx=4096,
    temperature=0.5,
    verbose=True,
)

def ask_llm_for_fix(build_output):
    prompt = f"""
You are a Gradle build expert. The build failed with the following output:

{build_output}

Analyze the error and provide a fix. Follow these steps:
1. Identify the specific error type (dependency conflict, version mismatch, missing dependency, etc.)
2. Determine which file needs to be modified (build.gradle or gradle.properties)
3. Provide the exact change needed

Return your response in this format:
ERROR_TYPE: [type of error]
FILE_TO_MODIFY: [build.gradle or gradle.properties]
FIX: [exact line(s) to add or modify]

Rules for fixes:
1. For build.gradle:
   - If adding a new dependency, use: implementation 'group:artifact:version'
   - If updating a version, provide the complete implementation line
   - If fixing a conflict, provide the resolution strategy

2. For gradle.properties:
   - Use property=value format
   - Include the full property name
   - Add one property per line

Example responses:

For missing dependency:
ERROR_TYPE: Missing dependency
FILE_TO_MODIFY: build.gradle
FIX: implementation 'org.springframework.boot:spring-boot-starter-web:2.7.0'

For version conflict:
ERROR_TYPE: Version conflict
FILE_TO_MODIFY: build.gradle
FIX: implementation('org.springframework.boot:spring-boot-starter-web:2.7.0') {{ force = true }}

For property setting:
ERROR_TYPE: Missing property
FILE_TO_MODIFY: gradle.properties
FIX: spring.version=5.3.0

If you cannot determine a fix, respond with:
ERROR_TYPE: Unknown error
FILE_TO_MODIFY: none
FIX: Unable to determine fix from the error message
"""
    return llm.invoke(prompt).strip()
