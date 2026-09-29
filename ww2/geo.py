"""地图几何预处理 -> build/geo.pkl

坐标统一用 (X, Y) = (经度, 纬度)，经度 < -30 的部分 +360，
这样欧洲、亚洲、太平洋、夏威夷在同一张平面上是连续的。
"""
import json, os, pickle

import numpy as np
import shapefile
from shapely.affinity import translate
from shapely.geometry import box, shape, Polygon, MultiPolygon, LineString, MultiLineString, Point
from shapely.ops import unary_union

D = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(D, "data")
OUT = os.path.join(D, "build", "geo.pkl")

EAST = box(-30, -90, 180, 90)
WEST = box(-180, -90, -30, 90)


def wrap(g):
    a = g.intersection(EAST)
    b = translate(g.intersection(WEST), 360, 0)
    return unary_union([x for x in (a, b) if not x.is_empty])


def polys(g):
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g]
    if hasattr(g, "geoms"):
        out = []
        for x in g.geoms:
            out += polys(x)
        return out
    return []


def rings(g):
    """多边形 -> [外环+内环 的 float32 数组列表]，供 cv2.fillPoly 使用（偶奇填充）"""
    out = []
    for p in polys(g):
        if p.area < 1e-5:
            continue
        rs = [np.asarray(p.exterior.coords, np.float32)]
        rs += [np.asarray(r.coords, np.float32) for r in p.interiors]
        out.append(rs)
    return out


def lines(g):
    if g.is_empty:
        return []
    if isinstance(g, LineString):
        return [np.asarray(g.coords, np.float32)]
    if hasattr(g, "geoms"):
        out = []
        for x in g.geoms:
            out += lines(x)
        return out
    return []


def read_shp(path):
    r = shapefile.Reader(path)
    return [shape(s.__geo_interface__) for s in r.shapes()]


def read_geojson(path, key="NAME"):
    d = json.load(open(path))
    out = {}
    for f in d["features"]:
        n = f["properties"].get(key)
        g = shape(f["geometry"]).buffer(0)
        out[n] = unary_union([out[n], g]) if n in out else g
    return out


def bbox_of(rs_list):
    pts = np.concatenate([r[0] for r in rs_list]) if rs_list else np.zeros((1, 2))
    return (float(pts[:, 0].min()), float(pts[:, 1].min()), float(pts[:, 0].max()), float(pts[:, 1].max()))


def P(*pts):
    return Polygon([(x if x >= -30 else x + 360, y) for x, y in pts])


