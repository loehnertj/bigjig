'''Find the dominant colors of an image.'''

import sys
import attr
import itertools as it
from contextlib import contextmanager
import numpy as np
try:
    from scipy.ndimage.measurements import center_of_mass
except ImportError:
    print('scipy unavailable: color extraction will be less accurate.')
    center_of_mass = None
from PyQt4.QtGui import QImage

__all__ = [
    'find_colors',
]

@attr.s
class Cluster:
    rgb = attr.ib([0, 0, 0])
    radius = attr.ib(0.0)
    
def qimage2array(image):
    assert image.format() == QImage.Format_ARGB32
    w = image.width()
    h = image.height()
    # flatten image already
    ptr = image.constBits()
    ptr.setsize(image.byteCount())
    a = np.array(ptr).reshape(w*h, 4)
    return a

# debug methods
@contextmanager
def mplaxes():
    import matplotlib.pyplot as plt
    ax = plt.gca()
    yield ax
    plt.show()
    
def showcolors(*clists):
    with mplaxes() as ax:
        ax.imshow(np.array([[cluster.rgb for cluster in clist] for clist in clists]))
        
def histograms(colors):
    with mplaxes() as ax:
        ax.plot(colors.sum(axis=2).sum(axis=1), scale, 'r-')
        ax.plot(colors.sum(axis=2).sum(axis=0), scale, 'g-')
        ax.plot(colors.sum(axis=1).sum(axis=0), scale, 'b-')
        
# required methods
scale = np.linspace(0., 1.0, 64, endpoint=False)
#RR, GG, BB = np.meshgrid(scale, scale, scale)
RR = scale[:,None,None]
GG = scale[None,:,None]
BB = scale[None,None,:]
def distsq(cluster):
    cr, cg, cb = cluster.rgb
    result= (RR-cr)**2 + (GG-cg)**2 + (BB-cb)**2
    return result
        

def find_colors(image, cluster_radius=0.25, threshold=0.03):
    '''cluster_radius: size of cluster sphere
    threshold: min percentage of pixels required in a cluster
    '''
    imgarr = qimage2array(image)
    #with mplaxes() as ax:
    #    ax.imshow(imgarr.reshape(image.width(), image.height(), 4)[:, :, [2, 1, 3]])
        
    # bin all pixels into a 64x64x64 array of all possible RGB coordinates.
    colors = np.zeros((64, 64, 64), dtype=float)
    cidx = tuple([(imgarr[:, n]/4.).astype(int) for n in [2,1,0]])
    # add up weighted by alpha value
    np.add.at(colors, cidx, imgarr[:, 3])
    
    # normalize to % of image; 255.0 = max alpha value
    colors /= imgarr[:, 3].sum()
    
    # Set initial clusters list empty.
    clusters = []
    # REPEAT:
    while True:
        # Create copy of the bin matrix and exclude existing clusters. ("remainder matrix")
        remainder = colors.copy()
        for cluster in clusters:
            remainder[distsq(cluster) <= cluster.radius**2] = 0.0
            
        # Scan the remainder matrix with a fixed raster, and find the color with most (leftover) pixels nearby.
        sradius = int(64.*cluster_radius)//2
        pts = np.arange(sradius//2, 64, sradius)
        counts = np.array([
            [
                ir, ig, ib,
                remainder[
                    max(ir-sradius, 0):(ir+sradius),
                    max(ig-sradius, 0):(ig+sradius),
                    max(ib-sradius, 0):(ib+sradius)
                ].sum()
            ]
            for ir, ig, ib in it.product(pts, pts, pts)
        ])
        maxind = np.argmax(counts[:,3])
        rgb, percentage = counts[maxind, 0:3]/64., counts[maxind, 3]
        
        # If the pixels make up <x% of the image, exit here.
        if percentage < threshold:
            break
        
        # Otherwise create a new cluster around the scan point.
        new_cluster = Cluster(rgb, cluster_radius)
        clusters.append(new_cluster)
        
    # Relax cluster positions of all clusters.
    old_clusters = clusters
    if center_of_mass:
        clusters = relax_cluster_positions(colors, clusters)
    #showcolors(old_clusters, clusters)
    return clusters
        
        
def relax_cluster_positions(colors, clusters, move_threshold=0.01):
    clusters = [Cluster(rgb=c.rgb, radius=c.radius) for c in clusters]
    moved = np.inf
    while moved > move_threshold:
        mindists = np.full(colors.shape, np.inf)
        labels = np.zeros(colors.shape, dtype=int)
        for n, cluster in enumerate(clusters):
            dist = distsq(cluster)
            # find idx at which cluster is located
            # might not take into account clusters that come later
            idx = (mindists > dist) & (dist <= cluster.radius**2)
            labels[idx] = n
            mindists[idx] = dist[idx]
            
        centers = center_of_mass(colors, labels, range(len(clusters)))
        moved = 0.0
        for cluster, center in zip(clusters, centers):
            center = np.array(center) / 64.
            moved = max(moved, sum((center-cluster.rgb)**2)**0.5)
            cluster.rgb = center
    return clusters
    
def main(filename):
    image = QImage(filename)
    clusters = find_colors(image)
        
if __name__=='__main__':
    main(sys.argv[1])