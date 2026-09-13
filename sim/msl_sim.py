#!/usr/bin/env python3
"""
NVLink PCB 仿真 v4 — 正确的 MSL 端口 (照抄 openEMS ports.py 的 MSLPort)
先做单端微带线 2 端口验证，再扩展差分。

MSLPort 要点:
  1. MSL 平面金属 (excite 方向拉平)
  2. 电压探针 ×3 (A/B/C 沿传播方向)
  3. 电流探针 ×2 (A/B 中点, norm_dir=传播方向)
  4. 激励在 feed_shift 位置, excite 方向
"""
import os, sys
import numpy as np

sys.path.append('.venv/lib/python3.12/site-packages')
from CSXCAD import ContinuousStructure

UNIT = 1e-6
# 微带线参数 (Megtron6): 单端 50Ω
W = 332.0     # 线宽 um (50Ω @H=200um, Megtron6)
H = 200.0     # 介质厚 um (8mil)
T = 35.0      # 铜厚 um (1oz)
L = 3000.0    # 线长 3mm (换网格密度)
DK = 3.7
SIM = '/tmp/nvlink_msl'

def ny_of(d):
    return {'x': 0, 'y': 1, 'z': 2}[d]

def add_msl_port(csx, nr, metal, start, stop, prop_dir, exc_dir, excite=0.0,
                 Feed_R=np.inf, feed_shift=0.0, meas_shift=None, priority=10):
    """照抄 openEMS ports.py MSLPort.__init__"""
    start = np.array(start, np.double); stop = np.array(stop, np.double)
    pny = ny_of(prop_dir); eny = ny_of(exc_dir)
    direction = float(np.sign(stop[pny] - start[pny]))
    upside_down = float(np.sign(stop[eny] - start[eny]))

    # 1) MSL 平面金属 (exc 方向拉平)
    m_start = np.array(start); m_stop = np.array(stop)
    m_stop[eny] = m_start[eny]
    metal.AddBox(list(m_start), list(m_stop))

    # 网格线 (传播方向)
    mesh = csx.GetGrid()
    prop_lines = np.array(mesh.GetLines(pny))
    if len(prop_lines) < 5:
        raise Exception('At least 5 lines in propagation direction required!')

    # 测量面位置
    measplane_shift = 0.5*abs(start[pny]-stop[pny]) if meas_shift is None else meas_shift
    measplane_pos = start[pny] + measplane_shift*direction
    idx = int(np.argmin(np.abs(prop_lines - measplane_pos)))
    idx = max(1, min(idx, len(prop_lines)-2))
    prope_idx = np.array([idx-1, idx, idx+1], int)
    if direction < 0:
        prope_idx = np.flipud(prope_idx)
    u_pos = prop_lines[prope_idx]

    # 2) 电压探针 ×3
    suffix = ['A', 'B', 'C']
    for n in range(3):
        us = 0.5*(start+stop); ue = 0.5*(start+stop)
        us[pny] = u_pos[n]; ue[pny] = u_pos[n]
        us[eny] = start[eny]; ue[eny] = stop[eny]
        csx.AddProbe(f'port_ut_{nr}{suffix[n]}', p_type=0).AddBox(list(us), list(ue))

    # 3) 电流探针 ×2 — 矩形环: 从地(z=0)到线(z=H), 横跨线宽
    i_pos = u_pos[0:2] + np.diff(u_pos)/2.0
    for n in range(len(i_pos)):
        a = np.array(start, np.double)
        b = np.array(stop,  np.double)
        a[pny] = i_pos[n]; b[pny] = i_pos[n]
        a[eny] = 0.0            # 地面
        b[eny] = abs(start[eny])  # 信号线高度
        csx.AddProbe(f'port_it_{nr}{suffix[n]}', p_type=1,
                     weight=direction, norm_dir=pny).AddBox(list(a), list(b))

    # 4) 激励
    if excite != 0:
        eidx = int(np.argmin(np.abs(prop_lines - (start[pny] + feed_shift*direction))))
        es = np.array(start); ee = np.array(stop)
        es[pny] = prop_lines[eidx]; ee[pny] = prop_lines[eidx]
        ev = np.zeros(3); ev[eny] = -1.0*upside_down*excite
        csx.AddExcitation(f'port_excite_{nr}', exc_type=0, exc_val=list(ev)).AddBox(list(es), list(ee))

    # 5) 馈电电阻
    if not np.isinf(Feed_R):
        rs = np.array(start); re = np.array(stop)
        re[pny] = rs[pny]
        if Feed_R == 0:
            metal.AddBox(list(rs), list(re))
        else:
            csx.AddLumpedElement(f'port_resist_{nr}', ny=eny, caps=True, R=Feed_R).AddBox(list(rs), list(re))

