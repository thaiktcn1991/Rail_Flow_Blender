# Rail Flow Blender - Retopology Tool
# Ported from Rail Flow Maya by ThaiLuong
# License: GPL-3.0

################################################################################
# 🛡️ AI PRE-DEBUG CHECKPOINT: BLENDER UI & LOGIC INTEGRITY
# ------------------------------------------------------------------------------
# TRƯỚC KHI SỬA BẤT KỲ LỖI NÀO, BẠN BẮT BUỘC PHẢI ĐỌC CÁC FILE CẨM NANG SAU:
# 1. [SMART_DEV_HANDBOOK.md](file:///d:/Google_AntiGravity/scratch/Rail_Flow_Blender/docs/AI_ONBOARDING_STANDARDS/SMART_DEV_HANDBOOK.md)
# 2. [COLLABORATION_PROTOCOL.md](file:///d:/Google_AntiGravity/scratch/Rail_Flow_Blender/docs/AI_ONBOARDING_STANDARDS/COLLABORATION_PROTOCOL.md)
# 3. [DAILY_DEVELOPMENT_LOG.md](file:///d:/Google_AntiGravity/scratch/Rail_Flow_Blender/docs/notes/DAILY_DEVELOPMENT_LOG.md)
# ------------------------------------------------------------------------------
# 🇻🇳 NGÔN NGỮ: TIẾNG VIỆT LÀ BẮT BUỘC.
# 🏗️ KIẾN TRÚC: TUÂN THỦ MODULAR (UI tách biệt hoàn toàn CORE).
# ################################################################################

bl_info = {
    "name": "Rail Flow",
    "author": "ThaiLuong (thaiktcn1991)",
    "version": (1, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Rail Flow",
    "description": "Advanced retopology tool (Blender Edition V1.1)",
    "doc_url": "https://github.com/thaiktcn1991/Rail_Flow_Blender",
    "category": "Mesh",
}

import bpy

from . import rf_properties
from . import rf_operators
from . import rf_ui


classes = []


def register():
    rf_properties.register()
    rf_operators.register()
    rf_ui.register()
    print("Rail Flow: Registered")


def unregister():
    rf_ui.unregister()
    rf_operators.unregister()
    rf_properties.unregister()
    print("Rail Flow: Unregistered")


if __name__ == "__main__":
    register()
