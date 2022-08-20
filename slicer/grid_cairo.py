
#***************************************************************************
#   Copyright  2010 Johannes Loehnert <loehnert.kde@gmx.de>
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public
#   License as published by the Free Software Foundation; either
#   version 2 of the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#**************************************************************************/
 
import itertools as it
from math import sqrt

from qtpy.QtCore import QLineF
from qtpy.QtGui import QPainterPath
 
from .util import getBestFitExtended

rotations = 4

class CairoCell(object):
    def __init__(self, corner, tl, tr, bl, br, id_top, id_left):
        # Please refer to the svg image.
        self.corner = corner
        self.tl = tl
        self.tr = tr
        self.bl = bl
        self.br = br
        
        # ids of top and left piece in cell
        self.id_top = id_top
        self.id_left = id_left
        
def check_collisions(edge, checkfunc, collision_tries, collision_shrink_factor=.95):
    '''collision checks for edge.
    implements automatic retrying and shrinking, as well as final verdict (pluglessness).
    edge is the edge under test.
    checkfunc takes edge as argument and returns a list of colliding edges.
    collision_tries is the number of retries. Must be at least 1.
    collision_shrink_factor is the factor by which the edge size is multiplied on
    each retry.
    '''
    
    intersects=False
    for i in range(collision_tries):
        if i>0:
            #qDebug() << "collision: uleft edge, x=" << x << ", y=" << y;
            edge.size_correction *= collision_shrink_factor
            edge.rerandomize_edge()
        offenders = checkfunc(edge)
        if not offenders: break
    if offenders:
        # give up and make the colliding borders plugless.
        edge.is_plugless = True;
        for border in offenders: border.is_plugless = True

