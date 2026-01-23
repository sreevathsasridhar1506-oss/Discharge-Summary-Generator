from fastapi import FastAPI
import os
import subprocess
from pydantic import BaseModel

app = FastAPI()

class Command(BaseModel):
    cmd: str
    cwd: str = None

@app.get("/file_system/read")
def read_file(path: str):
    if not os.path.exists(path):
        return {"error": "File not found"}
    with open(path, "r") as file:
        content = file.read()
    return {"content": content}

@app.post("/system/run")
def run_command(command: Command):
    try:
        result = subprocess.run(command.cmd, cwd=command.cwd, shell=True, capture_output=True, text=True)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/git/create_branch")
def create_branch(branch_name: str):
    try:
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        return {"message": f"Branch '{branch_name}' created successfully."}
    except subprocess.CalledProcessError as e:
        return {"error": str(e)}}

@app.post("/git/open_pr")
def open_pr(branch: str, title: str, body: str):
    try:
        subprocess.run(["gh", "pr", "create", "--title", title, "--body", body, "--base", "main", "--head", branch], check=True)
        return {"message": "Pull request created successfully."}
    except subprocess.CalledProcessError as e:
        return {"error": str(e)}}