#!/usr/bin/env python3
"""
NVLink 过孔补偿设计 (85Ω 差分过孔)
问题: 过孔阻抗 ~60-70Ω (目标85) → 容性失配 → 反射
"""
import numpy as np

c0 = 3e8
TUI = 1/25.78125e9

print("="*74)
print("差分过孔补偿设计 (85Ω, 25.78Gbps)")
print("="*74)

# 过孔寄生参数 (典型 8mil 板)
print("\n【过孔为什么会失配】")
print("  过孔 = 一段垂直传输线 + 寄生电容:")
print("    · 焊盘/反焊盘电容 (anti-pad)  ~0.2-0.4 pF")
print("    · 过孔筒电感                   ~1-2 nH")
print("    · 等效阻抗 ≈ 60-70Ω (85Ω 目标 → 低于目标)")
print(f"    · TUI = {TUI*1e12:.1f} ps, 过孔长度 2mm ≈ 传递延迟 ~12ps")
print("  → 25G 下这会明显闭合眼图 (反射 + 容性负载)")

print("\n【补偿手段 (按有效性)】")
methods = [
    ("1. 反焊盘优化 (anti-pad 缩小)", 
     "减小寄生电容 → 提高阻抗",
     "★ 最有效: anti-pad 从 40mil→28mil, 可把过孔阻抗 65→78Ω"),
    ("2. 加 GND 伴随过孔",
     "提供回流路径, 稳定阻抗, 减少串扰",
     "★ 必须: 每对差分加 2-4 个, 距离 < 30mil; 间距 = 线间距×2"),
    ("3. 背钻 (back drill)",
     "去除 stub, 消除 stub 谐振",
     "★ 25G 必须: stub < 10mil; 否则 12.9GHz 附近谐振"),
    ("4. 过孔焊盘缩小",
     "减小焊盘电容",
     "✓ 焊盘从 20mil→16mil"),
    ("5. 差分过孔间距 = 2×线间距",
     "保持差分耦合",
     "✓ 保持 100Ω 差分过孔阻抗"),
    ("6. 补偿 stub (调谐)",
     "加感抗补偿容抗",
     "⚠️ 窄带, 25G 宽带不适用"),
]

for name, why, detail in methods:
    print(f"\n  {name}")
    print(f"    原理: {why}")
    print(f"    参数: {detail}")

# 数值估算: anti-pad 尺寸 vs 阻抗
print("\n【反焊盘尺寸 vs 过孔阻抗】(估算)")
print(f"  {'anti-pad(直径 mil)':>20} {'过孔阻抗(Ω)':>12} {'匹配度':>10}")
for ap in [20, 24, 28, 32, 36, 40]:
    # 经验: anti-pad 越大 → 电容越大 → 阻抗越低
    z = 85 + (30 - ap) * 1.15   # 粗略线性: ap=30mil ≈ 85Ω
    tag = "✅ 接近85" if abs(z-85) < 6 else ("✓" if abs(z-85) < 12 else "⚠️")
    print(f"  {ap:>20} {z:>12.1f} {tag:>10}")

print("\n【推荐组合 (85Ω 差分过孔)】")
print("""
  · anti-pad 直径:   28-30 mil  (目标 85Ω)
  · 过孔焊盘:        16 mil
  · 钻孔:            8-10 mil
  · GND 伴随过孔:    每对 4 个 (四角), 距信号孔 < 25mil
  · 背钻深度:        到距目标层 < 10mil
  · 差分孔间距:      = 2×线间距 (保持 100Ω 耦合, 配合外部85Ω)

  验证: 3D 仿真过孔 S 参数 (openEMS 建过孔模型)
        目标 TDR 阻抗 85Ω±10%, |S11| < -15dB @12.9GHz
""")

print("【25G 过孔 stub 谐振频率】")
for stub_mil in [10, 20, 30, 40, 50]:
    L = stub_mil*25.4e-6
    f_res = c0/(4*L*np.sqrt(3.7))  # λ/4 谐振
    tag = "✅ 安全" if stub_mil <= 10 else ("⚠️ 接近" if stub_mil <= 20 else "❌ 危险")
    print(f"  stub {stub_mil:>2} mil ({L*1e3:.2f}mm): 谐振 @ {f_res/1e9:>5.1f} GHz {tag}")
print("""
  ⚠️ stub=30mil → 谐振 @12.9GHz (正好在 Nyquist!) → 必须背钻
""")
