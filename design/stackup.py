#!/usr/bin/env python3
"""
NVLink SXM2 双卡互联板 — 叠层设计方案
SXM2: 400-pin Amphenol MEG-Array, 12V
NVLink 2.0: 25.78125 Gbps/lane NRZ, 6 链路 x 8 lane/向, 85Ω 差分
材料: Megtron 6 (信号层) + FR-4 (普通层, 混压降本)
"""
import numpy as np

MIL = 25.4  # um per mil

# ============ 设计目标 ============
TARGET_ZDIFF = 85.0     # Ω 差分
TARGET_ZSE = 50.0       # Ω 单端(目标, 差分对由两条 50Ω 构成)

# ============ 12 层叠层方案 (总厚 ~2.0mm) ============
# 信号层放在内层(带状线) → 屏蔽好, 阻抗稳定
# 每层: (名称, 类型, 厚度mil, 材料, 说明)
STACKUP_12 = [
    ("L1",  "signal",  1.4, "Megtron6-core",   "表层信号(微带) / 或全 GND"),
    ("---",  "prepreg", 4.0, "Megtron6-prepreg", ""),
    ("L2",  "plane",   1.4, "copper",          "GND 平面 (完整参考面)"),
    ("---",  "core",    6.0, "Megtron6-core",   ""),
    ("L3",  "signal",  0.7, "Megtron6",        "★ NVLink 差分对 (带状线, 85Ω)"),
    ("---",  "prepreg", 2*8.0, "Megtron6-prepreg", " 到 L2/L4 各 8mil (85Ω 所需)"),
    ("L4",  "plane",   1.4, "copper",          "GND 平面"),
    ("---",  "core",    4.0, "FR-4-core",       ""),
    ("L5",  "signal",  0.7, "Megtron6",        "★ NVLink 差分对 (带状线, 85Ω)"),
    ("---",  "prepreg", 4.0, "FR-4-prepreg",    ""),
    ("L6",  "plane",   1.4, "copper",          "PWR/GND 平面"),
    ("---",  "core",    8.0, "FR-4-core",       "中心"),
    ("L7",  "plane",   1.4, "copper",          "PWR/GND 平面"),
    ("---",  "prepreg", 4.0, "FR-4-prepreg",    ""),
    ("L8",  "signal",  0.7, "Megtron6",        "★ NVLink 差分对"),
    ("---",  "core",    4.0, "FR-4-core",       ""),
    ("L9",  "plane",   1.4, "copper",          "GND 平面"),
    ("---",  "prepreg", 2*8.0, "Megtron6-prepreg", ""),
    ("L10", "signal",  0.7, "Megtron6",        "★ NVLink 差分对"),
    ("---",  "core",    6.0, "Megtron6-core",   ""),
    ("L11", "plane",   1.4, "copper",          "GND 平面"),
    ("---",  "prepreg", 4.0, "Megtron6-prepreg", ""),
    ("L12", "signal",  1.4, "Megtron6",        "表层信号(微带) / 或全 GND"),
]

# ============ NVLink 差分对 (带状线) 设计 ============
# L3: 到 L2(GND) 4mil, 到 L4(GND) 4mil → 总介质 8mil
L3_STRIKE = {"to_gnd_top": 8.0, "to_gnd_bot": 8.0, "total_dielectric": 16.0}

def z_se_stripline(W_mil, H_mil, T_mil, er):
    """单端带状线阻抗 (IPC-2141)"""
    if T_mil > 0:
        dW = T_mil/np.pi*(1+np.log(4*np.e/((T_mil/H_mil)**2+(1/np.pi/(W_mil/T_mil+1.1))**2))**0.5)
    else:
        dW = 0
    Weff = W_mil + dW
    return (60/np.sqrt(er))*np.log(4*H_mil/(0.67*np.pi*Weff*(0.8+T_mil/H_mil)))

def z_diff(zse, S_mil, H_mil):
    return 2*zse*(1-0.48*np.exp(-0.96*S_mil/H_mil))

if __name__ == '__main__':
    print("="*76)
    print("NVLink SXM2 双卡互联板 — 叠层设计方案 (12层)")
    print("="*76)

    # 计算总厚度
    total = sum(t for _, _, t, _, _ in STACKUP_12)
    print(f"\n【叠层表】(总厚 {total*MIL/1000:.2f} mm = {total:.1f} mil)\n")
    print(f"{'层':>5} {'类型':>8} {'厚度(mil)':>10} {'材料':>20} 说明")
    print("-"*76)
    for name, typ, th, mat, note in STACKUP_12:
        if name == "---":
            print(f"{'':>5} {'':>8} {th:>10.1f} {mat:>20} {note}")
        else:
            sym = "★" if typ == "signal" else " "
            print(f"{name:>5}{sym}{typ:>7} {th:>10.1f} {mat:>20} {note}")

    # 差分对参数 (基于 L3: 8mil 总介质)
    print(f"\n【NVLink 差分对设计】(L3/L5/L8/L10 带状线)")
    print(f"  层内介质: 到上参考面 {L3_STRIKE['to_gnd_top']}mil, 到下参考面 {L3_STRIKE['to_gnd_bot']}mil")
    print(f"  总介质厚: {L3_STRIKE['total_dielectric']}mil")
    print()
    print(f"  {'W(mil)':>7} {'S(mil)':>7} {'Zse(Ω)':>8} {'Zdiff(Ω)':>9} {'评价':>16}")
    print("  " + "-"*52)
    for W in [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]:
        for S in [4.0, 5.0, 6.0, 7.0, 8.0]:
            zse = z_se_stripline(W, 16.0, 0.7, 3.7)
            zd = z_diff(zse, S, 16.0)
            err = abs(zd - 85)
            if err < 3:
                tag = "✓✓ 推荐" if err < 1.5 else "✓ 可用"
                print(f"  {W:>7.1f} {S:>7.1f} {zse:>8.1f} {zd:>9.1f} {tag:>16}")

    print(f"\n【板级设计要点】")
    print("  1. NVLink 对数量: 6 链路 x 8 对 x 2 卡(交叉互连) = 96 对差分")
    print("  2. 对内等长: ±5 mil;  对间间距: >= 3W (>=12mil)")
    print("  3. 换层过孔: 背钻 stub < 10 mil (25G 必做)")
    print("  4. 参考面: 完整, 禁跨分割; 缝补过孔(stitching via) 每 100mil 一颗")
    print("  5. 连接器: Amphenol MEG-Array 400-pin (84740-102LF) — 勿买山寨")
    print("  6. 电源: 12V 主, 每卡峰值 ~300W → 铜厚 1oz+, 多过孔并联")
    print(f"\n【材料清单】")
    print("  · 信号层介质: Megtron 6 (Df 0.004 @10GHz) — 96 对差分全部在上面")
    print("  · 电源/普通层: FR-4 (混压降本)")
    print("  · 表面处理: ENIG (沉金) — 适合 25G + 多次回流")
