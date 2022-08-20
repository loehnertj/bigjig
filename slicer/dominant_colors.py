'''Find the dominant colors of an image or puzzle board.

``find_colors`` finds dominant colors in a single given QImage.

``update_colors_all_pieces`` finds dominant colors in the given puzzle board.

You can execute this module to recalculate dominant colors for an existing puzzle:

``python -m slicer.dominant_colors <path_to_puzzlefolder>``
'''

import logging
import sys
import os
import attr
import itertools as it
import numpy as np
try:
    from scipy.ndimage.measurements import center_of_mass
except ImportError:
    print('scipy unavailable: color extraction will be less accurate.')
    center_of_mass = None
from qtpy.QtGui import QImage
from puzzleboard.puzzle_board import PuzzleBoard

#import matplotlib.pyplot as plt

__all__ = [
    'find_colors',
    'update_colors_all_pieces',
]

def L():
    return logging.getLogger(__name__)

@attr.s
class Cluster:
    aLbsh = attr.ib([0, 0, 0])
    radius = attr.ib(0.0)

    @property
    def aLb(self):
        ash, L, bsh = self.aLbsh
        return ash-90., L, bsh-110.
    
    @property
    def xyz(self):
        a, L, b = self.aLb
        LL = (L + 16.) / 116.
        xyz = np.array([
            LL + a/500.,
            LL,
            LL - b/200.
        ])
        delta = 6./29.
        mask = (xyz > delta)
        xyz[mask] = xyz[mask]**3.
        xyz[~mask] = 3*delta*delta*(xyz[~mask]-4./29.)
        xyz = xyz * np.array([ 0.950456, 1.0, 1.088754 ])
        return xyz.tolist()

    @property
    def rgb(self):
        xyz = np.array(self.xyz)
        trafo = np.array([
            [ 3.24096994, -1.53738318, -0.49861076],
            [-0.96924364, 1.8759675, 0.04155506],
            [0.05563008, -0.20397696, 1.05697151]
        ])
        rgb_lin = trafo.dot(xyz)
        mask = (rgb_lin < 0.0031308)
        rgb_lin[mask] = 12.92*rgb_lin[mask]
        rgb_lin[~mask] = 1.055*(rgb_lin[~mask]**(5/12.) - 0.055)
        rgb = (rgb_lin * 255.0).clip(0., 255.)
        return rgb

    
def qimage2array(image):
    if image.format() != QImage.Format_ARGB32:
        image = image.convertToFormat(QImage.Format_ARGB32)
    w = image.width()
    h = image.height()
    ptr = image.constBits()
    ptr.setsize(image.byteCount())
    a = np.array(ptr, dtype='uint8').reshape(h, w, 4)
    return a


def debug_show(imgarr, old_clusters, clusters):
    import matplotlib.pyplot as plt
    f = plt.figure()
    ax = f.subplots()
    ax.imshow(imgarr[:, :, [2, 1, 0, 3]])
    f = plt.figure()
    ax = f.subplots()
    ax.imshow(np.array(
        [
            [cluster.rgb.astype(int) for cluster in old_clusters],
            [cluster.rgb.astype(int) for cluster in clusters]
        ]
    ))

from contextlib import contextmanager
import time
@contextmanager
def debug_profile(msg):
    t1 = time.time()
    yield
    t2 = time.time()
    L().info(msg+': %s ms', 1000.*(t2-t1))



# required methods
def bgr2aLb(image):
    '''Transforms [x, y, RGB]-Array to [x, y, L*a*b] array.

    The strange ordering is matched to our specific case.
    '''

    # reorder to RGB to keep sanity, also rescale to 1.0
    image = image[:,:,[2,1,0]] / 255.0
    # now we can mess around in image

    # Degamma
    mask = (image < 0.04045)
    image[mask] = image[mask] / 12.92
    image[~mask] = ((image[~mask] + 0.055) / 1.055) ** 2.4

    # Convert sRGB to XYZ
    matrix = np.array(
        [[0.41239080, 0.35758434, 0.18048079],
        [0.21263901, 0.71516868, 0.07219232],
        [0.019933082, 0.11919478, 0.95053215]])

    xyz = np.einsum('ij,mnj->mni', matrix, image)

    # D65 illuminant
    xyz[:, :, 0] /= 0.950456
    xyz[:, :, 2] /= 1.088754 

    # Calculate L, a, b from XYZ
    # apply ramping function
    mask = (xyz > 0.008856)
    xyz[mask] = xyz[mask]**(1/3.)
    xyz[~mask] = xyz[~mask] * 7.787 + (16./116.)

    # a*
    xyz[:,:,0] = (500. * (xyz[:,:,0] - xyz[:,:,1])).clip(-90., 99.)
    # b*
    xyz[:,:,2] = (200. * (xyz[:,:,1] - xyz[:,:,2])).clip(-110., 99.)
    # L*
    xyz[:,:,1] = (116. * xyz[:,:,1] - 16.0).clip(0., 100.)

    # xyz now contains a*, L*, b*
    return xyz

        
aa = np.linspace(0, 189, 190)[:,None,None]
LL = np.linspace(0., 100., 101)[None,:,None]
bb = np.linspace(0., 209., 210)[None,None,:]
def distsq(cluster):
    """square of euclidean distance"""
    ca, cL, cb = cluster.aLbsh
    result= (aa-ca)**2 + (LL-cL)**2 + (bb-cb)**2
    return result


