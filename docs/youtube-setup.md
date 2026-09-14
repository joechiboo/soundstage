# YouTube 上傳設定

一次性設定，約 10 分鐘。步驟 1–6 全部要在瀏覽器或你自己的機器上做，
沒有 CLI 的替代做法。

每做完一步都可以跑這行確認進度：

```bash
uv run soundstage auth --status
```

還沒開始時它會顯示：

```
client secret：C:\Users\joechiboo\.config\soundstage\client_secret.json（不存在）
token 快取：  C:\Users\joechiboo\.config\soundstage\token.json（不存在）
```

---

## 步驟 1：建立專案並啟用 API

1. 開 [console.cloud.google.com](https://console.cloud.google.com/)
2. 左上角專案選單 → **新增專案** → 取個名字（例如 `soundstage`）→ 建立
3. 確認右上角已切換到這個新專案
4. 左側「**API 和服務**」→「**程式庫**」
5. 搜尋 **YouTube Data API v3** → 點進去 → **啟用**

✅ **檢查點**：「API 和服務」→「已啟用的 API」裡看得到 YouTube Data API v3

---

## 步驟 2：品牌（應用程式名稱）

Google 已把舊的單一頁面「OAuth 同意畫面」改版成「**Google Auth Platform**」，
設定拆散在左側幾個分頁裡。對照表：

| 舊介面 | 新介面（左側選單） |
|---|---|
| OAuth 同意畫面 → 應用程式名稱、支援信箱 | **品牌** |
| OAuth 同意畫面 → User Type、測試使用者、發布狀態 | **目標對象** |
| OAuth 同意畫面 → 新增或移除範圍 | **資料存取權** |
| 憑證 → 建立 OAuth 用戶端 ID | **用戶端** |

網址直接進：`console.cloud.google.com/auth/overview?project=<你的專案ID>`

先確認這個專案乾不乾淨：點左側「**用戶端**」，列表是空的就代表沒有別的東西在
用這個同意畫面，可以安心設定。（同意畫面是一個專案共用一份，底下所有 OAuth
用戶端都套用它。）

然後到「**品牌**」填：

- 應用程式名稱：`soundstage` ← 這個名字會出現在你授權時看到的畫面上
- 使用者支援電子郵件：你的 Gmail
- 開發人員聯絡資訊：你的 Gmail

沒設定過的話這裡會先要你選 User Type，個人 Gmail 帳號選 **外部**。

✅ **檢查點**：「品牌」頁存得起來，沒有紅字必填欄位

---

## 步驟 3：資料存取權（加入範圍）

左側「**資料存取權**」→「**新增或移除範圍**」

範圍清單很長，直接用下方的「手動新增範圍」貼上：

```
https://www.googleapis.com/auth/youtube.upload
```

→ 新增至表格 → 更新 → 儲存

這個範圍會被標示為「**敏感**」，正常。

✅ **檢查點**：「資料存取權」頁的範圍列表裡看得到 `youtube.upload`

---

## 步驟 4：目標對象（測試使用者）

左側「**目標對象**」→「**+ Add users**」→ 把你自己的 Gmail 加進測試使用者 → 儲存。

加完「OAuth 使用者人數上限」會顯示 `1 位測試使用者`。

> ⚠️ 漏掉這步的話，步驟 7 授權時會直接被擋，而錯誤訊息不會告訴你原因是這個。

### 發布狀態就留在「測試」

同一頁上方的「**發布應用程式**」按鈕會是**灰的**，旁邊寫著
「To publish your app, you must complete your configuration on the Branding page」。
這是正常的，**不用去解**。

要發布成正式版，Google 會要求「品牌」頁補齊**應用程式首頁連結、隱私權政策連結、
服務條款連結、已授權網域**，而網域還得先在 Search Console 驗證過。對一個自用的
CLI 工具來說，等於要為此架一個網站。

**代價 vs 好處**：留在「測試」的唯一缺點是 refresh token **7 天後失效**。實際影響是：

> 想上傳時照常下 `upload` 指令即可。如果距離上次授權超過 7 天，程式會自動
> 開瀏覽器請你重新授權（點兩下，約 20 秒），然後接續完成上傳——不需要中斷
> 後重跑。細節見 [oauth-operations.md](oauth-operations.md)。

一年傳幾支的話，這比去架網站、寫隱私權政策、驗證網域划算太多。

**什麼時候才該發布**：真的要做無人值守的排程自動上傳時。那時 7 天失效會是硬傷，
才值得回來處理首頁與隱私權政策這些要求。

✅ **檢查點**：測試使用者列表裡有你的信箱

---

## 步驟 5：建立用戶端

左側「**用戶端**」→「**建立用戶端**」

- 應用程式類型：**電腦版應用程式**（介面上的字；英文是 Desktop app）
  ← 必須是這個，選成「網頁應用程式」的話 `run_local_server` 會因 redirect URI 對不上而失敗
- 名稱隨意

名稱隨意（例如 `soundstage cli`）。

建立後會跳出對話框顯示用戶端 ID 與密鑰，那裡有「**下載 JSON**」；
沒按到也沒關係，回用戶端列表點進去，右上角一樣有。

---

## 步驟 6：把憑證放到定位

```bash
mkdir -p ~/.config/soundstage
mv ~/Downloads/client_secret_*.json ~/.config/soundstage/client_secret.json
```

Windows 上這個目錄是 `C:\Users\<你>\.config\soundstage`。

也可以放在別的地方，用環境變數指過去：

```bash
export SOUNDSTAGE_CLIENT_SECRET=/path/to/client_secret.json
```

✅ **檢查點**：`uv run soundstage auth --status` 的 client secret 那行不再是「不存在」

---

## 步驟 7：授權

```bash
uv sync --extra upload   # 上傳相依是選用的，沒裝過要先裝
uv run soundstage auth
```

會發生的事：

1. 瀏覽器自動開啟（遠端主機請加 `--no-browser`，改在終端機顯示網址）
2. 選你的 Google 帳號
3. 看到「**Google 尚未驗證這個應用程式**」
   → 點「**進階**」→「**前往 soundstage（不安全）**」
   這是你自己建的 app，正常現象
4. 勾選權限 → 繼續
5. 終端機顯示授權完成

✅ **檢查點**：`uv run soundstage auth --status` 兩行都不再是「不存在」

---

## 之後每次怎麼用

```bash
# render 完再上傳
uv run soundstage upload out.mp4 --meta meta.yaml

# 或一行做完
uv run soundstage publish "菊次郎の夏 Part I.aac" --meta meta.yaml --visual waveform
```

token 過期會自動用 refresh token 更新，不用再登入。
授權被撤銷（改密碼、手動移除授權）或測試模式的 7 天期限到了，會自動重跑一次
授權流程。

📄 **設定完成後的日常維運**（token 壽命、重新授權、測試使用者管理）見
[oauth-operations.md](oauth-operations.md)。

---

## 已知限制

### 上傳的影片可能被強制鎖成 private

YouTube 對**未通過 API 稽核**的專案有這個限制：不管 `meta.yaml` 裡的 `privacy`
設什麼，上傳後影片都會是 private。

要解除得申請 YouTube API Services 稽核（要填表、說明用途、等審核）。

**實務上的繞法**：上傳後到 [YouTube Studio](https://studio.youtube.com/) 手動改
公開狀態 —— 那是可以改的。一年傳幾支的話，不值得為此去申請稽核。

### 每日配額

預設 10,000 點，**上傳一支影片約 1,600 點**，所以一天大約只能傳 6 支。
超過會收到 HTTP 403 `quotaExceeded`，太平洋時間午夜重置。

### Windows 上 token 檔沒有權限保護

`save_credentials()` 會呼叫 `chmod(0o600)`，但 Windows 不實作 POSIX 權限位元，
這是無效操作，實際落地是 `0o666`。實務上靠 `%USERPROFILE%` 自己的 ACL 擋住
其他一般使用者，但那是繼承來的保護。細節見 [TODO.md](../TODO.md) 的 D 項。

---

## 疑難排解

| 症狀 | 原因 |
|---|---|
| 授權時被擋，說沒有權限 | 步驟 4 的**測試使用者**沒加自己 |
| 每週都要重新授權 | 測試模式的正常行為，重跑 `soundstage auth` 即可，見步驟 4 |
| `找不到 OAuth client secret` | 步驟 6 的路徑或檔名不對，跑 `auth --status` 看它期待的位置 |
| `缺少 YouTube 上傳所需的套件` | 沒跑 `uv sync --extra upload` |
| `run_local_server` 卡住或失敗 | 步驟 5 的應用程式類型選錯，必須是**電腦版應用程式** |
| 「發布應用程式」按鈕是灰的 | 正常現象，不用解，見步驟 4 |
| 上傳成功但影片是 private | 見上方「已知限制」，到 Studio 手動改 |
| HTTP 403 `quotaExceeded` | 當天配額用完，隔天再試 |

想從頭來過：

```bash
uv run soundstage auth --reset   # 只清 token，client secret 保留
```

---

## ⚠️ 著作權提醒

《菊次郎の夏》是久石讓 1999 年的作品，仍在著作權保護期內。鋼琴翻彈上傳到
YouTube 大機率會被 Content ID 比對到 —— 通常不是下架，而是廣告收益歸權利方，
但也可能在部分國家被封鎖。

建議第一支先用 `privacy: private` 傳上去，看系統怎麼判定，再決定要不要公開。
`meta.yaml` 的預設值就是 `private`。
