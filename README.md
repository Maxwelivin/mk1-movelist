# MK1 招式表（PS5）

Mortal Kombat 1 全角色招式表與基本操作表，按鍵已換成 PS5 預設鍵位。

- 網頁：https://maxwelivin.github.io/mk1-movelist/
- 收錄：本體 22 名、Kombat Pack 1 共 7 名、Khaos Reigns／Kombat Pack 2 共 6 名，另有 21 位 Kameo
- 內容：招式屬性（上／中／下段）與幀數、必殺技（含強化）、Fatal Blow、連段挑戰（遊戲教學的 Kombo Challenge，271 組）、Fatality／Animality（附官方繁中名稱）、普通技、Kombo、空中技、投技、Breaker、Brutality
- 功能：角色篩選、招式搜尋、「面向左」方向反轉、說明中文化
- iOS 主畫面 App（PWA，可離線）；角色圖片由使用者自行匯入、只存在自己的裝置（IndexedDB），本 repo 不含任何官方圖片

連段挑戰、招式屬性與幀數整理自 [Altar of Gaming](https://altarofgaming.com/character/scorpion/mortal-kombat-1/moves/)。

資料整理自 [MKKomplete](https://icemantraveler.github.io/mkksg/mk12/default.htm) 與 [Mortal Kombat Warehouse](https://www.mortalkombatwarehouse.com/mk12/moves/special/)，兩邊交叉比對，不一致處在頁面上以 ⚠ 標示。非官方整理；Mortal Kombat 為 Warner Bros. 商標。

## 重建

```
python -I -X utf8 _src/parse.py _raw _src/data.json
python -I -X utf8 _src/crosscheck.py _raw _src
python -I -X utf8 _src/parse_trials.py _raw/aog _src
python -I -X utf8 _src/parse_frames.py _raw/aog _src
python -I -X utf8 _src/build.py _src dist/index.html
python -X utf8 _src/make_icons.py _src/pwa
python -X utf8 _src/check.py dist/index.html _shots
python -X utf8 _src/test_v9.py dist <圖片包> _shots   # 圖片包由 make_imgpack.py 產生，僅供私人使用，不得提交
```

`_raw/` 放下載的來源頁面（不納入版本控制）。