def generate_grid(engine, piece_count, image_width, image_height):
    e = engine
    
    # number of tries to resolve collision
    collision_tries = int(10 * e.settings.plug_size * e.settings.plug_size)
    if (collision_tries < 5): collision_tries = 5
    
    piece_ids = it.count()
    xCount, yCount = getBestFitExtended(1.0*image_width/image_height, piece_count, 2.0, 1., 1., 0.)
    cellWidth = 1.0 * image_width / xCount
    cellHeight = 1.0 * image_height / yCount
    
    # rationale: knobs should visually cover the same fraction of area as for the rect grid.
    length_base = sqrt(cellWidth * cellHeight*0.5) * e.settings.plug_size;
    edge = lambda: e.init_edge(None, length_base, is_straight=False)
    unit = lambda x1, y1, x2, y2: QLineF(x1*cellWidth, y1*cellHeight, x2*cellWidth, y2*cellHeight)
    # generate borders
    cells = []
    
    # grid is made 1 unit larger in both dimensions, to store the right and bottom borders.
    for x in range(xCount+1):
        cellRow = []
        cells.append(cellRow)
        for y in range(yCount+1):
            odd_cell = ((x+y)%2==1)
            # generate usual borders first, and cater for the "edge" cases afterwards.
            cell = CairoCell(edge(), edge(), edge(), edge(), edge(),
                id_top = next(piece_ids), id_left = next(piece_ids)
            )
            cellRow.append(cell)
            
            # determine border direction
            if odd_cell:
                cell.tl.flipped = True
                cell.tr.flipped = True
                cell.bl.flipped = True
                cell.br.flipped = True
            
            if (e.settings.alternate_flip):
                cell.tl.flipped ^= True
                cell.tr.flipped ^= True
                cell.bl.flipped ^= True
                cell.br.flipped ^= True
            
            # set border vectors
            if odd_cell:
                cell.corner.flipped ^= (y%2==1)
                cell.corner.unit_x = unit(x-0.25, y, (x+0.25), y)
            else:
                cell.corner.flipped ^= (x%2==1)
                cell.corner.unit_x = unit(x, (y-0.25), x, (y+0.25))
                
            if odd_cell:
                d1 = 0.25
                d2 = 0.
            else:
                d1 = 0.
                d2 = 0.25
                
            cell.tl.unit_x = unit((x+d1), (y+d2), (x+0.5), (y+0.5))
            cell.tr.unit_x = unit((x+1-d2), (y+d1), (x+0.5), (y+0.5))
            cell.bl.unit_x = unit((x+d2), (y+1-d1), (x+0.5), (y+0.5))
            cell.br.unit_x = unit((x+1-d1), (y+1-d2), (x+0.5), (y+0.5))
            
            cell.tl.smooth_join_to(cell.br)
            cell.tr.smooth_join_to(cell.bl)
                
            # edges
            if y==0:
                if not odd_cell:
                    cell.corner.unit_x = unit(x, y, x, y+.25)
                else:
                    cell.corner.is_straight = True
            if (x==0):
                if odd_cell:
                    cell.corner.unit_x = unit(x, y, x+.25, y)
                else:
                    cell.corner.is_straight = True
            
            if y==yCount:
                if not odd_cell:
                    cell.corner.unit_x = unit(x, y-.25, x, y)
                else:
                    cell.corner.is_straight = True
            
            if x==xCount:
                if odd_cell:
                    cell.corner.unit_x = unit(x-.25, y, x, y)
                else:
                    cell.corner.is_straight=True
                
            # collision checking
            def corner_collisions(corner):
                offenders = []
                e.out_of_bounds(corner, offenders)
                if x>0 and y>0:
                    corner.intersects(cells[x-1][y-1].br, offenders)
                if x>0:
                    corner.intersects(cells[x-1][y].tr, offenders)
                if y>0:
                    corner.intersects(cells[x][y-1].bl, offenders)
                return offenders
                    
            check_collisions(cell.corner, corner_collisions, collision_tries)
                    
            # for inner borders, don't bother with the "outer" cells, they do not matter.
            if x < xCount and y < yCount:
                def tl_collisions(tl):
                    offenders = []
                    e.out_of_bounds(tl, offenders)
                    tl.intersects(cells[x][y].corner, offenders)
                    if odd_cell:
                        if y>0: tl.intersects(cells[x][y-1].bl, offenders)
                    else:
                        if x>0: tl.intersects(cells[x-1][y].tr, offenders)
                    return offenders
                
                def tr_collisions(tr):
                    offenders = []
                    e.out_of_bounds(tr, offenders)
                    tr.intersects(cells[x][y].tl, offenders)
                    if not odd_cell:
                        if y>0: tr.intersects(cells[x][y-1].br, offenders)
                    return offenders
                
                def bl_collisions(bl):
                    offenders = []
                    e.out_of_bounds(bl, offenders)
                    bl.intersects(cells[x][y].tl, offenders)
                    if odd_cell:
                        if x>0: bl.intersects(cells[x-1][y].br, offenders)
                    return offenders
                
                def br_collisions(br):
                    offenders = []
                    e.out_of_bounds(br, offenders)
                    br.intersects(cells[x][y].tr, offenders)
                    br.intersects(cells[x][y].bl, offenders)
                    return offenders
                
                check_collisions(cell.tl, tl_collisions, collision_tries)
                check_collisions(cell.tr, tr_collisions, collision_tries)
                check_collisions(cell.bl, bl_collisions, collision_tries)
                check_collisions(cell.br, br_collisions, collision_tries)
    
    # done generating grid description, render everything.

    for x, y in it.product(range(xCount+1), range(yCount+1)):
        odd_cell = ((x+y)%2==1)

        # TOP PIECE. Start after the corner edge.
        if x<xCount:
            path = QPainterPath()
            path.moveTo(cells[x][y].corner.unit_x.p2())
            if not odd_cell: e.add_plug_to_path(path, cells[x][y].corner, True)
            if y==0:
                # half piece
                path.lineTo(cells[x+1][y].corner.unit_x.p1())
            else:
                e.add_plug_to_path(path, cells[x][y-1].bl, False)
                e.add_plug_to_path(path, cells[x][y-1].br, True)
            if odd_cell: e.add_plug_to_path(path, cells[x+1][y].corner, False)
            if y==yCount:
                path.lineTo(cells[x][y].corner.unit_x.p2())
            else:
                e.add_plug_to_path(path, cells[x][y].tr, False)
                e.add_plug_to_path(path, cells[x][y].tl, True)
            e.make_piece_from_path(cells[x][y].id_top, path)
            
        if y<yCount:
            path = QPainterPath()
            path.moveTo(cells[x][y].corner.unit_x.p2())
            if x==xCount:
                path.lineTo(cells[x-1][y].br.unit_x.p1() if odd_cell else cells[x][y+1].corner.unit_x.p2())
            else:
                e.add_plug_to_path(path, cells[x][y].tl, False)
                e.add_plug_to_path(path, cells[x][y].bl, True)
            if not odd_cell:
                e.add_plug_to_path(path, cells[x][y+1].corner, True)
            if x==0:
                path.lineTo(cells[x][y].corner.unit_x.p1() if odd_cell else cells[x][y].tl.unit_x.p1())
            else:
                e.add_plug_to_path(path, cells[x-1][y].br, False)
                e.add_plug_to_path(path, cells[x-1][y].tr, True)
            if odd_cell:
                e.add_plug_to_path(path, cells[x][y].corner, False)
            e.make_piece_from_path(cells[x][y].id_left, path)

    # generate relations
    for x, y in it.product(range(xCount), range(yCount+1)):
        odd_cell = ((x+y)%2==1)
        #corner
        if odd_cell:
            if y>0 and y<yCount: e.add_relation(cells[x][y].id_left, cells[x][y-1].id_left)
        else:
            if x>0 and x<xCount: e.add_relation(cells[x][y].id_top, cells[x-1][y].id_top)
        # inner-cell borders
        if y<yCount and x<xCount:
            e.add_relation(cells[x][y].id_top, cells[x][y].id_left)
            e.add_relation(cells[x][y].id_top, cells[x+1][y].id_left)
            e.add_relation(cells[x][y].id_left, cells[x][y+1].id_top)
            e.add_relation(cells[x+1][y].id_left, cells[x][y+1].id_top)