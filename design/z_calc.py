#!/usr/bin/env python3
"""
NVLink 差分对阻抗设计计算器
目标: SXM2 NVLink 2.0 的 85Ω 差分阻抗
材料: Megtron 6 (Dk 3.7 @1GHz, Df 0.004)
输出: 可用几何参数（线宽/间距）+ 叠层建议

模型: 边缘耦合差分带状线（内层走线，NVLink 板推荐）
"""
import numpy as np

Dk = 3.7          # Megtron 6 Dk
Dk_eff = Dk       # 带状线全部在介质中

# ============ 阻抗模型 ============

def z_se_stripline(W, H, T, er):
    """单端带状线特性阻抗 (IPC-2141 / Hammerstad 近似)
    W: 线宽, H: 到两参考面距离(总介质厚), T: 铜厚  单位统一
    """
    # 有效线宽修正（铜厚）
    if T > 0:
        dW = T / np.pi * (1 + np.log(4 * np.e / ((T / H) ** 2 + (1 / np.pi / (W / T + 1.1)) ** 2)) ** 0.5)
    else:
        dW = 0
    Weff = W + dW
    return (60 / np.sqrt(er)) * np.log(4 * H / (0.67 * np.pi * Weff * (0.8 + T / H)))

def z_diff_edge_coupled_stripline(Zse, S, H):
    """边缘耦合差分带状线的差分阻抗（近似）"""
    return 2 * Zse * (1 - 0.48 * np.exp(-0.96 * S / H))

def z_diff_exact_stripline(W, S, H, T, er):
    """用单端 + 耦合修正"""
    zse = z_se_stripline(W, H, T, er)
    return z_diff_edge_coupled_stripline(zse, S, H), zse

# ============ 典型 NVLink 板叠层参数 ============
# 带状线到两参考面的总介质厚 H_tot (= 2 x 半层)
# 常见: 芯板 4mil + 半固化片 2x4mil => 信号层到参考面约 5-8mil

H_OPTIONS = [4.0, 5.0, 6.0, 7.0, 8.0]   # mil  （单侧到参考面厚度）
W_OPTIONS = [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]  # mil 线宽
S_OPTIONS = [4.0, 5.0, 6.0, 7.0, 8.0, 10.0]      # mil 对内间距
T = 0.7   # mil  铜厚 (0.5oz = 0.7mil, 1oz = 1.4mil)

def mil2um(x): return x * 25.4
def um2mil(x): return x / 25.4

if __name__ == '__main__':
    print("=" * 72)
    print("NVLink 差分阻抗设计 (目标 85Ω, Megtron6 Dk=%.1f)" % Dk)
    print("=" * 72)
    print("\n【扫描: 找 85Ω 的组合】(带状线, 单侧介质厚 H, 总介质=2H)\n")
    print(f"{'H(mil)':>7} {'W(mil)':>7} {'S(mil)':>7} {'Zse(Ω)':>8} {'Zdiff(Ω)':>9} {'误差':>7}")
    print("-" * 72)

    best = []
    for H in H_OPTIONS:
        for W in W_OPTIONS:
            for S in S_OPTIONS:
                # 带状线：信号在中间，到上下参考面各 H
                zse = z_se_stripline(mil2um(W), mil2um(2*H), mil2um(T), Dk)  # 总厚 2H
                zdiff = z_diff_edge_coupled_stripline(zse, mil2um(S), mil2um(2*H))
                err = zdiff - 85.0
                if abs(err) < 3.0:
                    best.append((abs(err), H, W, S, zse, zdiff, err))

    best.sort()
    for _, H, W, S, zse, zdiff, err in best[:18]:
        print(f"{H:>7.1f} {W:>7.1f} {S:>7.1f} {zse:>8.1f} {zdiff:>9.1f} {err:>+7.1f}")

    print(f"\n共 {len(best)} 组满足 |Zdiff-85| < 3Ω\n")

    # 推荐方案: 优先最常见工艺 (W=4mil 线/4mil 间距, 或 5/5)
    print("【工艺友好推荐】")
    for H in H_OPTIONS:
        for (W, S) in [(4.0, 4.0), (4.0, 6.0), (5.0, 5.0), (5.0, 7.0), (4.5, 5.0)]:
            zse = z_se_stripline(mil2um(W), mil2um(2*H), mil2um(T), Dk)
            zdiff = z_diff_edge_coupled_stripline(zse, mil2um(S), mil2um(2*H))
            if abs(zdiff - 85) < 4:
                print(f"  单侧介质 {H:.0f}mil | 线宽 {W}mil | 间距 {S}mil "
                      f"→ Zdiff = {zdiff:.1f}Ω  (Zse={zse:.1f}Ω)")
