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
├── TEMPLATE.html     ← 中英並排原稿的骨架，複製它來寫新的一天
├── reports/
│   └── YYYY-MM-DD.html      ← 中文版
├── en/               ← 英文版，整個目錄都由 build_index.py 產生
│   ├── index.html
│   └── reports/YYYY-MM-DD.html
├── assets/report.css ← 日報共用樣式
├── tools/selfcheck.mjs         ← 建置後的自檢（中英兩版＋兩份首頁，29 項）
├── .github/workflows/build.yml ← push 之後自動建置、commit 產物、跑自檢
├── sitemap.xml       ← 由 build_index.py 產生，兩種語言的網址都列
└── README.md
```

`TEMPLATE.html` 放在根目錄是刻意的：`build_index.py` 只掃 `reports/`，所以它不會被拆、
不會進首頁、也不會進 sitemap，可以安心當參照。

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

## 自動建置

`.github/workflows/build.yml` 會在 `reports/`、`build_index.py`、`assets/`、`tools/`
有變動時自動跑起來，做四件事：

1. 執行 `build_index.py`（拆中英、重建兩份首頁、重寫 sitemap）
2. 把產物 commit 回 `main`
3. 確認沒有任何日報被跳過，且兩份首頁的卡片數 == 日報數、sitemap 網址數 == (日報數＋1)×2
4. 用 Playwright 跑 `tools/selfcheck.mjs` 驗最新那一天的中英兩版與兩份首頁

**所以推一份中英並排的日報到 `reports/` 就夠了**，另外四個檔（拆完的中英兩版、兩份
首頁、sitemap）不必自己產、也不必自己推。用 `GITHUB_TOKEN` 推的 commit 不會再觸發
workflow，不會有迴圈。

第 2 步刻意排在第 3、4 步之前：萬一真的有問題，讓「拆好的兩份」上線，也比讓「中英
並排的原稿」留在線上好——後者會中英文疊在一起顯示，而且根本沒有英文版網址。檢查失敗
時 workflow 會紅燈，GitHub 會寄通知。

⚠️ 沒有 `.github/workflows/build.yml` 的話就沒有這一段自動化，得自己在本機跑
`python3 build_index.py` 再把**五個**檔（拆完的中英兩版、兩份首頁、`sitemap.xml`）
一起推上去。GitHub App token 預設沒有 `workflows` 權限，所以這個檔通常只能用有
`workflow` scope 的憑證（或直接在網頁上建檔）加進來。

## 手動新增一份日報

日報寫成**一份中英並排的 HTML**——用 `span.zh`／`span.en` 成對包住兩種語言（行內的
短句用 `zh-inline`／`en-inline`），建置時會自動拆成兩個網址。**不需要自己準備 `en/`
那一份。** 直接從 `TEMPLATE.html` 複製一份來改最省事：

```bash
cp TEMPLATE.html reports/2026-08-17.html
# 換掉 <head> 的六個 meta，把 ★ 標的地方換成當天內容
git add -A && git commit -m "日報：2026-08-17" && git push
# → CI 會自動建置、commit 產物、跑自檢
```

想在本機先看結果（可選，CI 也會做一次）：

```bash
python3 build_index.py
npm install --no-save playwright && npx playwright install chromium
node tools/selfcheck.mjs 2026-08-17    # 全過 exit 0，任一項失敗 exit 1
```

⚠️ 原稿直接用瀏覽器開會看到中英文疊在一起、右上角語言切換沒反應——**這是正常的**。
`assets/report.css` 已經沒有「用 CSS 藏起另一種語言」的規則了（線上每一頁本來就只剩
一種語言）。不要為了「修好它」而加 inline CSS。版面對不對，等建置完再用 selfcheck 驗。

⚠️ `span.zh`／`span.en`／`span.zh-inline`／`span.en-inline` 這四個開標籤只能出現在
真的要成對的內容上。**連註解裡都不要寫出字面的開標籤**——建置時會逐個掃、找不到對應
的 `</span>` 就直接中止，**整個建置停擺**，不是只跳過那一份。要在文字裡提到它們，就
寫成 `span.zh` 這種形式。

### 一份日報要長什麼樣，才拆得開

| 要求 | 為什麼 |
|---|---|
| 中英文節點**成對**，而且 `zh`／`en` 與 `zh-inline`／`en-inline` **兩組分開各自相等**（不能互相抵銷） | 少一邊就會拆出一頁缺內容的頁面 |
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
