import os
import sys
import time
import re
import subprocess
import urllib.request
import signal
import webbrowser

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def cleanup_old_processes():
    """切れた時や再起動時に古いポート8000のプロセスやcloudflaredを掃除する"""
    if sys.platform == "win32":
        try:
            # 8000番ポートを使用しているプロセスを調査して終了
            out = subprocess.check_output('netstat -ano | findstr :8000', shell=True, text=True, stderr=subprocess.DEVNULL)
            for line in out.strip().splitlines():
                parts = line.split()
                if len(parts) >= 5 and "LISTENING" in parts:
                    pid = parts[-1]
                    if pid != "0" and int(pid) != os.getpid():
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
            # 古いcloudflaredも終了
            subprocess.run('taskkill /F /IM cloudflared.exe', shell=True, capture_output=True)
        except Exception:
            pass

def copy_to_clipboard(text):
    """URLをクリップボードに自動コピー"""
    if sys.platform == "win32":
        try:
            p = subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True)
            p.communicate(input=text.strip().encode('utf-8'))
        except Exception:
            pass

def main():
    print("=" * 60)
    print("[*] クオンツ投資シミュレーター Web公開サーバー起動スクリプト")
    print("=" * 60)

    # 0. Cleanup previous zombie processes
    print("\n[0/3] 前回の接続や残存プロセスをクリーンアップ中...")
    cleanup_old_processes()
    time.sleep(1)

    # 1. Start uvicorn
    print("\n[1/3] Uvicorn 内部サーバーを起動しています (ポート 8000)...")
    os.makedirs("scratch", exist_ok=True)
    uvicorn_log = open("scratch/uvicorn.log", "w", encoding="utf-8")
    uvicorn_cmd = [sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8000"]
    uvicorn_proc = subprocess.Popen(
        uvicorn_cmd,
        stdout=uvicorn_log,
        stderr=subprocess.STDOUT,
        text=True
    )

    # Health check
    server_ready = False
    for i in range(15):
        time.sleep(1)
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/", timeout=2) as resp:
                if resp.status == 200:
                    server_ready = True
                    print("✅ 内部サーバーが正常に応答しました (HTTP 200 OK)")
                    break
        except Exception:
            continue

    if not server_ready:
        print("❌ 内部サーバーの起動に失敗しました。詳細は scratch/uvicorn.log をご確認ください。")
        uvicorn_proc.kill()
        sys.exit(1)

    # 2. Start Cloudflare Tunnel
    print("\n[2/3] Cloudflare Tunnel で外部HTTPS通信路を確立しています...")
    cloudflared_path = r"C:\Program Files (x86)\cloudflared\cloudflared.exe"
    if not os.path.exists(cloudflared_path):
        cloudflared_path = "cloudflared"

    cf_log_path = os.path.abspath("scratch/cloudflared.log")
    if os.path.exists(cf_log_path):
        try:
            os.remove(cf_log_path)
        except Exception:
            pass

    cf_log = open(cf_log_path, "a+", encoding="utf-8")
    cf_cmd = [cloudflared_path, "tunnel", "--url", "http://127.0.0.1:8000"]
    cf_proc = subprocess.Popen(
        cf_cmd,
        stdout=cf_log,
        stderr=subprocess.STDOUT,
        text=True
    )

    public_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    # Read output file to find URL
    for _ in range(30):
        time.sleep(1)
        if os.path.exists(cf_log_path):
            with open(cf_log_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                match = url_pattern.search(content)
                if match:
                    public_url = match.group(0)
                    break

    if public_url:
        os.makedirs("scratch", exist_ok=True)
        with open("scratch/public_url.txt", "w", encoding="utf-8") as f:
            f.write(public_url)

        print("\n" + "=" * 60)
        print("🎉 【Web公開URLが発行されました！】")
        print(f"👉 {public_url}")
        print("=" * 60)
        print("※ このURLをスマホや外部PCのブラウザに入力すれば、どこからでもアクセスできます。")
        print("※ このウィンドウを開いたままにしている間、ずっとアクセス可能です。")
        print("※ 終了するには Ctrl+C を押してください。\n")
        copy_to_clipboard(public_url)
        print("📋 URLをクリップボードに自動コピーしました！")
        try:
            webbrowser.open(public_url)
        except Exception:
            pass
    else:
        print("❌ 公開URLの取得に失敗しました。")

    # Keep alive
    try:
        while True:
            time.sleep(1)
            if uvicorn_proc.poll() is not None:
                print("❌ Uvicorn プロセスが終了しました。")
                break
            if cf_proc.poll() is not None:
                print("❌ Cloudflared プロセスが終了しました。")
                break
    except KeyboardInterrupt:
        print("\n🛑 終了処理を実行中...")
    finally:
        cf_proc.kill()
        uvicorn_proc.kill()
        print("✅ サーバーを安全に停止しました。")

if __name__ == "__main__":
    main()
