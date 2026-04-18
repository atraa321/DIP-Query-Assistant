# DIP 查询助手

面向医师的离线 DIP 查询桌面助手，支持：

- 托盘常驻运行
- 悬浮式查询窗口
- 按 `DIP编码 / 病种名称 / 关键词` 查询
- 分别显示 `居民医保金额` 与 `职工医保金额`
- 从本地 `数据源/` 目录生成 SQLite 查询库

## 开发环境

- 建议目标运行环境：`Windows 7 x64`
- 建议打包环境：`Python 3.8 x64`

## 安装依赖

```powershell
python -m pip install -r requirements.txt
```

如果安装 `PySide2` 遇到本机代理问题，可先手工下载对应 wheel 后本地安装。

## 生成查询库

```powershell
$env:PYTHONPATH = "src"
python scripts/build_data.py
```

默认会读取：

- `数据源/平顶山2025年DIP2.0分组目录库.xlsx`

并输出：

- `data/dip_lookup.db`

## 运行程序

```powershell
$env:PYTHONPATH = "src"
python run_app.py
```

也可以直接双击：

```text
start.bat
```

## 打包 EXE

```powershell
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1
```

## 配置说明

- 运行时配置文件：`config/settings.json`
- 示例配置文件：`config/settings.example.json`
- 本地数据目录：`数据源/`

## 首版边界

- 当前是轻量查询版，不包含完整病例入组。
- 金额按后台设置中的居民/职工点值分别试算。
- 若未设置点值，界面会显示 `未设置点值`。