def find_colors(image, cluster_radius=0.33, threshold=0.01):
    '''Finds dominant colors in the image.

    The algorithm works roughly like this:
    
     * Tally up all image pixels in Lab space.
     * Scan the Lab space with a fixed and find the (raster) color with most counts nearby.
     * Remember this color and discard counts within the cluster
     * Repeat until most of the image's colors are covered by clusters.
     * Then, calculate actual center-of-mass for all clusters by k-means.
    
    Parameters:
        image (QImage instance): the image to analyse
        cluster_radius (float): size of cluster sphere (relative to L* axis)
        threshold (float): min percentage of pixels required in a cluster

    Returns:
        List of lists [r,g,b]

    The cluster_radius determines the "granularity" of the result. Lower
    cluster_radius will lead to dramatically longer runtimes.
    
    Smoothing: Preferably do *not* apply pre-smoothing. It tends to degrade the result.
    '''
    L().debug('-load image')
    w = image.width()
    h = image.height()
    imgarr = qimage2array(image)
    
    imgarr_flat = imgarr.reshape(w*h, 4)
    L().debug('-convert to Lab')
    aLb_flat = bgr2aLb(imgarr).reshape(w*h, 3)

        
    # Bounds of Lab: 
    # https://stackoverflow.com/questions/19099063/what-are-the-ranges-of-coordinates-in-the-cielab-color-space
    # Shift to all-positive values
    # a* : +90
    aLb_flat[:,0] += 90.0
    # b* : +110
    aLb_flat[:,2] += 110.0

    L().debug('- tally')
    colors = np.zeros((190, 101, 210), dtype=float)
    cidx = tuple([(aLb_flat[:, n]).astype(int) for n in [0,1,2]])
    # add up weighted by alpha value
    imgarr_alpha = imgarr_flat[:,3]
    np.add.at(colors, cidx, imgarr_alpha)
    
    # normalize to % of image; 255.0 = max alpha value
    colors /= imgarr_alpha.sum()
    
    L().debug('- find clusters')
    # Set initial clusters list empty.
    clusters = []
    # REPEAT:
    while True:
        # Create copy of the bin matrix and exclude existing clusters. ("remainder matrix")
        remainder = colors.copy()

        for cluster in clusters:
            remainder[distsq(cluster) <= (cluster.radius)**2] = 0.0
            
        # Scan the remainder matrix with a fixed raster, and find the color with most (leftover) pixels nearby.
        sradius = int(100.*cluster_radius)//2
        raster_a = np.arange(sradius//2, 190, sradius)
        raster_L = np.arange(sradius//2, 101, sradius)
        raster_b = np.arange(sradius//2, 210, sradius)
        counts = np.array([
            [
                ia, iL, ib,
                remainder[
                    max(ia-sradius, 0):(ia+sradius),
                    max(iL-sradius, 0):(iL+sradius),
                    max(ib-sradius, 0):(ib+sradius)
                ].sum()
            ]
            for ia, iL, ib in it.product(raster_a, raster_L, raster_b)
        ])
        maxind = np.argmax(counts[:,3])
        aLbsh, percentage = counts[maxind, 0:3], counts[maxind, 3]
        
        # If the pixels make up <x% of the image, exit here.
        if percentage < threshold:
            break
        
        # Otherwise create a new cluster around the scan point.
        new_cluster = Cluster(aLbsh=aLbsh, radius=100.*cluster_radius)
        clusters.append(new_cluster)
        
    # Relax cluster positions of all clusters.
    old_clusters = clusters
    L().debug('- k-means')
    if center_of_mass:
        clusters = relax_cluster_positions(colors, clusters)

    #debug_show(imgarr, old_clusters, clusters)
    L().debug('- done')
    return [c.rgb.astype(int).tolist() for c in clusters]
        
        
def relax_cluster_positions(colors, clusters, move_threshold=3.0):
    clusters = [Cluster(aLbsh=c.aLbsh, radius=c.radius) for c in clusters]
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
            center = np.array(center)
            moved = max(moved, sum((center-cluster.aLbsh)**2)**0.5)
            cluster.aLbsh = center
    return clusters

def update_colors_all_pieces(board, qimages=None):
    '''Calculate and store dominant colors for all pieces.

    Parameters:
        board (PuzzleBoard instance): board to update.
        qimages (dict pieceid->QImage): piece images.

    Missing piece images are loaded on the fly.
    '''
    qimages = qimages or {}
    for piece in board.pieces:
        try:
            img = qimages[piece.id]
        except KeyError:
            path = os.path.join(board.imagefolder, piece.image)
            img = QImage(path)
        piece.dominant_colors = find_colors(img)
        L().info('%s %s %s', piece.id, piece.image, piece.dominant_colors)

def main(puzzlepath):
    board = PuzzleBoard.from_folder(puzzlepath)
    update_colors_all_pieces(board)
    board.save_puzzle()

def testmain(filename):
    import matplotlib.pyplot as plt
    from pathlib import Path
    from random import choice
    p = Path(filename)
    if p.is_dir():
        files = list(p.glob('*.png'))
        p = choice(files)

    image = QImage(str(p))
    clusters = find_colors(image)
    plt.show()

if __name__=='__main__':
    logging.basicConfig(level='INFO')
    main(sys.argv[1])