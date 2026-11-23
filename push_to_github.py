import subprocess
import os

repo_dir = r"e:\SMT 7\Edge Intelligent and Computing\TUGAS BESAR"

def run(cmd_list, shell=False):
    p = subprocess.run(cmd_list, cwd=repo_dir, capture_output=True, text=True, shell=shell)
    print("CMD:", " ".join(cmd_list) if isinstance(cmd_list, list) else cmd_list)
    if p.stdout:
        print("STDOUT:", p.stdout.strip())
    if p.stderr:
        print("STDERR:", p.stderr.strip())
    return p.returncode

# 1. Retrieve token
p_cred = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n", text=True, capture_output=True)
token = None
for line in p_cred.stdout.splitlines():
    if line.startswith("password="):
        token = line.split("=", 1)[1]

print("Token found:", bool(token))

# 2. Init git
run(["git", "init", "-b", "main"])
run(["git", "config", "user.name", "Risa"])
run(["git", "config", "user.email", "ttsalitsatus@gmail.com"])

# 3. Add remote
auth_remote = f"https://x-access-token:{token}@github.com/taritsats/ESP32-EdgeAI-HAR-MPU6050.git"
run(["git", "remote", "remove", "origin"])
run(["git", "remote", "add", "origin", auth_remote])

# 4. Git add & commit
run(["git", "add", "-A"])
run(["git", "commit", "-m", "Initial commit: Complete Edge AI HAR System on ESP32 and MPU6050"])

# 5. Git push
print("\n--- Pushing to GitHub ---")
rc = run(["git", "push", "-u", "origin", "main", "--force"])
if rc == 0:
    print("\nSUCCESS! Successfully pushed to https://github.com/taritsats/ESP32-EdgeAI-HAR-MPU6050")
    # Reset remote back to clean URL without token embedded
    run(["git", "remote", "set-url", "origin", "https://github.com/taritsats/ESP32-EdgeAI-HAR-MPU6050.git"])
else:
    print("\nFailed with return code", rc)
