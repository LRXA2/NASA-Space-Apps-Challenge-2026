# Panorama of the sky seen from the lunar south pole, 2026-11-14 12:00 TT.
# IAU 2009 Moon orientation (leading terms only): pole RA/Dec and prime meridian angle W.
import json, math, sys
from datetime import datetime
d = (datetime(2026,11,14,12) - datetime(2000,1,1,12)).total_seconds()/86400
a0, d0 = math.radians(269.9949), math.radians(66.5392)
W = math.radians((38.3213 + 13.17635815*d) % 360)
def rz(t): c,s=math.cos(t),math.sin(t); return [[c,s,0],[-s,c,0],[0,0,1]]
def rx(t): c,s=math.cos(t),math.sin(t); return [[1,0,0],[0,c,s],[0,-s,c]]
def mm(A,B): return [[sum(A[i][k]*B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
R = mm(rz(W), mm(rx(math.pi/2-d0), rz(math.pi/2+a0)))
def body(ra, dec):
    ra, dec = math.radians(ra), math.radians(dec)
    s = [math.cos(dec)*math.cos(ra), math.cos(dec)*math.sin(ra), math.sin(dec)]
    b = [sum(R[i][j]*s[j] for j in range(3)) for i in range(3)]
    alt = math.degrees(math.asin(-b[2])); az = math.degrees(math.atan2(b[1], b[0]))
    return az, alt
stars = json.load(open('dl/stars.6.json'))['features']
out = []
for f in stars:
    m = f['properties']['mag']
    if m > 5.6: continue
    ra, dec = f['geometry']['coordinates']; ra %= 360
    az, alt = body(ra, dec)
    if alt < 0: continue
    out.append([round(az,2), round(alt,2), m, f['id'], f['properties'].get('bv')])
named = {'Canopus':(95.99,-52.70),'Achernar':(24.43,-57.24),'LMC':(80.89,-69.76),'SMC':(13.19,-72.83),'Miaplacidus':(138.30,-69.72),'Avior':(125.63,-59.51),'Acrux':(186.65,-63.10),'Alpha Centauri':(219.90,-60.83),'Hadar':(210.96,-60.37),'Fomalhaut':(344.41,-29.62),'Sirius':(101.29,-16.72),'Peacock':(306.41,-56.73)}
nm = {k: [round(x,2) for x in body(*v)] for k,v in named.items()}
json.dump({'date':'2026-11-14T12:00TT','stars':out,'named':nm}, open('sky.json','w'))
print(len(out), 'stars above horizon'); print(nm)
alts=[s[1] for s in out]; print('alt range', min(alts), max(alts))
