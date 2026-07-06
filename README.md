# Echo Registry Analyzer (ERA)

Version 0.3.0

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

- `output/merged_all.xlsx`
- `output/patient_summary.xlsx`
- `output/birthday_conflict.xlsx`
- `output/gender_conflict.xlsx`
- `output/data_quality.xlsx`

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
