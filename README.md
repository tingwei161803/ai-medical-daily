# AI／醫療AI 每日新知日報

每天台北時間早上 08:00 由 Claude 自動產出並推送至此 repo，透過 GitHub Pages 發佈。

**線上閱讀：** https://ai-medical-daily.peteraim.com

---

## 每天輪值主題

| 星期 | 主題 | `report-theme` | `ci` |
|---|---|---|---|
| 一 | 臨床應用與研究 | `clinical` | 0 |
| 二 | 產業與商業動向 | `industry` | 1 |
| 三 | 法規與政策 | `regulation` | 2 |
| 四 | 技術突破 | `technology` | 3 |
| 五 | 產品與公司深度分析 | `product` | 4 |
| 六 | 廣義 AI 新知 | `general-ai` | 5 |
| 日 | 本週回顧與精選延伸閱讀 | `weekly-review` | 6 |

每份日報固定包含：重點新聞 5–8 則、產品分析、公司狀況與競爭關係、台灣視角、延伸閱讀、參考文獻，並支援繁中／English 與深色模式。每一則具體資訊都在原地附上來源連結。

---

## 一個語言一個網址

繁中與 English **各有自己的網址**，不是同一頁切換：

| | 中文 | English |
|---|---|---|
| 首頁 | `/` | `/en/` |
| 日報 | `/reports/YYYY-MM-DD.html` | `/en/reports/YYYY-MM-DD.html` |

每一頁**只有一種語言的節點**（另一種是真的刪掉，不是用 CSS 藏起來），`<html lang>`
與內文一致，`<head>` 帶 canonical（指自己）、三行 hreflang（`zh-Hant` / `en` /
`x-default` 指中文版）與 `og:url`，右上角的語言切換是真的 `<a href>`。

這些都不必手動維護——**`build_index.py` 會在建置時產生**，見下方〈索引如何運作〉。

## 結構

```
.
├── CNAME             ← 自訂網域設定，請勿刪除
├── index.html        ← 由 build_index.py 產生，請勿手動編輯
├── build_index.py    ← 掃描 reports/ 重建整個站台
├── reports/
│   └── YYYY-MM-DD.html      ← 中文版
├── en/               ← 英文版，整個目錄都由 build_index.py 產生
│   ├── index.html
│   └── reports/YYYY-MM-DD.html
├── assets/report.css ← 日報共用樣式
├── sitemap.xml       ← 由 build_index.py 產生，兩種語言的網址都列
└── README.md
```

⚠️ `CNAME` 由 GitHub Pages 的自訂網域設定產生，內容為 `ai-medical-daily.peteraim.com`。刪掉它網站就會退回 `*.github.io` 網址。

⚠️ `en/` 底下的檔案不要手動編輯，下次建置會被覆蓋。要改英文內容，改 `reports/` 裡
那一份的英文節點，再跑一次 `build_index.py`。

## 索引如何運作

`build_index.py` 讀取每份日報 `<head>` 內的 meta 標籤來建立首頁清單：

```html
<meta name="report-date"       content="2026-08-16">
<meta name="report-theme"      content="weekly-review">
<meta name="report-title-zh"   content="中文標題">
<meta name="report-title-en"   content="English headline">
<meta name="report-summary-zh" content="一句話中文摘要">
<meta name="report-summary-en" content="One-line English summary">
```

缺少 meta 的檔案會退回用檔名 `YYYY-MM-DD.html` 判斷日期；完全無法解析的會被跳過並在執行時印出提示。

首頁功能：依日期倒序列表、主題標籤、關鍵字搜尋、主題篩選、月曆視圖、繁中／English、深色模式、響應式排版。首頁清單在建置時就寫進 HTML，不必等 JavaScript 跑完才看得到。

重建整個站台（無第三方相依，Python 3 即可）：

```bash
python3 build_index.py
```

它會做三件事：把還是中英並排的日報拆成中文版與 `en/` 版、重建兩種語言的首頁、重寫 `sitemap.xml`。**已經拆過的日報不會再被動**，所以重複執行是安全的。

## 手動新增一份日報

日報照舊寫成**一份中英並排的 HTML**——用 `<span class="zh">`／`<span class="en">`
成對包住兩種語言（行內的短句用 `zh-inline`／`en-inline`），建置時會自動拆成兩個
網址。**不需要自己準備 `en/` 那一份。**

```bash
cp 你的報告.html reports/2026-08-17.html
python3 build_index.py
git add -A && git commit -m "日報：2026-08-17" && git push
```

### 一份日報要長什麼樣，才拆得開

| 要求 | 為什麼 |
|---|---|
| 中英文節點**成對**：`<span class="zh">`／`<span class="en">`（行內短句用 `zh-inline`／`en-inline`） | 少一邊就會拆出一頁缺內容的頁面 |
| `<head>` 有 `report-title-en` 與 `report-summary-en` | 英文版的標題與描述取自這兩個 |
| 右上角有**一組**語言切換（`<div class="seg">…</div>`，裡面是按鈕或連結都可以） | 會整塊換成指向這一天另一個語言的連結 |

**對不上就跳過那一份，不會中斷建置，也不會硬拆。** 例如：

```
  ! 跳過 reports/2026-08-18.html：缺 <meta name="report-summary-en">，英文版會少掉標題或描述
    這一份維持原樣、不產生英文版，也不會進英文首頁與 sitemap。
```

被跳過的那一天維持中英並排的原樣等人處理，其餘日報照常拆。因為它不會進英文首頁
也不會進 sitemap，所以不會留下連到 404 的網址。補好上表缺的東西再跑一次就會拆開。

## 免責聲明

內容由 AI 蒐集整理並附上原始出處，但仍可能有誤。所有數據請以參考文獻中的原始來源為準。本 repo 內容不構成投資或醫療建議。