def main():
    land50 = wrap(unary_union([g.buffer(0) for g in read_shp(os.path.join(DATA, "ne_50m_land/ne_50m_land.shp"))]))
    land10_raw = read_shp(os.path.join(DATA, "ne_10m_land/ne_10m_land.shp"))
    land10 = wrap(unary_union([g.buffer(0) for g in land10_raw]))
    lakes = wrap(unary_union([g.buffer(0) for g in read_shp(os.path.join(DATA, "ne_50m_lakes/ne_50m_lakes.shp"))]))
    c38 = {k: wrap(v) for k, v in read_geojson(os.path.join(DATA, "world_1938.geojson")).items() if k}
    c45 = {k: wrap(v) for k, v in read_geojson(os.path.join(DATA, "world_1945.geojson")).items() if k}
    print("loaded")

    # 内陆国界：1938 年各国边界，去掉贴着海岸线的部分
    bnd = unary_union([g.boundary for k, g in c38.items() if k != "None"])
    inner = land50.buffer(-0.12)
    borders = bnd.intersection(inner).simplify(0.01)
    print("borders")

    C = lambda n: c38[n]
    G38 = C("Germany")
    austria = c45["Austria"].intersection(G38.buffer(0.05))
    rhine = P((5.5, 47.3), (7.9, 47.5), (8.5, 47.7), (8.8, 48.3), (9.0, 49.0), (8.9, 49.8), (8.7, 50.4),
              (8.5, 50.9), (8.2, 51.4), (7.8, 51.8), (7.3, 52.2), (5.5, 52.3)).intersection(G38)
    germany = G38.difference(austria).difference(rhine)
    cz = C("Czechoslovakia")
    czech_lands = cz.intersection(box(12, 47, 18.9, 52))
    sudeten = czech_lands.difference(czech_lands.buffer(-0.32))
    czech_rest = cz.difference(sudeten).difference(box(22.3, 47, 25, 50))  # 喀尔巴阡罗塞尼亚划给匈牙利
    pl = C("Poland")
    pl_west = pl.intersection(P((14, 56), (22.9, 56), (22.9, 54.3), (22.3, 53.6), (23.0, 53.0), (23.6, 52.2),
                                 (23.9, 51.5), (24.1, 50.8), (23.6, 50.4), (22.8, 49.8), (22.6, 49.0), (14, 48)))
    pl_east = pl.difference(pl_west)
    denmark = C("Denmark").intersection(box(7, 54, 16, 58))
    norway = C("Norway").intersection(box(4, 57, 32, 71.5))
    benelux = unary_union([C("Netherlands"), C("Belgium"), C("Luxembourg")])
    fr = C("France").intersection(box(-6, 41, 10, 52))
    fr_occ = fr.intersection(P((-6, 51.5), (9, 51.5), (9, 47.5), (6.1, 46.25), (5.5, 47.0), (4.85, 46.8),
                               (3.33, 46.56), (2.07, 47.22), (0.7, 47.2), (0.15, 45.65), (-0.5, 43.9),
                               (-1.25, 43.1), (-6, 43)))
    fr_vichy = fr.difference(fr_occ).intersection(box(-6, 41, 8, 52))
    italy = C("Italy").intersection(box(6, 36, 19, 48))
    albania = C("Albania")
    libya = C("Libya").intersection(box(9, 19, 26, 34))
    italy_s = italy.intersection(P((8, 41.9), (19, 41.9), (19, 36), (8, 36)))
    italy_n = italy.difference(italy_s)
    balkans = unary_union([C("Yugoslavia"), C("Greece").intersection(box(19, 34, 30, 42.5)),
                           C("Hungary"), C("Romania"), C("Bulgaria")])
    ussr_w = unary_union([C("USSR"), C("Estonia"), C("Latvia"), C("Lithuania"), pl_east]).intersection(box(20, 40, 60, 71))
    line41 = P((20, 62), (30.0, 62), (30.3, 60.2), (31.2, 59.9), (32.0, 59.2), (33.0, 57.8), (35.9, 56.9),
               (36.3, 56.0), (36.7, 55.2), (37.2, 54.1), (38.3, 52.8), (37.0, 51.7), (36.9, 50.2),
               (37.6, 49.0), (38.6, 47.3), (37.5, 45.0), (32.0, 44.0), (20, 44))
    ussr41 = ussr_w.intersection(line41)
    line42 = P((36.9, 51.7), (38.3, 52.8), (39.3, 51.8), (40.6, 50.2), (42.3, 49.6), (43.8, 49.2),
               (44.6, 48.6), (44.3, 46.3), (45.0, 44.2), (44.6, 43.4), (43.6, 43.3), (42.6, 43.2),
               (40.0, 43.6), (37.6, 44.5), (38.6, 47.3), (37.6, 49.0), (36.9, 50.2))
    ussr42 = ussr_w.intersection(line42).difference(ussr41)

    # ---------------- 远东
    japan = C("Empire of Japan")
    china = C("Chinese warlords")
    front38 = P((108, 44), (108, 41.2), (110, 40.6), (111.2, 38.2), (111.6, 36.5), (111.0, 35.0), (113.0, 34.6),
                (114.2, 32.4), (113.8, 31.4), (113.4, 30.4), (113.1, 29.3), (115.9, 28.6), (117.8, 29.2),
                (120.0, 29.6), (121.8, 29.4), (125, 29.4), (125, 44))
    china_n = china.intersection(front38).intersection(P((108, 44), (125, 44), (125, 34.8), (108, 34.8)))
    china_e = china.intersection(front38).intersection(box(117.6, 29.2, 125, 34.8))
    china_38 = china.intersection(front38).difference(china_n).difference(china_e)
    canton = china.intersection(Point(113.4, 23.0).buffer(1.1))
    hainan = china.intersection(box(108.4, 18.0, 111.2, 20.2))
    ichigo = china.intersection(unary_union([
        LineString([(114.0, 30.6), (113.0, 28.2), (112.6, 26.9), (111.6, 26.2), (110.3, 25.3),
                    (109.4, 24.3), (108.3, 22.8), (106.8, 22.0)]).buffer(0.85),
        LineString([(113.6, 34.7), (113.9, 32.0), (114.0, 30.6)]).buffer(0.7)])).difference(china_38).difference(china_n)
    indochina = unary_union([C("French Indo-China"), C("Cochin China"), C("Laos"), C("Cambodia")])
    siam = C("Siam")
    malaya = C("Malaysia")
    phil = C("Philippines")
    dei = C("Dutch East Indies")
    burma = c45["Burma"]
    png_n = c45["Papua New Guinea"].intersection(P((140, -5.5), (143.5, -3.5), (146.5, -7.5), (148, -8.5),
                                                    (153, -8.5), (153, -1), (140, -1)))
    hk = C("Hong Kong")

    # 太平洋防御圈（1942 年最大范围）画成海上的半透明红区
    perim = P((141, 45.5), (156, 51), (173, 53.2), (178, 51.2), (168, 30), (167, 19.4), (172.5, 7.5),
              (174.5, 0.5), (168, -5), (162, -11), (148, -11), (140, -9.5), (126, -11), (115, -9.6),
              (105, -8), (95, 2.5), (92.5, 12.5), (93.8, 20.5), (95, 26.5), (98, 28.5), (102, 24.0),
              (106, 22.5), (107.5, 21.6), (110, 20.0), (114, 21.5), (119, 24.5), (122, 30), (125, 34),
              (129.5, 34.5), (130.5, 42.5), (135, 45), (141, 45.5))
    perim_sea = perim.difference(land50.buffer(0.0))

    pieces = dict(
        germany=germany, rhineland=rhine, austria=austria, sudeten=sudeten, czech=czech_rest,
        poland_w=pl_west, denmark=denmark, norway=norway, benelux=benelux, france_occ=fr_occ,
        vichy=fr_vichy, italy_n=italy_n, italy_s=italy_s, albania=albania, libya=libya, balkans=balkans,
        ussr41=ussr41, ussr42=ussr42,
        japan=japan, china_n=china_n, china_e=china_e, china_38=china_38, canton=canton, hainan=hainan,
        ichigo=ichigo, indochina=indochina, siam=siam, malaya=malaya, phil=phil, dei=dei, burma=burma,
        png_n=png_n, hongkong=hk, perim=perim_sea,
    )
    allies = dict(
        uk=C("United Kingdom"), france=fr, poland=pl, china=unary_union([china, C("Xinjiang")]),
        ussr=unary_union([C("USSR"), C("Mongolia")]), usa=C("United States"),
    )
    out = dict(
        land50=rings(land50), land10=rings(land10), lakes=rings(lakes),
        borders=lines(borders),
        pieces={k: rings(v) for k, v in pieces.items()},
        allies={k: rings(v) for k, v in allies.items()},
        perim_line=np.asarray(perim.exterior.coords, np.float32),
    )
    for k, v in out["pieces"].items():
        print(f"{k:12s} parts={len(v):3d} bbox={tuple(round(x, 1) for x in bbox_of(v))}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pickle.dump(out, open(OUT, "wb"))
    print("land10 pts", sum(len(r) for rs in out["land10"] for r in rs), "land50 pts",
          sum(len(r) for rs in out["land50"] for r in rs), "border lines", len(out["borders"]))


if __name__ == "__main__":
    main()
