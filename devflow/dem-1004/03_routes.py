"""测试仓库：新增健康检查接口 /healthz

需求编号：DEM-1004
对应改动目标：api/routes.py（新增/调整对外接口）

本文件由 DevFlow 流水线使用 Mock 适配器生成，仅用于打通交付链路，
是**占位实现**，不包含真实业务逻辑。提交到仓库的路径刻意放在 devflow/dem-1004/，
以免覆盖仓库已有代码。
"""

DEVFLOW_PLACEHOLDER = True
DEMAND_CODE = "DEM-1004"
TARGET_PATH = "api/routes.py"


def handle_dem_1004_2_routes(payload: dict) -> dict:
    """测试仓库：新增健康检查接口 /healthz —— 占位入口。

    真实实现应落在 api/routes.py，并按设计文档补齐校验、幂等与审计。
    """
    raise NotImplementedError(
        "DevFlow 占位实现：DEM-1004 的真实逻辑需由可用适配器产出"
    )
