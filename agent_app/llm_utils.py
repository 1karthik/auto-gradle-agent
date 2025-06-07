# llm_utils.py
from langchain_community.llms import LlamaCpp

MODEL_PATH = "C:\\Users\\karth\\models\\Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf"

llm = LlamaCpp(
    model_path=MODEL_PATH,
    n_ctx=8192,
    temperature=0.2,
    verbose=True,
)

def ask_llm_for_fix(build_output):
    prompt = f"""
{build_output}

The error says to change Spring Boot version to one that supports JVM 11. 

COPY AND PASTE EXACTLY THESE THREE LINES, DO NOT MODIFY THEM:

ERROR_TYPE: JVM compatibility
FILE_TO_MODIFY: build.gradle
FIX: implementation 'org.springframework.boot:spring-boot-starter-web:2.7.0'

DO NOT ADD ANY OTHER TEXT. DO NOT EXPLAIN. JUST THOSE THREE LINES.
"""
    return llm.invoke(prompt).strip()
