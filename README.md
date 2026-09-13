# NVLink SXM2 双卡互联板 — 设计与仿真

自研 NVLink 双卡互联板（SXM2 ↔ SXM2）的设计参数与电磁仿真流程。

## 背景

SXM2 的 NVLink 2.0 每 lane 25.78125 Gbps NRZ，6 链路 × 8 lane，
85Ω 差分阻抗。原厂 baseboard 用 FR-4 + 无源直通，25G 下损耗过大。

本项目目标：用低损耗材料（Megtron 6）+ 正确叠层 + Redriver，
并通过 3D 电磁仿真（openEMS）验证，争取一次成型。

## 内容

```
design/
  z_calc.py    差分阻抗计算器 (带状线模型, 扫描 85Ω 几何)
  stackup.py   12 层叠层方案 (Megtron6 + FR4 混压)
sim/
  api_sim7.py  openEMS 3D FDTD 仿真 (MSL 端口, S参数)
  msl_sim.py   早期版本 (纯 CSXCAD, 无 openEMS Python 包时)
docs/
```

## 关键设计参数

### 50Ω 微带 (Megtron6, Dk=3.7, H=200um)
```
W = 332 um (W/H = 1.66)
```

### 85Ω 差分 (边缘耦合带状线)
```
单侧介质 8mil (总 16mil):
  W=3.5mil / S=5.0mil → 85.1Ω
  W=4.0mil / S=7.0mil → 85.7Ω  ← 工艺友好
  4.5mil / S=8.0mil   → 83.6Ω
```

### 12 层叠层
```
L1  信号(表层)   Megtron6
L2  GND
L3  ★差分对      Megtron6 (8mil 介质各侧)
L4  GND
L5  ★差分对      Megtron6
L6  PWR/GND      FR-4
L7  PWR/GND      FR-4
L8  ★差分对      Megtron6
L9  GND
L10 ★差分对      Megtron6
L11 GND
L12 信号(表层)   Megtron6
```

板级规范: 96 对差分 / 对内等长 ±5mil / 对间 ≥3W /
背钻 stub <10mil / 连接器 Amphenol MEG-Array 400-pin (84740-102LF)

## openEMS 仿真要点

```bash
# 依赖: openEMS + CSXCAD Python 绑定
export LD_LIBRARY_PATH=$OPENEMS_ROOT/lib
```

关键设置（对照官方 MSL_NotchFilter.py）:
1. `resolution = C0/(f_max*sqrt(eps_r))/unit/50`  (λ/50)
2. `mesh.SmoothMeshLines()` 分方向多次调用（必须，否则不收敛）
3. 端口用 `FDTD.AddMSLPort(...)`（不是 LumpedPort）
4. 后处理 `p.CalcPort(sim, f, ref_impedance=50)`

## 材料成本分析

`design/cost_opt.py` 对比了几种材料方案（12 层）：

| 方案 | 材料成本 | 说明 |
|------|---------|------|
| 当前设计 | ¥9960/m² | 信号层 M6 + 电源 FR-4 |
| 电源→普通FR-4 | ¥9740/m² | 省 2% |
| 电源→CEM-3 | ¥9640/m² | 省 3%（但混压更复杂） |
| +表层信号→M4 | ¥8640/m² | 省 13% |

关键结论：**成本大头在信号层（M6），不在地源层**。
真正省钱的顺序：减 M6 层数 > M4 替代 > 电源层降级。

## 信号完整性设计

`design/si_design.py` — 完整 SI 分析：
- 信号层分配（96 对差分 → 4 层，相邻层正交布线）
- 阻抗控制链（连接器→扇出→过孔→带状线）
- 串扰预算 / 插入损耗 / 时序 / 眼图预算

**关键数据**（80mm 走线 @12.9GHz）：
| 材料 | Df | 插损 |
|------|-----|------|
| Megtron6 | 0.004 | 1.9 dB |
| Megtron4 | 0.008 | 3.8 dB |
| FR-4 | 0.020 | 9.4 dB |

→ 这解释了原厂 FR-4 板眼图差的原因

眼图预算：发送 800mVpp - 6.7dB 衰减 → 接收眼高 370mV（46%）✓

## 过孔设计

`design/via_comp.py` + `docs/via_design.md`

85Ω 差分过孔参数：
- **anti-pad 28-30mil**（决定阻抗，20mil→96Ω, 30mil→85Ω, 40mil→74Ω）
- 钻孔 8-10mil / 焊盘 14-16mil
- GND 伴随过孔每对 4 个
- 背钻 stub < 10mil

## 当前状态

```
✅ openEMS 工具链打通 (含 Python 绑定)
✅ 50Ω / 85Ω 几何算出
✅ 12 层叠层方案
✅ S21 插损结果可信 (5mm 微带 -17dB @1GHz)
⚠️ S11 还剩一个固定系数问题 (恒定 +2~3dB, 疑似激励源贡献未扣)
```

## License

GPL-3.0

本项目的仿真脚本参考/移植了 openEMS 官方示例（CRLH_Extraction.py、
MSL_NotchFilter.py）的代码逻辑，并链接 openEMS 库（GPL），
因此以 GPL-3.0 发布。
