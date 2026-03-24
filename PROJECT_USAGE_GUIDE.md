# Project-Based Data Management - 使用指南

## 快速开始

### 1. 启动服务器（自动迁移）
```bash
cd ~/mytest/llm-performance-viz
uv run start_viz_server.py
```

服务器会自动：
- 检测旧的数据结构
- 自动迁移到 `default` project
- 创建 `archive_results/default/` 目录
- 加载现有数据

访问: http://localhost:8000

### 2. 查看可用项目
打开Web UI后，在左侧边栏会看到 "Project Selection" 下拉菜单：
```
🚀 GCR GPU Perf

Project Selection
  [default ▼]     <- 选择项目
```

### 3. 切换项目
点击下拉菜单选择不同的项目：
- `default` - 默认项目
- `project-a` - 自定义项目
- 其他自定义项目...

项目会自动：
- 加载该项目的数据
- 清除之前的选择
- 重新渲染树结构

---

## 项目管理

### 目录结构
```
archive_results/
├── default/
│   ├── runtime1--instance1--model1/
│   │   ├── sysinfo.json
│   │   └── test_in:1600_out:400_proc:1_rand:100.json
│   └── ...
├── project-a/
│   └── ...
└── project-b/
    └── ...
```

### 创建新项目

#### 方法 1：手动创建目录
```bash
mkdir -p archive_results/my-project
# 然后复制测试数据到该目录
cp -r archive_results/default/* archive_results/my-project/
```

刷新 Web UI，新项目会自动出现。

#### 方法 2：指定项目运行测试
```bash
# 运行测试时指定项目（需要脚本支持）
./run_single_test.sh config.yaml --project my-project
```

### 删除项目
```bash
rm -rf archive_results/project-name
```

刷新 Web UI，项目会自动消失。

---

## 数据迁移

### 从旧版本迁移（如果有旧数据）

#### 自动迁移（推荐）
```bash
python3 migrate_to_project_structure.py
```

脚本会：
- ✓ 自动检测旧结构
- ✓ 创建备份
- ✓ 迁移到 `default` project
- ✓ 保留所有数据

#### 手动检查结构
```bash
python3 migrate_to_project_structure.py --show-structure
```

#### 不创建备份
```bash
python3 migrate_to_project_structure.py --no-backup
```

#### 指定自定义目录
```bash
python3 migrate_to_project_structure.py -d /custom/path/archive_results
```

---

## API 使用

### 获取所有项目列表
```bash
curl http://localhost:8000/api/projects
# 返回: {"projects": ["default", "project-a", "project-b"]}
```

### 获取特定项目的树结构
```bash
curl "http://localhost:8000/api/tree-structure?project=project-a"
```

### 获取项目中模型的组合
```bash
curl "http://localhost:8000/api/combinations?project=project-a"
```

### 获取对比数据
```bash
curl -X POST http://localhost:8000/api/comparison-data \
  -H "Content-Type: application/json" \
  -d '{
    "project": "project-a",
    "combinations": [
      {"runtime": "vllm-v0.9.2", "instance_type": "g6e.4xlarge", "model_name": "Qwen3-30B"}
    ]
  }'
```

### 导出数据
```bash
curl -X POST http://localhost:8000/api/export-csv \
  -H "Content-Type: application/json" \
  -d '{
    "project": "project-a",
    "combinations": [...]
  }' \
  -o data.csv
```

---

## 服务器配置

### 启动选项

```bash
# 使用自定义项目作为默认
uv run start_viz_server.py --project production

# 使用自定义结果目录
uv run start_viz_server.py --results-dir /data/llm-results

# 使用自定义端口
uv run start_viz_server.py --port 9000

# 组合多个选项
uv run start_viz_server.py \
  --results-dir /data/archive_results \
  --port 9000 \
  --project production
```

### 完整帮助
```bash
uv run start_viz_server.py --help
```

---

## 工作流示例

### 场景：比较两个不同配置集合的性能

1. **创建项目结构**
   ```bash
   mkdir -p archive_results/config-v1
   mkdir -p archive_results/config-v2
   ```

