# tools/

## selfcheck.mjs

日報的建置後自檢。**跑在 `build_index.py` 之後**——它驗的是拆完的產物，不是中英並排的原稿。

```bash
python3 build_index.py
npm install --no-save playwright
node tools/selfcheck.mjs 2026-08-25
```

沒給第二個參數就自己在 repo 根目錄起一個臨時 http server（CSS 是絕對路徑
`/assets/report.css`，用 `file://` 開抓不到樣式）。也可以指定現成的：

```bash
node tools/selfcheck.mjs 2026-08-25 http://localhost:8899
```

共 29 項，涵蓋中英兩份日報與兩份首頁：

| 驗什麼 | 為什麼 |
|---|---|
| 只剩自己語言的節點 | 拆不乾淨會讓一頁同時出現兩種語言 |
| `<html lang>` 與內文一致 | zh-Hant / en |
| canonical、og:url 各指自己 | 指錯比沒有更糟 |
| 三行 hreflang | zh-Hant / en / x-default |
| 語言切換是真的 `<a href>` | 並排版的按鈕在單語頁上沒意義 |
| 外部 CSS 實際載入（不是 404） | 監看 response，並確認沒殘留整段 inline CSS |
| 導覽元件齊全 | brand 連結、gh-star、頁尾社群、home-fab |
| 390px 無水平捲動 | 行動版可讀 |
| `↑` 與 home 不重疊、不超出畫面 | 捲到頁面下方時量兩者的位置 |
| 每張新聞卡片都有外部連結 | 「每一則具體資訊都就地附出處」的底線 |
| 兩份首頁份數一致且有今天的卡片 | 中英任一邊少一天都算錯 |

全過 `exit 0`；任一項失敗 `exit 1`，並在最後列出未通過的項目。CI 拿這個當守門步驟。

Chromium：會先找 `/opt/pw-browsers/chromium-*/chrome-linux/chrome`，找不到就用 Playwright 預設位置。
