from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser(description="检查本项目 DIP 分组核算所需基础文件是否齐备，并可校验入组结果。")
    parser.add_argument("--stat-month", help="可选，检查特定月份点值与结果文件准备情况，例如 2025-01")
    parser.add_argument("--result-path", help="可选，入组结果文件路径（支持Excel/CSV），用于校验特殊病例入组情况")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    data_root = project_root / "数据仓库"

    checks = [
        ("DIP目录库", data_root / "平顶山2025年DIP2.0分组目录库.xlsx"),
        ("ICD10映射", data_root / "ICD10国临版2.0对照医保版2.0.xlsx"),
        ("ICD9映射", data_root / "ICD9国临版3.0对照医保版2.0.xlsx"),
    ]

    ok = True
    print("=== DIP输入检查 ===")
    print(f"项目根目录: {project_root}")
    print(f"数据目录: {data_root}")
    print()

    for label, path in checks:
        exists = path.exists()
        ok = ok and exists
        status = "OK" if exists else "MISSING"
        print(f"[{status}] {label}: {path}")

    print()
    for label, path in checks:
        if not path.exists():
            continue
        try:
            xls = pd.ExcelFile(path)
            print(f"[SHEETS] {label}: {', '.join(xls.sheet_names)}")
        except Exception as exc:  # pragma: no cover - diagnostic path
            ok = False
            print(f"[ERROR] {label} 无法读取: {exc}")

    directory_file = data_root / "平顶山2025年DIP2.0分组目录库.xlsx"
    if directory_file.exists():
        try:
            directory_df = pd.read_excel(directory_file, sheet_name="目录", dtype=str).fillna("")
            score_col = "病种分值"
            group_col = "病种类型（1.核心病种；2.综合病种）"
            group_series = directory_df.get(group_col, pd.Series(dtype=str)).astype(str).str.strip()
            summary = {
                "目录记录数": len(directory_df),
                "核心病种数": int((group_series == "1").sum()) if group_col in directory_df.columns else "N/A",
                "综合病种数": int(group_series.isin(["0", "2"]).sum()) if group_col in directory_df.columns else "N/A",
                "含分值记录数": int(directory_df.get(score_col, pd.Series(dtype=str)).astype(str).str.strip().ne("").sum())
                if score_col in directory_df.columns
                else "N/A",
            }
            print()
            print("=== DIP目录摘要 ===")
            for key, value in summary.items():
                print(f"{key}: {value}")
            if group_col in directory_df.columns:
                unique_values = ", ".join(sorted(value for value in group_series.unique() if value != ""))
                print(f"病种类型原始值: {unique_values}")
        except Exception as exc:  # pragma: no cover - diagnostic path
            ok = False
            print(f"[ERROR] 目录sheet读取失败: {exc}")

        # 特殊病种校验
        print()
        print("=== 特殊病种校验 ===")
        special_disease_checks = [
            ("新生儿病种", "新生儿|出生|儿"),
            ("肿瘤病种", "肿瘤|癌|瘤|C[0-9]|D[0-4]"),
            ("重症病种", "重症|ICU|呼吸衰竭|心力衰竭"),
            ("联合手术病种", "联合|双侧|多部位"),
            ("日间手术病种", "日间|日间手术"),
            ("康复病种", "康复|物理治疗|功能训练"),
        ]
        name_col = "病种名称"
        if name_col in directory_df.columns:
            name_series = directory_df[name_col].astype(str).str
            for label, pattern in special_disease_checks:
                count = int(name_series.contains(pattern, case=False, regex=True).sum())
                status = "OK" if count > 0 else "WARNING"
                print(f"[{status}] {label}: {count} 种")
                if count == 0:
                    print(f"  提示：当前目录库中未找到{label}相关记录，可能影响特殊病例入组")
        else:
            print("[WARNING] 目录库中未找到病种名称列，无法校验特殊病种")

        # 辅助目录字段校验
        print()
        print("=== 辅助目录字段校验 ===")
        assist_fields = ["CCI校正系数", "年龄系数", "肿瘤校正系数", "床日费用标准"]
        for field in assist_fields:
            exists = field in directory_df.columns
            status = "OK" if exists else "MISSING"
            print(f"[{status}] {field}")
            if not exists:
                print(f"  提示：目录库中缺少{field}字段，特殊病例校正功能将无法使用")

    if args.stat_month:
        print()
        print("=== 月份提示 ===")
        print(f"目标月份: {args.stat_month}")
        print("此脚本仅检查本地文件准备情况。")
        print("若要确认该月份点值、病例与结果表是否齐全，请进一步检查数据库中的 dwd_case、sys_dip_point_value 和 ads/dws 结果表。")

    # 入组结果校验
    if args.result_path:
        print()
        print("=== 入组结果校验 ===")
        result_path = Path(args.result_path)
        if not result_path.exists():
            print(f"[ERROR] 入组结果文件不存在: {result_path}")
            ok = False
        else:
            try:
                # 读取结果文件
                if result_path.suffix.lower() in ['.xlsx', '.xls']:
                    result_df = pd.read_excel(result_path, dtype=str).fillna("")
                elif result_path.suffix.lower() == '.csv':
                    result_df = pd.read_csv(result_path, dtype=str, low_memory=False).fillna("")
                else:
                    print(f"[ERROR] 不支持的文件格式: {result_path.suffix}")
                    ok = False
                    result_df = None

                if result_df is not None:
                    print(f"[INFO] 读取到病例数: {len(result_df)}")
                    
                    # 检查必要字段
                    required_fields = ["年龄", "住院天数", "总费用", "入组结果", "病种分值", "是否特殊病例"]
                    exist_fields = [f for f in required_fields if f in result_df.columns]
                    missing_fields = [f for f in required_fields if f not in result_df.columns]
                    
                    if missing_fields:
                        print(f"[WARNING] 缺少字段: {', '.join(missing_fields)}，部分校验功能无法使用")
                    
                    # 特殊病例入组统计
                    if "是否特殊病例" in result_df.columns:
                        special_count = int((result_df["是否特殊病例"].astype(str).str.strip() == "是").sum())
                        special_rate = special_count / len(result_df) * 100
                        print(f"[INFO] 特殊病例数: {special_count} ({special_rate:.2f}%)")
                        
                        if "入组结果" in result_df.columns:
                            special_matched = int((
                                (result_df["是否特殊病例"].astype(str).str.strip() == "是") &
                                (result_df["入组结果"].astype(str).str.strip().isin(["已入组", "匹配成功"]))
                            ).sum())
                            special_match_rate = special_matched / special_count * 100 if special_count > 0 else 0
                            print(f"[INFO] 特殊病例入组率: {special_match_rate:.2f}%")
                            if special_match_rate < 90:
                                print(f"[WARNING] 特殊病例入组率偏低，请检查特殊入组规则是否正确应用")
                    
                    # 异常病例统计
                    if "总费用" in result_df.columns and "住院天数" in result_df.columns:
                        try:
                            result_df["总费用_num"] = pd.to_numeric(result_df["总费用"], errors='coerce')
                            result_df["住院天数_num"] = pd.to_numeric(result_df["住院天数"], errors='coerce')
                            
                            # 超高费用病例（这里简化判断，实际应结合病组均费）
                            high_cost_count = int((result_df["总费用_num"] > 100000).sum())
                            print(f"[INFO] 超高费用病例（>10万）: {high_cost_count}")
                            
                            # 超长住院病例
                            long_stay_count = int((result_df["住院天数_num"] > 30).sum())
                            print(f"[INFO] 超长住院病例（>30天）: {long_stay_count}")
                            
                        except Exception as e:
                            print(f"[WARNING] 费用/住院天数字段解析失败: {e}")

            except Exception as exc:
                ok = False
                print(f"[ERROR] 入组结果文件读取失败: {exc}")

    print()
    if ok:
        print("检查完成：本地 DIP 基础文件已具备，可继续做入组或核算。")
        return 0

    print("检查完成：存在缺失或读取错误，建议先修复基础文件。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
