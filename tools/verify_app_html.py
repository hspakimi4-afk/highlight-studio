#!/usr/bin/env python3
"""
highlight-studio-03-app.html(本体・音声認識/ffmpeg処理ページ)を、
外部CDN(cdn.jsdelivr.net)へのネットワークアクセスなしで実際に
ブラウザ実行して検証するためのスクリプト。

## これまでの経緯
03-app.htmlは `import { pipeline, env } from
"https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.0.0"` を
使ったESモジュールで、このCDNへのアクセスができないサンドボックス環境では
9回のレビューを通じて「静的な構造チェック(タグ対応・ID重複)はできるが、
実際にボタンを押したときの動作確認はできない」という制約が続いていた。

## このスクリプトでの解決方法
Playwrightの`page.route()`でCDNへのリクエストをインターセプトし、
`pipeline`/`env`の最小限のダミー実装(スタブ)をその場で返すことで、
モジュールの読み込み自体を成立させ、実際の音声認識モデルをダウンロード
せずに、UIのロジック(スタイル選択でハイライトボックス欄が出る、
ファイル選択でボタンが有効になる、等)を実際のブラウザで検証できるように
した。音声認識・ffmpeg変換そのものの動作(実際の書き出し結果の精度等)は
このスタブでは検証できないので、その部分は別途、実ネットワークが使える
環境での確認が必要。

## 使い方
    cd frontend
    python3 -m http.server 8899 &
    python3 ../tools/verify_app_html.py

前提: `pip install playwright && playwright install chromium`
(このリポジトリのrequirements.txtには含めていない。あくまで手動検証用ツール)
"""
import os
import sys
import tempfile

from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("HS_VERIFY_BASE_URL", "http://127.0.0.1:8899")

STUB_MODULE = b"""
export async function pipeline(){
  return async () => ({ text: '(stub) dummy transcription' });
}
export const env = { backends: { onnx: { wasm: {} } } };
"""


def run():
    console_errors = []
    page_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(5000)
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        page.route(
            "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.0.0",
            lambda route: route.fulfill(status=200, content_type="application/javascript", body=STUB_MODULE),
        )
        page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
        page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
        page.route("https://unpkg.com/**", lambda route: route.abort())

        # app.htmlは会員登録不要になり、ログイン状態のチェックは行わない。
        # 直接app.htmlを開いて検証する。
        page.goto(f"{BASE_URL}/highlight-studio-03-app.html", wait_until="load")
        page.wait_for_timeout(300)

        style_buttons = page.query_selector_all("#styleSegmented button")
        results = {}
        for btn in style_buttons:
            val = btn.get_attribute("data-val")
            btn.click()
            page.wait_for_timeout(100)
            results[val] = page.is_visible("#highlightBoxField")

        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.write(b"\x00" * 1024)
        tmp.close()
        page.set_input_files("#videoInput", tmp.name)
        page.wait_for_timeout(200)
        to_step2_enabled = not page.is_disabled("#toStep2Btn")
        os.unlink(tmp.name)

        browser.close()

    print("style -> highlightBoxField visible:", results)
    print("toStep2Btn enabled after file select:", to_step2_enabled)
    print("console errors:", console_errors)
    print("page errors:", page_errors)

    ok = (
        results.get("style2") is True
        and results.get("style1") is False
        and to_step2_enabled
        and not page_errors
    )
    print("RESULT:", "OK" if ok else "CHECK OUTPUT ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
