# 贡献指南

感谢你对电费分析工具的关注！欢迎参与贡献。

## 如何贡献

### 报告问题

1. 在 [GitHub Issues](https://github.com/sunlotus/smart-ebocr/issues) 搜索是否已有相同问题
2. 如果没有，点击 "New Issue" 并选择 "Bug Report" 模板
3. 填写问题描述、复现步骤、预期行为和实际行为

### 提交代码

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feat/your-feature`
3. 提交修改：使用规范的 commit message
4. 推送分支：`git push origin feat/your-feature`
5. 创建 Pull Request

### Commit 规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <description>

feat(ocr): 支持识别新版电费截图格式
fix(billing): 修复采暖季谷段费率计算错误
docs(readme): 更新安装说明
```

类型说明：
- `feat` — 新功能
- `fix` — Bug 修复
- `docs` — 文档变更
- `style` — 代码格式（不影响功能）
- `refactor` — 重构（既非新功能也非 Bug 修复）
- `test` — 测试相关
- `chore` — 构建/工具变更

### 代码风格

**后端 (Python)**:
- 遵循 PEP 8
- 使用 `black` 格式化，行宽 88
- 使用 `isort` 管理导入顺序
- 函数添加 type hints 和 docstring

**前端 (Vue/JavaScript)**:
- 使用 Vue 3 Composition API
- 遵循已有的代码风格

### 开发环境

```bash
# 后端
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask run

# 前端
cd frontend
npm install
npm run dev
```

### 测试

```bash
# 后端测试
pytest tests/

# 前端 E2E 测试
cd frontend
npx playwright test
```

## 许可证

通过提交代码，你同意你的贡献将在 Apache 2.0 许可证下发布。
