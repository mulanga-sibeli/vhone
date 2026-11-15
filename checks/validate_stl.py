"""Check exported binary STL topology, units and volume against CAD measurements."""
from collections import defaultdict, Counter
from pathlib import Path
import struct
import json

ROOT = Path(__file__).resolve().parent.parent
manifest = json.loads((ROOT / "docs/model_manifest.json").read_text())
reports = []
for path in sorted((ROOT / "STL").glob("*.stl")):
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    assert len(data) == 84 + 50*count, path
    edges = defaultdict(list)
    points = []
    volume = 0.0
    for i in range(count):
        values = struct.unpack_from("<12fH", data, 84+50*i)
        a,b,c = [tuple(values[j:j+3]) for j in (3,6,9)]
        points.extend((a,b,c))
        assert len({a,b,c}) == 3, (path, i, "degenerate triangle")
        volume += (a[0]*(b[1]*c[2]-b[2]*c[1]) + a[1]*(b[2]*c[0]-b[0]*c[2]) + a[2]*(b[0]*c[1]-b[1]*c[0]))/6
        for u,v in ((a,b),(b,c),(c,a)):
            edges[tuple(sorted((u,v)))].append((u,v))
    assert all(len(v) == 2 and v[0] == v[1][::-1] for v in edges.values()), (path,"non-manifold/inconsistent edges")
    bounds = [max(p[k] for p in points)-min(p[k] for p in points) for k in range(3)]
    expected = manifest[path.stem]
    assert volume > 0 and abs(volume/expected["volume_mm3"]-1) < 0.005, (path,volume)
    assert all(abs(a-b) < 0.1 for a,b in zip(bounds,expected["bounds_mm"])), (path,bounds)
    assert abs(min(p[2] for p in points)) < 1e-5, (path,"not on print bed")
    reports.append(f"PASS {path.name}: {count} triangles, closed consistently wound edges, positive volume {volume:.2f} mm3, CAD bounds match, print bed Z=0")
(ROOT / "docs/stl_validation.txt").write_text("\n".join(reports)+"\n")
print("\n".join(reports))
