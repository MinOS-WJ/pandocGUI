# pandocGUI

pandocGUI 是面向 Windows 10/11 x64 的 Pandoc 图形化封装。应用不包含
`pandoc.exe`，运行前需要单独安装 Pandoc 3.x。

## 使用

1. 单独安装 Pandoc 3.x。
2. 运行 `installer/output` 中的安装包。
3. 启动 pandocGUI；若未自动检测到 Pandoc，请在设置页选择 `pandoc.exe`。

## 功能

- 多输入文件合并转换与任务队列
- Pandoc 3.10 完整参数面板和附加参数入口
- 动态格式、扩展与高亮能力检测
- 转换预设、命令预览和完整日志
- Pandoc 查询工具
- PyInstaller 目录构建和 NSIS 用户级安装

安装包只包含 pandocGUI 自身，不包含 Pandoc 或 PDF/TeX 等外部转换引擎。
