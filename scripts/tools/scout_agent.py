import requests
from bs4 import BeautifulSoup
import json
import time
import os

def autonomous_scout(query):
    print(f"[*] 「{query}」に関する自律調査を開始します...")
    
    # 実際にはGoogle Search APIなどを使いますが、ここでは主要な攻略キーワードから検索をシミュレート
    # 簡易版として、いくつかの攻略ハブサイトをターゲットにします
    targets = [
        "https://altema.jp/kingshot/",
        "https://kingshotguide.org/",
    ]
    
    knowledge_base = []
    
    for url in targets:
        try:
            print(f"[*] 巡回中: {url}")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # タイトルや最新ニュースのセクションを抽出（サイト構造に合わせて調整が必要）
                title = soup.title.string if soup.title else url
                # 簡易的にテキストを抽出
                text = ' '.join([p.get_text() for p in soup.find_all('p')[:5]])
                
                knowledge_base.append({
                    "source": title,
                    "url": url,
                    "content": text[:300] + "..."
                })
                print(f"[+] 情報を取得しました: {title}")
        except Exception as e:
            print(f"[!] エラーが発生しました ({url}): {e}")
        
        time.sleep(1) # サーバー負荷軽減

    # 結果をJSONとして保存（Webアプリが読み込めるように）
    output_path = "autonomous_knowledge.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(knowledge_base, f, ensure_ascii=False, indent=4)
    
    print(f"\n[OK] 調査完了。'{output_path}' にデータを保存しました。")

if __name__ == "__main__":
    search_query = input("調査したいキーワードを入力してください: ")
    autonomous_scout(search_query)
