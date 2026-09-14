# OAuth 日常維運

設定完成之後的事：授權多久會過期、過期了怎麼辦、測試使用者是什麼。
一次性的設定流程見 [youtube-setup.md](youtube-setup.md)。

---

## 目前的設定現況

| 項目 | 值 |
|---|---|
| Google Cloud 專案 | `YoutubeUploader` |
| 應用程式名稱（授權畫面顯示的） | `soundstage` |
| 發布狀態 | **測試**（刻意不發布，理由見下方） |
| 使用者類型 | 外部 |
| 測試使用者 | `joechiboo@gmail.com` |
| 授權範圍 | `https://www.googleapis.com/auth/youtube.upload` |
| client secret | `~/.config/soundstage/client_secret.json` |
| token 快取 | `~/.config/soundstage/token.json` |

隨時可以查：

```bash
uv run soundstage auth --status
```

---

## 有兩種 token，壽命差很多

`token.json` 裡同時存著兩個東西，搞混的話會誤判問題：

| | 壽命 | 過期時會怎樣 |
|---|---|---|
| **access token** | **1 小時** | 程式自動拿 refresh token 換新的，你完全不會察覺 |
| **refresh token** | **7 天**（測試模式的限制） | 需要重新走一次瀏覽器授權 |

所以「每小時就過期」是正常且無感的；真正會打擾到你的是**每 7 天一次**。

---

## 重新授權是自動的，你不用先跑 auth

`get_credentials()` 有三層處理，`upload` 和 `publish` 都會經過它：

```
1. 快取還有效        → 直接用
2. access token 過期 → 用 refresh token 自動換新的 → 存回 token.json
3. refresh 也失敗    → 印出「已快取的授權失效…」→ 自動開瀏覽器重新授權
```

也就是說，**平常照常下指令就好**：

```bash
uv run soundstage upload out.mp4 --meta meta.yaml
```

如果距離上次授權超過 7 天，它會自己在第 3 步開瀏覽器，你點兩下（選帳號 →
進階 → 前往）就會接續完成上傳，不需要中斷後重跑。

`soundstage auth` 只有在你想**預先**授權（例如待會要離線、或想先確認沒問題）
時才需要手動跑。

---

## 除了 7 天，還有哪些情況會讓授權失效

- **改 Google 帳號密碼**
- **在 [Google 帳戶的第三方應用程式](https://myaccount.google.com/permissions) 手動移除 soundstage 的存取權**
- **改動授權範圍**（在 Cloud Console 的「資料存取權」增減 scope）
- **超過 6 個月完全沒用**

這幾種情況的表現都一樣：`RefreshError` → 自動重新授權。處理方式不用變。

---

## 測試使用者

### 為什麼需要

發布狀態是「測試」時，**只有列在測試使用者名單上的 Google 帳號**能通過授權。
不在名單上的帳號會看到「**存取遭到封鎖**」，而錯誤訊息不會說原因是這個。

### 怎麼改

Cloud Console →「Google Auth Platform」→「**目標對象**」→ 測試使用者 →
`+ Add users`

- 上限 **100 位**，以應用程式的整個生命週期計算（加了又刪也算用掉）
- 只有你自己要用的話，一個就夠

### 換帳號上傳要注意

如果之後想改用別的 Google 帳號（例如另一個 YouTube 頻道）：

1. 先把新帳號加進測試使用者
2. `uv run soundstage auth --reset`（清掉舊 token，client secret 保留）
3. `uv run soundstage auth`，在瀏覽器選新帳號

---

## 手動指令

```bash
uv run soundstage auth              # 預先授權（需要時會開瀏覽器）
uv run soundstage auth --status     # 看 client secret 與 token 是否存在
uv run soundstage auth --reset      # 清掉 token，下次重新授權
uv run soundstage auth --no-browser # 遠端主機：改在終端機顯示授權網址
```

`--reset` 只刪 `token.json`，不會動到 `client_secret.json`，所以不用重做 Cloud
Console 那一整套。

---

## 疑難排解

| 症狀 | 原因與處理 |
|---|---|
| 「存取遭到封鎖」 | 這個帳號不在測試使用者名單上，或你在瀏覽器選錯了 Google 帳號 |
| 「Google 尚未驗證這個應用程式」 | **正常現象**，測試模式必然出現。點「進階」→「前往 soundstage（不安全）」 |
| 印出「已快取的授權失效…」然後開瀏覽器 | **正常現象**，就是 7 天到了在自動重新授權，點完就會接續 |
| 每次都要重新授權（不到 7 天） | `token.json` 沒寫成功。檢查 `~/.config/soundstage/` 的權限，或跑 `auth --status` 確認 |
| `找不到 OAuth client secret` | `client_secret.json` 路徑或檔名不對 |
| `缺少 YouTube 上傳所需的套件` | 跑 `uv sync --extra upload` |

---

## 什麼時候才該脫離測試模式

只有一種情況值得：**要做無人值守的排程自動上傳**。那時 7 天失效會是硬傷，
因為沒有人在旁邊點瀏覽器。

代價是 Google 要求先在「品牌」頁補齊**應用程式首頁連結、隱私權政策連結、
服務條款連結、已授權網域**，而網域還得先在 Search Console 驗證過——等於要為
一個自用 CLI 工具架一個網站。在那之前，測試模式加上自動重新授權已經夠用。

---

## ⚠️ 安全提醒

`client_secret.json` 和 `token.json` **都不能進版控**。
`.gitignore` 已經擋住 `client_secret*.json` 和 `token.json`，但它們本來就該放在
`~/.config/soundstage/` 而不是專案目錄裡。

另外，Windows 上這兩個檔案**沒有權限保護**：程式會呼叫 `chmod(0o600)`，但
Windows 不實作 POSIX 權限位元，實際落地是 `0o666`。實務上靠 `%USERPROFILE%`
自己的 ACL 擋住其他一般使用者，但那是繼承來的。細節見 [TODO.md](../TODO.md) 的 D 項。
