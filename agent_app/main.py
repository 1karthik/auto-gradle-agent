# main.py
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from core_agent import create_agent_executor, update_dependency, run_gradle_build, apply_fix
import os
from git import Repo

app = FastAPI()

class FixRequest(BaseModel):
    github_url: str
    dependency_name: str
    dependency_version: str

@app.post("/fix")
def fix_dependency(request: FixRequest):
    print("\n[API] Starting dependency fix process...")
    
    # Step 1: Download project to agent_app/temp
    temp_dir = os.path.join(os.path.dirname(__file__), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    repo_name = request.github_url.split("/")[-1].replace(".git", "")
    repo_dir = os.path.join(temp_dir, repo_name)
    
    print(f"[API] Cloning repository to {repo_dir}")
    if os.path.exists(repo_dir):
        import shutil
        shutil.rmtree(repo_dir)
    Repo.clone_from(request.github_url, repo_dir)
    
    # Step 2: Update dependency version
    print(f"[API] Updating dependency {request.dependency_name} to version {request.dependency_version}")
    update_result = update_dependency({
        "github_url": request.github_url,
        "dependency_name": request.dependency_name,
        "dependency_version": request.dependency_version
    })
    
    # Step 3: Run initial Gradle build
    print("[API] Running initial Gradle build")
    build_result = run_gradle_build({"github_url": request.github_url})
    
    # Step 4: If build failed, try fixes with retry logic
    if "Build succeeded" not in build_result:
        print("[API] Initial build failed, starting fix attempts...")
        max_attempts = 3
        attempt = 1
        last_fix_result = None
        
        while attempt <= max_attempts:
            print(f"\n[API] Fix attempt {attempt} of {max_attempts}")
            
            # Get LLM suggestion and apply fix
            fix_result = apply_fix(build_result)
            print(f"[API] Fix result: {fix_result}")
            
            if "Error applying fix" in fix_result or "No fix applied" in fix_result:
                print("[API] No valid fix received from LLM, stopping attempts")
                break
                
            last_fix_result = fix_result
            
            # Run build again to verify fix
            print(f"[API] Running build after fix attempt {attempt}")
            build_result = run_gradle_build({"github_url": request.github_url})
            
            if "Build succeeded" in build_result:
                print(f"[API] Build succeeded after {attempt} fix attempts")
                break
                
            attempt += 1
        
        return {
            "initial_build": build_result,
            "fix_attempts": attempt - 1,
            "last_fix_applied": last_fix_result,
            "final_build": build_result,
            "repo_location": repo_dir,
            "status": "success" if "Build succeeded" in build_result else "failed"
        }
    
    return {
        "build_result": build_result,
        "repo_location": repo_dir,
        "status": "success"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
