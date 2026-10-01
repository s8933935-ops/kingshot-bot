import sys
import subprocess
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SESSION_ID = "533b4982-120f-4baa-b810-9c4dfe42570c"
PROJECT_DIR = r"C:\Users\s8933\projects\keiba-ai-simulator"

def main():
    if len(sys.argv) < 2:
        print("Usage: python claude_keiba_gate.py <prompt>")
        sys.exit(1)
        
    prompt = " ".join(sys.argv[1:])
    print(f"[claude_keiba_gate] 競馬予想シミュレーター基盤構築 ({SESSION_ID}) へ問い合わせ中...")
    
    cmd = ["claude.cmd", "--resume", SESSION_ID, "-p", prompt]
    try:
        proc = subprocess.run(
            cmd,
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        if proc.returncode == 0:
            print("\n======================================================")
            print("Claude（競馬予想シミュレーター基盤構築）からの監査回答")
            print("======================================================\n")
            print(proc.stdout)
            print("\n======================================================")
        else:
            print(f"[Error] Returncode: {proc.returncode}")
            print(f"Stdout: {proc.stdout}")
            print(f"Stderr: {proc.stderr}")
            sys.exit(proc.returncode)
    except Exception as e:
        print(f"[Exception] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