2. **复制对应数据**
   ```bash
   cp results_v1/* archive_results/config-v1/
   cp results_v2/* archive_results/config-v2/
   ```

3. **启动服务器**
   ```bash
   uv run start_viz_server.py
   ```

4. **在 Web UI 中**
   - 选择 `config-v1` 项目
   - 添加需要的模型到对比
   - 记录结果
   - 切换到 `config-v2` 项目
   - 添加相同的模型进行对比

---

## 浏览器持久化

### localStorage 自动保存
系统会自动在浏览器中记忆：
- 上次选择的项目
- Token 配置
- Chart 可见性设置

清除缓存将重置这些设置。

### 手动清除缓存
```javascript
// 在浏览器开发者工具 Console 中运行
localStorage.clear()
```

---

## 故障排除

### 项目在下拉菜单中不显示

**原因1：目录不存在**
```bash
# 检查目录是否存在
ls -la archive_results/
```

**原因2：目录权限问题**
```bash
# 检查权限
ls -ld archive_results/project-name
chmod 755 archive_results/project-name
```

**原因3：需要刷新**
- 点击树结构旁的刷新按钮 (↻)
- 或重新加载页面

### 切换项目后数据不变

**原因1：浏览器缓存**
```javascript
// 在开发者工具 Console 执行
localStorage.removeItem('lastProject')
location.reload()
```

**原因2：服务器未加载新项目**
- 查看服务器控制台输出
- 可能是文件权限问题

### 旧数据不见了

**检查迁移**
```bash
# 列出所有项目
ls -la archive_results/

# 检查default项目中的数据
find archive_results/default -type f | head
```

**恢复备份**
```bash
# 迁移脚本会创建备份
ls -la archive_results_backup_*

# 恢复备份
rm -rf archive_results
mv archive_results_backup_username archive_results
```

---

## 性能考虑

### 对于大型数据集
- 每个项目应该包含逻辑相关的测试
- 避免在一个项目中放置过多不相关的模型
- 可以创建多个小项目而不是一个大项目

### 项目大小建议
- 小：< 100 个测试组合 ✓ 最快
- 中：100-1000 个测试组合 ✓ 快
- 大：> 1000 个测试组合 ⚠️ 可能较慢

---

## 最佳实践

### 项目命名
```
✓ 好的名字：
  - default
  - production
  - staging
  - experiment-1
  - benchmark-v2
  - customer-a

✗ 避免：
  - 名字带空格
  - 特殊字符（/ \ : * ? " < > |）
  - 太长的名字（> 50字符）
```

### 项目组织
```
✓ 推荐方式：
  - default: 所有生产测试
  - staging: 测试新配置
  - experimental: 一次性实验
  - customer-a: 特定客户的数据

✗ 避免：
  - 将所有测试混在一个项目
  - 频繁创建和删除项目
  - 项目名称完全相同的副本
```

### 备份策略
```bash
# 定期备份重要项目
tar -czf archive_results_backup_$(date +%Y%m%d).tar.gz archive_results/

# 或使用 rsync
rsync -av archive_results/ /backup/archive_results_$(date +%Y%m%d)/
```

---

## 常见问题 (FAQ)

**Q: 能否在项目之间移动数据？**
A: 可以。手动复制/移动目录：
```bash
cp -r archive_results/project-a/model-x archive_results/project-b/
```

**Q: 项目数据是否会互相影响？**
A: 不会。每个项目的数据完全隔离，互不影响。

**Q: 能否同时加载多个项目的数据？**
A: 当前版本一次只能加载一个项目。可以在不同的浏览器标签页中打开不同项目。

**Q: 删除项目会删除原始数据吗？**
A: 是的，删除 `archive_results/project-name/` 目录会删除该项目的数据。删除前请备份重要数据。

**Q: 项目支持哪些特殊字符？**
A: 建议只使用字母、数字、下划线和连字符（a-z, 0-9, _, -）。

---

## 更新内存库
最后，别忘了更新你的个人笔记以记住这个新功能！
