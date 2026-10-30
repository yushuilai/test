"""S7 改名验证：订单导出新增 CSV 编码选项

需求编号：DEM-1006
对应改动目标：services/export/handler.py（承载需求主流程）

本文件由 DevFlow 流水线使用 Mock 适配器生成，仅用于打通交付链路，
是**占位实现**，不包含真实业务逻辑。提交到仓库的路径刻意放在 devflow/dem-1006/，
以免覆盖仓库已有代码。
"""

DEVFLOW_PLACEHOLDER = True
DEMAND_CODE = "DEM-1006"
TARGET_PATH = "services/export/handler.py"


def handle_dem_1006_0_handler(payload: dict) -> dict:
    """S7 改名验证：订单导出新增 CSV 编码选项 —— 占位入口。

    真实实现应落在 services/export/handler.py，并按设计文档补齐校验、幂等与审计。
    """
    raise NotImplementedError(
        "DevFlow 占位实现：DEM-1006 的真实逻辑需由可用适配器产出"
    )
