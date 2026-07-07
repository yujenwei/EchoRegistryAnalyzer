# Echo Registry Analyzer (ERA)

Version 0.4.3

## 使用方式

1. 將所有 Excel 放入 `input/`
2. 安裝套件：

```bash
pip install -r requirements.txt
```

3. 執行：

```bash
python run.py
```

## 目前輸出

### 基本整理

- `output/merged_all.xlsx`
- `output/patient_summary.xlsx`
- `output/birthday_conflict.xlsx`
- `output/gender_conflict.xlsx`
- `output/data_quality.xlsx`

### 疾病分類

- `output/disease_summary.xlsx`
- `output/disease_statistics.xlsx`
- `output/disease_reports/PDA.xlsx`
- `output/disease_reports/VSD.xlsx`
- `output/disease_reports/ASD.xlsx`
- `output/disease_reports/Impaired_myocardial_performance.xlsx`
- 其他疾病報表

## 原始欄位

目前預期欄位：

- 檢查日期
- 病歷號碼
- 姓名
- 性別
- 出生日期
- 檢查項目
- 診斷
- 報告

## 疾病字典

請修改：

```text
dictionary/diseases.json
```

新增疾病時，只要加入：

```json
"新疾病": {
  "keywords": ["keyword1", "keyword2"],
  "exclude": ["no keyword1"]
}
```

若需要 LVEF 條件：

```json
"Impaired myocardial performance": {
  "keywords": ["myocarditis", "heart failure"],
  "lvef_less_than": 50,
  "exclude": []
}
```


## v0.4.1 更新：Negation Detection

疾病分類現在先在每一次檢查紀錄中判斷關鍵字是否為陽性，再彙整到病人層級。

### 例子

- 只有 `no PDA` 的病人：不會列入 PDA。
- 曾經有 `PDA`，後來變成 `no PDA` 的病人：仍會列入 PDA。
- `PDA closed`、`s/p PDA ligation` 會視為曾經有 PDA。
- `no CoA`、`without CoA` 不會列入 CoA / IAA。


## v0.4.2 更新：DiseaseEngine 效能改善

v0.4.1 在大型資料庫中可能看起來像卡住，因為會重複過濾 examination-level DataFrame。

v0.4.2 改為：

- 先依病歷號碼預先分組檢查紀錄。
- 每個疾病只掃描預先分組後的資料。
- 執行時顯示疾病分類進度。

仍保留 v0.4.1 的 row-level negation detection。


## v0.4.3 更新

### 1. 日期解析修正

修正 Excel serial number 被解析成 `1970-01-01` 的問題。

現在支援：

- Excel serial number，例如 `45000`
- `YYYYMMDD`，例如 `20200131`
- 一般日期字串，例如 `2020/01/31`
- 原本就是 datetime 的儲存格

### 2. CoA / IAA 排除規則加強

以下描述不會列入 CoA / IAA：

- `No COA`
- `no CoA`
- `no coarctation`
- `no coarctation of aorta`
- `without CoA`
- `without coarctation`
