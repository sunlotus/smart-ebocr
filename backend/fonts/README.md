# Fonts

本目录包含 PDF 报告生成所需的中文字体文件。

## Noto Sans SC (思源黑体)

- **License**: SIL Open Font License 1.1 (https://scripts.sil.org/OFL)
- **Copyright**: Copyright 2014-2021 Adobe, with Reserved Font Name 'Source'
- **Source**: https://github.com/google/fonts/tree/main/ofl/notosanssc
- **Files**:
  - `NotoSansSC-VF.ttf` — 可变字体（Regular + Bold，TrueType 轮廓）

SIL OFL 允许自由使用、修改和再分发，包括在商业产品中嵌入。

## 技术说明

ReportLab 的 TTFont 仅支持 TrueType 轮廓 (.ttf)，不支持 CFF/OpenType (.otf) 字体。
本目录使用可变 TTF 格式以确保与 ReportLab 兼容。

如系统无内嵌字体，代码会回退到：
1. Windows: 微软雅黑 (C:/Windows/Fonts/msyh.ttc)
2. Linux: Noto Sans CJK (/usr/share/fonts/.../NotoSansCJK-*.ttc)
3. ReportLab 内置 CID 字体: STSong-Light (华文宋体)
