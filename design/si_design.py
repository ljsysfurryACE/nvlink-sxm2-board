#!/usr/bin/env python3
"""
NVLink SXM2 板 — 信号完整性 (SI) 完整设计
覆盖: 层分配 / 阻抗 / 串扰 / 损耗 / 时序 / 过孔 / 眼图预算
"""
import numpy as np

# ===== 基础参数 =====
BPS = 25.78125e9        # NVLink 2.0 每 lane 速率 (NRZ)
TUI = 1/BPS             # 单位间隔 = 38.8 ps
DK, DF = 3.7, 0.004     # Megtron6
ZDIFF = 85              # 差分阻抗
LINKS, LANES = 6, 8     # 6 链路 × 8 lane/向
PAIRS = LINKS * LANES   # 每卡 48 对差分

print("="*76)
print("NVLink SXM2 板 — 信号完整性设计")
print("="*76)
print(f"\n基础: {BPS/1e9:.2f} Gbps/lane, TUI={TUI*1e12:.2f} ps, "
      f"差分 {ZDIFF}Ω, 材料 Megtron6 (Df={DF})")

# ===== 1. 信号层分配 =====
print("\n【1. 信号层分配】(双卡互联: 每卡 48 对, 双向 96 对)")
print("  可用信号层: L3 / L5 / L8 / L10 (4 层内层带状线)")
print("  每层承载: 24 对差分 (96/4)")
print("""
  ⚠️ 关键: 相邻信号层【正交布线】(水平 vs 垂直)
     层对: (L3 ↔ L5) 用 L4(GND) 隔离 → 交叉走线
           (L8 ↔ L10) 用 L9(GND) 隔离 → 交叉走线
  → 层间串扰降低 10-20dB

  SXM2 扇出 (MEG-Array 400-pin):
     · 连接器焊盘间距: 1.27mm 栅格
     · 需 via-in-pad 或 激光过孔从焊盘引出
     · 每对差分扇出: 2 个过孔 + 短走线到内层
""")

# ===== 2. 阻抗控制链 =====
print("【2. 阻抗控制 — 全链路一致 (85Ω 差分)】")
print("""
  链路(每段都必须 85Ω±10%, 目标 ±5%):
    ① 连接器          → MEG-Array 标称阻抗 (查 datasheet)
    ② 扇出区 (表层)   → 微带 85Ω 差分 + 参考 L2/L4
    ③ 换层过孔        → ⚠️ 最容易失配处! 过孔阻抗 ≈ 60-70Ω
    ④ 内层传输线      → 带状线 85Ω (W=4mil/S=7mil, 单侧8mil介质)
    ⑤ 对端同样结构

  ⚠️ 过孔处理:
     · 差分过孔: 两孔间距 = 2×线间距 (保持耦合)
     · 反焊盘 (anti-pad) 直径优化 → 补偿容性
     · 添加 GND 伴随过孔 (每对 2-4 个) → 提供回流
     · 背钻 stub < 10mil (25G 必须!)
""")

# ===== 3. 串扰预算 =====
print("【3. 串扰预算】")
print(f"""
  对内 (P↔N):    差分对本身, 靠紧耦合抵消 ✓
  对间 (相邻对):  间距 ≥ 3W = 21mil → NEXT < 3%
  层间 (L3↔L5):  正交 + GND 夹层 → < 2%
  邻链路:         NVLink 6 链路之间加 GND 屏蔽墙
  目标: 总串扰 < 5% (眼高损失 < 0.5dB)
""")

# ===== 4. 插入损耗 (关键!) =====
print("【4. 插入损耗 — 25G 下最关键】")
def loss_db(length_mm, df, freq_hz=12.9e9):
    """介质损耗 (近似): IL = 2.3 * f(GHz) * Df * sqrt(Dk) * L(m) ... 简化"""
    # 每 inch 介质损耗 (dB) ≈ 2.3 * f(GHz) * Df * sqrt(Dk) / 12 ? 用经验值
    # 经验: Megtron6 @12.9GHz ≈ 0.6 dB/inch (纯介质)
    base = 0.6 * df/0.004   # 归一到 M6
    return base * length_mm/25.4 * (freq_hz/12.9e9)

for mat, df in [('Megtron6', 0.004), ('Megtron4', 0.008), ('FR-4', 0.020)]:
    il = loss_db(80, df)     # 80mm 典型走线 (卡间互联)
    print(f"  {mat:10s} Df={df:.3f}: 80mm@12.9GHz ≈ {il:.1f} dB")

print("""
  NVLink 预算: 总插损 < 15 dB @Nyquist (含连接器)
     · 80mm Megtron6 ≈ 1.9 dB ✓ 直连可行
     · FR-4 会到 ~9.5 dB ⚠️ (这就是原厂板眼图差的原因)
  → Megtron6 下【直连可行】; 若加长或更高裕量, 加 Redriver
     Redriver: TI DS280BR810 (8ch, 消除 ISI, 可加 10-15dB 裕量)
""")

# ===== 5. 时序 =====
print("【5. 时序控制】")
print(f"""
  对内等长:  ±5 mil (±0.127mm) → skew < 1ps (0.025 TUI) ✓
  对间等长:  ±50 mil → 用于 lane-to-lane deskew
  链路间:    NVLink 有弹性缓冲, 放宽到 ±100 mil
  TUI = {TUI*1e12:.1f} ps → 总 skew 预算 < 20% TUI = {TUI*1e12*0.2:.1f} ps
""")

# ===== 6. 眼图预算 =====
print("【6. 眼图预算 (25.78 Gbps NRZ)】")
amp = 800.0  # mV 差分幅度 (SXM2 NVLink 典型)
print(f"  发送幅度: {amp:.0f} mVpp (差分)")
budget = [
    ('连接器', 0.5), ('扇出+过孔', 1.5), ('传输线 80mm M6', 1.9),
    ('对间串扰', 0.5), ('参考面不连续', 0.3), ('总裕量预留', 2.0)
]
tot = sum(b for _, b in budget)
print(f"  {'项目':<20} {'损耗(dB)':>10}")
for n, b in budget:
    print(f"  {n:<20} {b:>10.1f}")
print(f"  {'合计':<20} {tot:>10.1f}")
atten = 10**(-tot/20)
eye = amp * atten
print(f"\n  → 接收眼高 ≈ {eye:.0f} mV (发送 {amp:.0f} mV, 衰减 {tot:.1f}dB)")
print(f"  → 眼高比 = {eye/amp*100:.0f}%")
if eye/amp > 0.3:
    print("  ✅ 超过典型接收灵敏度门限 (通常要求 > 25-30%)")
else:
    print("  ⚠️ 需加 Redriver 或缩短走线")

print("\n【7. 其他 SI 铁律】")
print("""
  · 参考面完整: 差分对【绝不跨分割】; 换参考面时加缝合电容
  · 回流路径: GND 过孔紧邻信号过孔 (< 30mil)
  · 阻焊开窗: 差分对上方不开窗 (阻抗跳变)
  · 拐角: 45° 或圆弧 (禁 90°)
  · 禁 stub: 无 T 型分支
  · 测试点: 不加在差分对上 (加则用 < 0.5mm 焊盘)
""")
