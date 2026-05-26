# Changelog

本项目的显著变更记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/)。

## [1.0.0] - 2026-04-14

### Added
- 批量 OCR 识别结果按日期排序
- 爱发电 OAuth 集成 + 商业授权系统
- 多电表管理（赞助者功能）

### Changed
- 品牌由 Smart EBOCR 更名为"电费分析工具"（现名 smart-ebocr）
- 多电表管理从高级用户下调到支持者档位

## [0.3.0] - 2026-03-xx

### Added
- SSE 异步批量处理架构
- 目录扫描批量识别
- 采暖季特殊谷段费率支持

### Fixed
- OCR 三引擎回退逻辑优化
- 年度累计阶梯计算修正

## [0.2.0] - 2026-02-xx

### Added
- Vue 3 前端重写（原为纯后端模板）
- ECharts 用电可视化
- Pinia 状态管理
- TailwindCSS 样式系统

### Changed
- 后端重构为 Flask Blueprint 架构
- 数据库迁移至 SQLAlchemy ORM

## [0.1.0] - 2025-xx-xx

### Added
- 阶梯电价 vs 峰谷电价对比
- 年度累计计费
- 自定义电价参数

## [0.0.1] - 2024-xx-xx

### Added
- OCR 识别"网上国网"截图
- 单张上传与识别
- 基础用电数据记录
