# Echo Registry Analyzer (ERA)

Version 0.4.0

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
