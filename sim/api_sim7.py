#!/usr/bin/env python3
"""完全对齐官方 MSL_NotchFilter.py 的做法"""
import os, sys, numpy as np
from CSXCAD import ContinuousStructure
from openEMS import openEMS
from openEMS.physical_constants import C0

unit = 1e-6
W, H, T, L = 332.0, 200.0, 35.0, 5000.0
DK = 3.7
f_max = 30e9
Sim = '/tmp/nvlink_v7'

def build():
    CSX = ContinuousStructure()
    FDTD = openEMS(EndCriteria=1e-5)
    FDTD.SetCSX(CSX)
    mesh = CSX.GetGrid()
    mesh.SetDeltaUnit(unit)

    FDTD.SetGaussExcite(f_max/2, f_max/2)
    FDTD.SetBoundaryCond(['PML_8','PML_8','MUR','MUR','PML_8','PML_8'])

    sub = CSX.AddMaterial('Megtron6', epsilon=DK)
    sub.AddBox([-3000, -3000, 0], [L+3000, 3000, H])
    pec = CSX.AddMetal('PEC')
    pec.AddBox([-3000, -3000, -T], [L+3000, 3000, 0])

    # ★ 官方 resolution = lambda/50
    resolution = C0/(f_max*np.sqrt(DK))/unit/50
    print("  resolution = %.1f um (lambda/50)" % resolution)

    # 官方风格: 粗框架
    feed = L/3.0
    mesh.SetLines('x', [-feed-L/2, 0, feed+L/2])
    mesh.SetLines('y', [-3000, 0, 3000])
    mesh.SetLines('z', [0, 3000])
    mesh.AddLine('x', np.linspace(0, L, 31))
    mesh.AddLine('z', [-T, 0, H, H+T])
    # ★ 官方: 分方向多次 SmoothMeshLines
    mesh.SmoothMeshLines('x', resolution/4)
    mesh.SmoothMeshLines('x', resolution)
    mesh.SmoothMeshLines('y', resolution/4)
    mesh.SmoothMeshLines('y', resolution)
    mesh.SmoothMeshLines('z', resolution)

    xl = mesh.GetLines('x')
    port = [None, None]
    port[0] = FDTD.AddMSLPort(1, pec, [xl[0], -W/2, H], [-feed, W/2, 0], 'x', 'z',
                              excite=-1, FeedShift=10*resolution, MeasPlaneShift=feed/3, priority=10)
    port[1] = FDTD.AddMSLPort(2, pec, [xl[-1], -W/2, H], [feed, W/2, 0], 'x', 'z',
                              FeedShift=10*resolution, MeasPlaneShift=feed/3, priority=10)
    return FDTD, CSX, port

if __name__ == '__main__':
    os.makedirs(Sim, exist_ok=True)
    FDTD, CSX, port = build()
    print("跑仿真...", flush=True)
    FDTD.Run(Sim, cleanup=False, verbose=2)
    print("仿真完成", flush=True)
    f = np.linspace(1e6, f_max, 801)
    # ★ 官方: 只传 ref_impedance
    for p in port:
        p.CalcPort(Sim, f, ref_impedance=50)
    s11 = port[0].uf_ref/port[0].uf_inc
    s21 = port[1].uf_ref/port[0].uf_inc
    print("\nf(GHz)   S11(dB)   S21(dB)")
    for ft in [1e9,5e9,10e9,12.9e9,20e9,25e9]:
        k = np.argmin(np.abs(f-ft))
        print("%6.1f  %8.2f  %8.2f" % (f[k]/1e9, 20*np.log10(abs(s11[k])+1e-12), 20*np.log10(abs(s21[k])+1e-12)))
    ok = (np.abs(s11).max()<=1.01) and (np.abs(s21).max()<=1.01)
    print("\n|S11|max=%.3f  |S21|max=%.3f → %s" % (np.abs(s11).max(), np.abs(s21).max(), "✅ 物理合理!" if ok else "❌"))
