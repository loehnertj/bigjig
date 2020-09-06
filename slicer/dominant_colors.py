'''Find the dominant colors of an image or puzzle board.

``find_colors`` finds dominant colors in a single given QImage.

``update_colors_all_pieces`` finds dominant colors in the given puzzle board.

You can execute this module to recalculate dominant colors for an existing puzzle:

``python -m slicer.dominant_colors <path_to_puzzlefolder>``
'''

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
from PyQt4.QtGui import QImage
from puzzleboard.puzzle_board import PuzzleBoard

#import matplotlib.pyplot as plt

__all__ = [
    'find_colors',
    'update_colors_all_pieces',
]

@attr.s
class Cluster:
    rgb = attr.ib([0, 0, 0])
    radius = attr.ib(0.0)
    
def qimage2array(image):
    assert image.format() == QImage.Format_ARGB32
    w = image.width()
    h = image.height()
    ptr = image.constBits()
    ptr.setsize(image.byteCount())
    a = np.array(ptr, dtype='uint8').reshape(h, w, 4)
    return a


def debug_show(imgarr, old_clusters, clusters):
    f = plt.figure()
    ax = f.subplots()
    ax.imshow(imgarr[:, :, [2, 1, 0, 3]])
    f = plt.figure()
    ax = f.subplots()
    ax.imshow(np.array(
        [
        #    [cluster.rgb for cluster in old_clusters],
            [cluster.rgb for cluster in clusters]
        ]
    ))


# required methods
scale = np.linspace(0., 1.0, 64, endpoint=False)
#RR, GG, BB = np.meshgrid(scale, scale, scale)
RR = scale[:,None,None]
GG = scale[None,:,None]
BB = scale[None,None,:]
def distsq(cluster):
    """square of euclidean distance"""
    cr, cg, cb = cluster.rgb
    result= (RR-cr)**2 + (GG-cg)**2 + (BB-cb)**2
    return result
        

def find_colors(image, cluster_radius=0.25, threshold=0.01):
    '''Finds dominant colors in the image.

    The algorithm works roughly like this:
    
     * Tally up all image pixels in R,G,B space.
     * Scan the RGB space with a fixed and find the (raster) color with most counts nearby.
     * Remember this color and discard counts within the cluster
     * Repeat until most of the image's colors are covered by clusters.
     * Then, calculate actual center-of-mass for all clusters by k-means.
    
    Parameters:
        image (QImage instance): the image to analyse
        cluster_radius (float): size of cluster sphere
        threshold (float): min percentage of pixels required in a cluster

    Returns:
        List of lists [r,g,b]

    The cluster_radius determines the "granularity" of the result. Lower
    cluster_radius will lead to dramatically longer runtimes.
    
    Smoothing: Preferably do *not* apply pre-smoothing. It tends to degrade the result.
    '''
    w = image.width()
    h = image.height()
    imgarr = qimage2array(image)
    
    imgarr_flat = imgarr.reshape(w*h, 4)
        
    # bin all pixels into a 64x64x64 array of all possible RGB coordinates.
    colors = np.zeros((64, 64, 64), dtype=float)
    cidx = tuple([(imgarr_flat[:, n]/4.).astype(int) for n in [2,1,0]])
    # add up weighted by alpha value
    imgarr_alpha = imgarr_flat[:,3]
    np.add.at(colors, cidx, imgarr_alpha)
    
    # normalize to % of image; 255.0 = max alpha value
    colors /= imgarr_alpha.sum()
    
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

    #debug_show(imgarr, old_clusters, clusters)
    return [(c.rgb*255).astype(int).tolist() for c in clusters]
        
        
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
        print(piece.id, piece.image, piece.dominant_colors)

def main(puzzlepath):
    board = PuzzleBoard.from_folder(puzzlepath)
    update_colors_all_pieces(board)
    board.save_puzzle()

def testmain(filename):
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
    main(sys.argv[1])