import random
import unittest
from shapely.geometry import Polygon
from test_topology import project,line
from topology import export_rows

class ProjectionNodingTests(unittest.TestCase):
    def fixture(self):
        generator=random.Random(127)
        x=500000+generator.random();y=1000000+generator.random()
        a=(x,y);b=(x+10.31,y+7.13);c=(x+6.14,y+16.32);d=(x-4.17,y+9.19);t=.373
        start=(a[0]+t*(b[0]-a[0])+1e-5,a[1]+t*(b[1]-a[1]))
        end=(d[0]+t*(c[0]-d[0])-1e-5,d[1]+t*(c[1]-d[1]))
        return [line([a,b,c,d,a]),line([start,end])],Polygon([a,b,c,d])

    def test_projection_on_slanted_edge_materializes_shared_vertices(self):
        elements,outline=self.fixture()
        p=project(elements,snap=True,label_levels={})
        self.assertEqual(len(p['parcels']),2)
        self.assertFalse(any(i['code']=='DANGLE' for i in p['issues']+p['ignored_issues']))
        self.assertEqual(len(export_rows(p,allow_unnumbered=True)),2)
        self.assertAlmostEqual(sum(r['DienTich'] for r in p['parcels']),outline.area,places=6)
        from collections import Counter
        degrees=Counter(tuple(point) for row in p['noded_lines'] for point in (row['points'][0],row['points'][-1]))
        for issue in p['issues']:
            if issue['code']=='SNAPPED_ENDPOINT':self.assertGreaterEqual(degrees[tuple(issue['target'])],3)

    def test_disabled_snap_does_not_silently_accept_open_divider(self):
        from shapely.geometry import Point
        elements,outline=self.fixture()
        centre=outline.centroid
        inset=[]
        for value in elements[-1]['points']:
            edge=outline.boundary.interpolate(outline.boundary.project(Point(value)))
            inset.append((edge.x+(centre.x-edge.x)*1e-6,edge.y+(centre.y-edge.y)*1e-6))
        elements[-1]=line(inset)
        p=project(elements,snap=False,label_levels={})
        with self.assertRaises(ValueError):export_rows(p,allow_unnumbered=True)
