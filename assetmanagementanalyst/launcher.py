import subprocess
import sys

def start():
    subprocess.run(["streamlit", "run", "assetmanagementanalyst/main.py"])

def dev():
    subprocess.run(["streamlit", "run", "assetmanagementanalyst/main.py", 
                   "--server.port=8501", "--server.address=localhost"])

if __name__ == "__main__":
    globals()[sys.argv[1]]()