def build():
    csx = ContinuousStructure()
    mesh = csx.GetGrid(); mesh.SetDeltaUnit(UNIT)
    # 基板 Megtron6
    csx.AddMaterial('Megtron6', epsilon=DK).AddBox(start=[-1000, 0, 0], stop=[L+1000, 8000, H])
    # 地平面
    gnd = csx.AddMetal('GND')
    gnd.AddBox(start=[-2000, 0, -T], stop=[L+2000, 4000, 0])
    # 信号线 (微带)
    line = csx.AddMetal('LINE')
    line.AddBox(start=[0, 0, H], stop=[L, W/2, H+T])
    # 网格
    mesh.AddLine('x', np.linspace(-1000, L+1000, 11))
    mesh.AddLine('x', np.linspace(0, L, 301))
    mesh.AddLine('y', np.linspace(0, W/2+300, 13))
    mesh.AddLine('y', [W/2+300, 4000])
    mesh.AddLine('z', np.linspace(-T-200, H+T+200, 17))
    mesh.AddLine('z', [-T, 0, H, H+T])
    # MSL 端口 (官方几何: 端口面斜跨, z 从线高到地)
    # 官方: portstart=[-L, -W/2, H], portstop=[0, +W/2, 0]
    feed = L/3.0
    add_msl_port(csx, 1, line, start=[0, 0, H], stop=[feed, W/2, 0],
                 prop_dir='x', exc_dir='z', excite=-1.0, feed_shift=feed/3.0, meas_shift=feed/3.0)
    add_msl_port(csx, 2, line, start=[L, 0, H], stop=[L-feed, W/2, 0],
                 prop_dir='x', exc_dir='z', meas_shift=feed/3.0)
    return csx

def fdtd_block():
    return ('  <FDTD NumberOfTimesteps="40000" EndCriteria="1e-5" OverSampling="1"\n'
            '        TimeStepFactor="0.9">\n'
            '    <Excitation Type="0" f0="12.9e9" fc="12.9e9"/>\n'
            '    <BoundaryCond xmin="PML_8" xmax="PML_8" ymin="PMC"\n'
            '                  ymax="PML_8" zmin="PML_8" zmax="PML_8"/>\n'
            '  </FDTD>\n')

if __name__ == '__main__':
    os.makedirs(SIM, exist_ok=True)
    csx = build()
    raw = os.path.join(SIM, 'csx_raw.xml')
    csx.Write2XML(raw)
    body = open(raw).read()
    body = body.split('?>', 1)[-1].strip() if body.lstrip().startswith('<?xml') else body.strip()
    xml = os.path.join(SIM, 'model.xml')
    open(xml, 'w').write('<?xml version="1.0" encoding="utf-8"?>\n<openEMS>\n' + body + '\n' + fdtd_block() + '</openEMS>\n')
    print(f"模型: {xml} ({os.path.getsize(xml)/1024:.0f} KB)")
    print(f"端口: MSL (voltage x3 + current x2)")
    print(f"微带: W={W}um H={H}um L={L/1000:.1f}mm")
