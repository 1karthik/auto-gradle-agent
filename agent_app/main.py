# agent_app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import shutil
from pathlib import Path

from core_agent import GradleBuildFixingAgent

app = FastAPI(
    title="Gradle Build Fixer Agent",
    description="An agent to update Gradle properties and fix build errors using a local LLM."
)

class ProjectUpdateRequest(BaseModel):
    project_url: str  # e.g., "https://github.com/your-org/your-project.git"
    dependency_name: str
    dependency_value: str

# Define a temporary directory for cloning projects
TEMP_PROJECTS_DIR = Path("temp_projects")
TEMP_PROJECTS_DIR.mkdir(exist_ok=True)

@app.post("/update_and_build/")
async def update_and_build_project(request: ProjectUpdateRequest):
    project_name = request.project_url.split('/')[-1].replace(".git", "")
    project_path = TEMP_PROJECTS_DIR / project_name

    # 1. Clone the project (simplified - error handling and existing dir handling needed)
    if project_path.exists():
        shutil.rmtree(project_path) # Clean up previous clone for fresh start
    
    clone_command = f"git clone {request.project_url} {project_path}"
    print(f"Cloning project: {clone_command}")
    os.system(clone_command) # In a real app, use subprocess.run for better control

    if not project_path.exists():
        raise HTTPException(status_code=500, detail="Failed to clone project.")

    # Initialize the agent
    # Model path would likely come from an environment variable or config
    llm_model_path = os.getenv("LLM_MODEL_PATH", "./agent_app/models/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf")
    
    agent = GradleBuildFixingAgent(
        project_path=project_path,
        llm_model_path=llm_model_path
    )

    try:
        # 2. Update gradle.properties
        update_success = agent.update_gradle_properties(
            request.dependency_name,
            request.dependency_value
        )
        if not update_success:
            raise HTTPException(status_code=500, detail="Failed to update gradle.properties.")

        # 3. Run initial build and fix if needed
        build_result = await agent.run_and_fix_build()
        
        # 4. Clean up the cloned project (optional, depends on desired behavior)
        # shutil.rmtree(project_path)

        return {"status": "success", "message": "Project updated and built successfully (or fixed).", "build_details": build_result}

    except Exception as e:
        # Clean up in case of error too
        # shutil.rmtree(project_path)
        raise HTTPException(status_code=500, detail=str(e))

# To run this: uvicorn main:app --reload