#!/usr/bin/env python3
"""PCB 材料成本优化分析"""
import numpy as np

# 材料价格 (参考, ¥/m², 18x24in拼板估算)
MAT = {
    'Megtron6':      {'price': 1400, 'Df': 0.004, 'Tg': 185, '用途': 'NVLink 差分 / 25G 高速'},
    'Megtron4':      {'price':  900, 'Df': 0.008, 'Tg': 175, '用途': '中速信号'},
    'FR-4 (高Tg)':   {'price':  260, 'Df': 0.020, 'Tg': 170, '用途': '普通信号 / 电源'},
    'FR-4 (普通Tg)': {'price':  150, 'Df': 0.022, 'Tg': 140, '用途': '电源 / 地 (DC, 无信号)'},
    'CEM-3':         {'price':  100, 'Df': 0.025, 'Tg': 130, '用途': '电源层 (最便宜)'},
}

# 12 层叠层的层类型
LAYERS = [
    ('L1',  'signal'), ('L2','gnd'), ('L3','diff'), ('L4','gnd'),
    ('L5',  'diff'),   ('L6','pwr'), ('L7','pwr'),  ('L8','diff'),
    ('L9',  'gnd'),  ('L10','diff'),('L11','gnd'),  ('L12','signal'),
]

print("="*74)
print("NVLink 板 PCB 材料成本优化")
print("="*74)
print("\n【材料价格参考】(¥/m², 单面板料, 不含压合/工艺)")
for k, v in MAT.items():
    print("  %-14s ¥%5d  Df=%.3f  Tg=%d°C  %s" % (k, v['price'], v['Df'], v['Tg'], v['用途']))

print("\n【方案对比】(12层)")

def calc(scheme, name):
    """scheme: dict layer_type -> material"""
    total = 0; detail = []
    for ln, typ in LAYERS:
        m = scheme.get(typ)
        if m:
            total += MAT[m]['price']
            detail.append((ln, typ, m))
    print("\n  ▶ %s: 材料成本 ≈ ¥%d/m²" % (name, total))
    for ln, typ, m in detail:
        print("     %-4s %-7s %s" % (ln, typ, m))
    return total

# 方案A: 当前设计 (信号+差分=M6, 电源=FR4高Tg)
A = calc({'signal':'Megtron6','diff':'Megtron6','gnd':'FR-4 (高Tg)','pwr':'FR-4 (高Tg)'},
         "当前设计 (全信号层 M6 + 电源 FR4高Tg)")

# 方案B: 电源层降级为普通 FR-4
B = calc({'signal':'Megtron6','diff':'Megtron6','gnd':'FR-4 (高Tg)','pwr':'FR-4 (普通Tg)'},
         "电源层 → 普通 FR-4 (Tg140)")

# 方案C: 电源层用 CEM-3
C = calc({'signal':'Megtron6','diff':'Megtron6','gnd':'FR-4 (高Tg)','pwr':'CEM-3'},
         "电源层 → CEM-3 (最便宜)")

# 方案D: 只差分用 M6, 表层信号用 M4
D = calc({'signal':'Megtron4','diff':'Megtron6','gnd':'FR-4 (高Tg)','pwr':'CEM-3'},
         "差分 M6 + 表层 M4 + 电源 CEM-3")

print("\n【节省对比】")
print("  A → B: 省 ¥%d/m² (%.0f%%)" % (A-B, (A-B)/A*100))
print("  A → C: 省 ¥%d/m² (%.0f%%)" % (A-C, (A-C)/A*100))
print("  A → D: 省 ¥%d/m² (%.0f%%)" % (A-D, (A-D)/A*100))

print("\n【注意事项】")
print("  1. DC 电源层不看 Df (只看 Tg/耐压/CTE), CEM-3 完全够 ✓")
print("  2. ⚠️ 混压工艺有额外成本: 不同材料压合需对位/CTE匹配")
print("     · 小批量时工艺成本可能 > 材料节省")
print("     · 大批量(>100片)才划算")
print("  3. ⚠️ CEM-3 机械强度低于 FR-4, 厚板/大板慎用")
print("  4. 关键: 高速信号层【绝不能】降级 (25G 需要 Df<0.005)")
