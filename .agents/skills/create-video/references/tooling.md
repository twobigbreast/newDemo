# 工具使用与复用边界

## 已交付文件

| 文件 | 负责的重复步骤 |
|---|---|
| scripts/video.py | 初始化、缓存、配音、内部审片、渲染调度、媒体验收、说明生成 |
| scripts/render_runtime.py | 共用字体检查、13 张关键帧/海报、Skia→FFmpeg 编码、进程峰值与耗时 |
| scripts/site_workflow.py | 页面/目录/注册表、媒体迁移标记、构建打包、发布下一步与响应记录 |
| scripts/sync_source.py | 通过 stdin 接凭据，只同步登记文件，记录已推送 commit |
| scripts/browser_check.cjs | 实际播放器的延迟加载、桌面/手机、Range 与六次 seek |
| templates/dark-matter, templates/cmb | 已使用过的完整科学绘图、模型、时间轴和旁白模板 |
| templates/shared | 现有页面样式与通用影片构建器 |

## 典型命令

以下 scripts/ 路径相对于本 skill 根目录。

```sh
python scripts/video.py init --project /workspace/work/new-film --template dark-matter --slug new-film
# 编辑 video.json 的分镜、参考、素材信息，以及科学模型/绘图函数。
python scripts/video.py run --project /workspace/work/new-film --through keyframes
# 助手实际查看 work/keyframes.jpg；这不是用户审批。
python scripts/video.py review --project /workspace/work/new-film --note '实际审片记录'
python scripts/video.py run --project /workspace/work/new-film --through docs
# 再运行同一命令应逐步打印 CACHE，不重做视频。
```

配音已确定时可单独运行 `audio`，无需等页面完成。`run --through keyframes` 会自动复用音轨。`verify --file /path/existing.mp4` 可单独验证既有成片，禁止为了上传而重做它的配音或动画。

## 默认上传交付

已有成片托管到已有网站时，先使用 [直接上传与验收](direct-upload.md)。不需要 video.json、Git 写凭据、构建或部署；网站响应记录和两阶段发布仅用于已确认需要源码改动的分支。`site` 命令要求 `--allow-source-changes --reason`，用于阻止误走整站发布。

## 网站响应记录

`next` 是工具调用计划，不是替代原生 MCP 的 HTTP 发布器。助手调用它输出的工具后，把完整响应 JSON 经 stdin 输入：

```sh
python scripts/video.py receipt --project <project> --phase stage_saved
python scripts/video.py receipt --project <project> --phase site_access
python scripts/video.py receipt --project <project> --phase stage_deployed
python scripts/video.py receipt --project <project> --phase storage_ready
```

final_saved/final_deployed 同理。凭据仅送入 `sync`，不能送进状态文件。普通 get_site 响应中的凭据、bearer 等字段不会被 receipt 保存，只保存访问方式判据。

`sync` 若官方 source helper 可用，应由该 helper 处理源码；自带工具是 helper 缺失时的备用路径。`package` 要求有对应的已推送 commit 记录，并检查构建没有修改已同步的跟踪文件。archive 内容只包含 hosting.json 与构建 Worker，不是源码树。

## 已知边界

- 两套画面模板是具体科学主题，不能自动保证陌生主题的物理正确性；仍需适配模型和审片。
- 自动检验黑屏/重复帧不能替代视觉和科学检查。
- 通用 Sites 安装器针对本仓库现有 Worker 约定；不假装支持所有框架或存储平台。
- 直接调用原生工具仍由助手执行；脚本自动化的是构建、状态、参数、恢复与去重。
- 不同环境的速度不同；阶段记录必须实测，不能将历史 FPS 当作承诺。
