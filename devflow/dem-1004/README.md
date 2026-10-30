# DEM-1004 · 测试仓库：新增健康检查接口 /healthz

> 本目录由 **DevFlow** 流水线自动生成，用于验证「需求 → 设计 → 开发 → 测试 → 交付」链路。
> 内容是 **Mock 适配器产出的占位实现**，不是可上线的业务代码。

## 设计意图（真实实现应对应的位置）

| 目标文件 | 变更 | 原因 |
|---|---|---|
| `services/core/handler.py` | modify | 承载需求主流程 |
| `services/core/models.py` | modify | 补齐数据结构与校验 |
| `api/routes.py` | modify | 新增/调整对外接口 |
| `web/src/pages/Feature.tsx` | add | 前端入口与交互 |

## 为何放在 `devflow/` 之下

流水线只被授权写这个目录。若直接改上面列出的真实路径，会因为 diff 上下文是
虚构的而无法应用，也容易覆盖仓库已有代码。

## 接入真实适配器后

把 `MockAdapter` 换成能产出真实补丁的子进程适配器（Claude Code / Codex / CodeBuddy），
`writes` 就会变成真实改动，届时可放开 `devflow/` 的写入限制。

## 计划覆盖的测试

- `tests/test_dem_1004_1.py` · test_ac_001 · AC-001
- `tests/test_dem_1004_2.py` · test_ac_002 · AC-002
- `tests/test_dem_1004_3.py` · test_ac_003 · AC-003
- `tests/test_dem_1004_4.py` · test_ac_004 · AC-004
- `tests/test_dem_1004_5.py` · test_ac_005 · AC-005
