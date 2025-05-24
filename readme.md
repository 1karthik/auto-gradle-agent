# Gradle Build Fixing Agent

This project provides a FastAPI-based agent that can update Gradle project properties and attempt to fix build failures using a local Large Language Model (LLM).

## Tech Stack

* **Python**
* **FastAPI**: For the web API.
* **LangChain**: For orchestrating the LLM and its tools.
* **Llama.cpp**: For running local GGUF models.
* **Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf**: The specific LLM used for reasoning and fixing.
* **ReAct-style Agent**: The core reasoning loop for the agent.

## Features

* Receive a project URL, dependency name, and value.
* Clone the specified project.
* Update `gradle.properties` with the new dependency version/value.
* Run a Gradle build.
* If the build fails, analyze the error using the local LLM.
* Attempt to apply fixes suggested by the LLM to `gradle.properties` or `build.gradle`.
* Retry the build after applying a fix.

## Setup Instructions

### 1. Prerequisites

* Python 3.9+
* Git (for cloning repositories)
* `make` (for `llama-cpp-python` compilation, especially with GPU support)
* C/C++ compiler (e.g., GCC, Clang)
* If you plan to use GPU acceleration for `llama-cpp-python`, ensure you have CUDA (for NVIDIA GPUs) or ROCm (for AMD GPUs) installed and correctly configured.

### 2. Clone the Repository (Conceptual)

```bash
git clone <this-repo-url>
cd <this-repo-name>