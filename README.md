# 附近美食查詢｜Flask + OpenStreetMap + Vercel

使用 Python Flask 建立的簡易附近美食查詢網站。使用者可輸入地點或分享瀏覽器定位，查詢附近餐廳、咖啡廳與速食店。

## 功能

- Nominatim：將文字地點轉換為經緯度。
- Overpass API：查詢附近的 OSM 餐飲資料。
- 搜尋半徑：300m、500m、1000m。
- 類型篩選：全部、餐廳、咖啡廳、速食。
- 顯示店名、類型、料理種類、營業時間、地址與直線距離。
- 提供 Google Maps 與 OpenStreetMap 導航連結。
- 支援瀏覽器 Geolocation API。
- 不需要 API Key。

## 專案結構

```text
nearby-food-app/
├── api/
│   └── index.py
├── templates/
│   └── index.html
├── .env.example
├── .gitignore
├── .python-version
├── README.md
├── requirements.txt
└── vercel.json
```

## 本地執行（Python 3.11+）

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app api.index run --debug
```

瀏覽器開啟 http://127.0.0.1:5000

## 部署 Vercel

1. 將專案推送到 GitHub。
2. 在 Vercel 選擇 Add New → Project，匯入 GitHub Repository。
3. Root Directory 選專案根目錄，保留 vercel.json 設定。
4. 按下 Deploy。

## 注意事項

- 請將 api/index.py 中 User-Agent 的聯絡信箱改成可聯絡的信箱。
- Nominatim 公開服務有速率限制，正式上線請加入快取與節流。
- Overpass 公共服務繁忙時可能逾時。
- 距離為直線距離，不是道路或步行距離。
- 地圖資料來源：© OpenStreetMap contributors。
