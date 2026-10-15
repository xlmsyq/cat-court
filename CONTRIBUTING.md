# 贡献指南 Contributing

欢迎 issue 和 PR，尤其是这几类：

- **新的「条款体」罪名**：判决书里的可爱条款是这个项目的灵魂，欢迎补充
- **新的责任可视化**：目前是猫爪天平，如果你有更好的隐喻（不带「投票 / 谁占理」暗示），非常欢迎
- **多语言**：目前只有中文 prompt 和界面
- **无障碍**：色彩对比、屏幕阅读器标签

## 开发约定

1. 前端是 **`static/index.html` 单文件**，不引入构建工具、不引入 npm 依赖，通过 FastAPI 后端启动。
2. API Key 只从服务端环境变量读取，不能写入前端、示例文件或提交记录。
3. Prompt 里的几条铁律不能删（不说教 / 不贴标签 / 不做心理诊断 / 病中一方给低能耗方案 /
   给责任占比小的一方留台阶）。这些是产品边界，不是风格偏好。
4. 提 PR 前请附一张实机截图（尤其是改了 UI 的）。

## 本地跑

```bash
# 前后端版
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-xxx
uvicorn app:app --reload --port 8000
```

## 测试

```bash
pip install -r requirements.txt pytest
python -m pytest -q
```
