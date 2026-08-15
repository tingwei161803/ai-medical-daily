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

每份日報固定包含：重點新聞 5–8 則、產品分析、公司狀況與競爭關係、台灣視角、延伸閱讀、參考文獻，並支援繁中／English 全頁切換與深色模式。每一則具體資訊都在原地附上來源連結。

---

## 結構

```
.
├── CNAME             ← 自訂網域設定，請勿刪除
├── index.html        ← 由 build_index.py 產生，請勿手動編輯
├── build_index.py    ← 掃描 reports/ 重建首頁
├── reports/
│   └── YYYY-MM-DD.html
└── README.md
```

⚠️ `CNAME` 由 GitHub Pages 的自訂網域設定產生，內容為 `ai-medical-daily.peteraim.com`。刪掉它網站就會退回 `*.github.io` 網址。

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

首頁功能：依日期倒序列表、主題標籤、關鍵字搜尋、主題篩選、月曆視圖、繁中／English 切換、深色模式、響應式排版。

重建索引（無第三方相依，Python 3 即可）：

```bash
python3 build_index.py
```

## 手動新增一份日報

```bash
cp 你的報告.html reports/2026-08-17.html
python3 build_index.py
git add -A && git commit -m "日報：2026-08-17" && git push
```

## 免責聲明

內容由 AI 蒐集整理並附上原始出處，但仍可能有誤。所有數據請以參考文獻中的原始來源為準。本 repo 內容不構成投資或醫療建議。
