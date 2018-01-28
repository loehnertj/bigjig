

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

from PyQt4.QtCore import QLineF, QPointF
from PyQt4.QtGui import QPainterPath
 
from .util import getBestFitExtended

rotations = 6

class RotrexCell(object):
    def __init__(self, horiz, vert, tl, tr, bl, br, id_corner, id_tri, id_rect):
        # Please refer to the svg image.
        self.horiz = horiz
        self.vert = vert
        self.tl = tl
        self.tr = tr
        self.bl = bl
        self.br = br
        
        # ids of top and left piece in cell
        self.id_corner = id_corner
        self.id_tri = id_tri
        self.id_rect = id_rect
        
    @classmethod
    def create(cls, edgefunc, idfunc):
        edges = [edgefunc() for n in range(6)]
        ids = [idfunc() for n in range(3)]
        args = edges+ids
        return cls(*args)
    
dummy_cell = RotrexCell(*([None]*9))
        
def check_collisions(edge, others, collision_tries, engine, collision_shrink_factor=.95):
    '''collision checks for edge.
    implements automatic retrying and shrinking, as well as final verdict (pluglessness).
    edge is the edge under test.
    others is a list of the edges that edge might collide against. (None = Skip)
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
        offenders = []
        engine.out_of_bounds(edge, offenders)
        for other in others:
            if other is None: continue
            edge.intersects(other, offenders)
        if not offenders: break
    # offenders left after N tries?
    if offenders:
        # give up and make the colliding borders plugless.
        edge.is_plugless = True;
        for border in offenders: border.is_plugless = True
        
def itercells(cells):
    '''yields (x, y, cell, cell_left, cell_above, is_odd_cell)'''
    Nx = len(cells)
    Ny = len(cells[0])
    for x in range(Nx):
        for y in range(Ny):
            yield (
                x,
                y,
                cells[x][y],
                cells[x-1][y] if x>0 else dummy_cell,
                cells[x][y-1] if y>0 else dummy_cell,
                (x+y)%2==1
            )

def generate_grid(engine, piece_count, image_width, image_height):
    e = engine
    R3 = sqrt(3.0)
    xunit = 1.5 + R3
    x1, x2, x3, x4 = [ x/xunit for x in (0.5, 1.0, .5+R3, 1.+R3) ]
    yunit = 1.0 + 0.5 * R3
    y1, y2 = [ y / yunit for y in (0.5*R3, 1.0) ]
    
    # number of tries to resolve collision
    collision_tries = int(10 * e.settings.plug_size * e.settings.plug_size)
    if (collision_tries < 5): collision_tries = 5
    
    piece_ids = it.count()
    xCount, yCount = getBestFitExtended(1.0*image_width/image_height*yunit/xunit, piece_count, 3.0, 1., 2., 1.)
    cellWidth = 1.0 * image_width / xCount
    cellHeight = 1.0 * image_height / yCount
    
    # rationale: knobs should visually cover the same fraction of area as for the rect grid.
    length_base = sqrt(cellWidth * cellHeight / 3.0) * e.settings.plug_size;
    unit = lambda x1, y1, x2, y2: QLineF(x1*cellWidth, y1*cellHeight, x2*cellWidth, y2*cellHeight)
    # generate borders
    cells = []
    
    # grid is made 1 unit larger in both dimensions, to store the right and bottom borders.
    for x in range(xCount+1):
        cellRow = []
        cells.append(cellRow)
        for y in range(yCount+1):
            # generate usual borders first, and cater for the "edge" cases afterwards.
            cell = RotrexCell.create(
                lambda: e.init_edge(None, length_base, is_straight=False),
                lambda: next(piece_ids)
            )
            cellRow.append(cell)
    
    flip = e.settings.alternate_flip
    for x, y, cell, c_left, c_above, odd_cell in itercells(cells):
        # determine border direction
        cell.horiz.flipped |= (odd_cell == flip)
        cell.vert.flipped |= (odd_cell == flip)
        cell.tl.flipped |= (odd_cell != flip)
        cell.tr.flipped |= (odd_cell != flip)
        cell.bl.flipped |= (odd_cell == flip)
        cell.br.flipped |= (odd_cell == flip)
        
        # set border vectors
        cell.horiz.unit_x = unit(
            x-x1,
            y + (y2 if odd_cell else y1),
            x + x1,
            y + (y2 if odd_cell else y1)
            )
        cell.vert.unit_x = unit(
            x + (x1 if odd_cell else x4),
            y - y2,
            x + (x1 if odd_cell else x4),
            y + y2
            )
        cell.tl.unit_x = unit(
            x + (x3 if odd_cell else x2),
            y,
            x + x1,
            y + (y2 if odd_cell else y1)
            )
        cell.tr.unit_x = unit(
            x + (x3 if odd_cell else x2),
            y,
            x + x4,
            y + (y1 if odd_cell else y2)
            )
        cell.bl.unit_x = unit(
            x + x1,
            y + (y2 if odd_cell else y1),
            x + (x2 if odd_cell else x3),
            y + 1.0
            )
        cell.br.unit_x = unit(
            x + x4,
            y + (y1 if odd_cell else y2),
            x + (x2 if odd_cell else x3),
            y + 1.0
            )
            
        # pieces at frame
        # top edge
        if y==0:
            cell.vert.unit_x.setP1(QPointF(cell.vert.unit_x.x1(), y*cellHeight))
        # left edge
        if x==0:
            cell.horiz.unit_x.setP1(QPointF(x * cellWidth, cell.horiz.unit_x.y1()))
        # right edge
        if x==xCount:
            cell.horiz.unit_x.setP2(QPointF(x * cellWidth, cell.horiz.unit_x.y2()))
        # bottom
        if y==yCount:
            cell.vert.unit_x.setP2(QPointF(cell.vert.unit_x.x2(), y*cellHeight))
            
        
        # collision checking
        if not odd_cell:
            checks = [
                (cell.horiz, [c_left.tr, (cells[x-1][y+1].vert if (x>0 and y<yCount) else None)]),
                (cell.vert, [c_above.br]),
                (cell.tl, [c_above.bl, cell.horiz]),
                (cell.tr, [c_above.br, cell.tl, cell.vert]),
                (cell.bl, [cell.tl]),
                (cell.br, [cell.bl, cell.tr]),
            ]
        else:
            checks = [
                (cell.horiz, [c_left.br, c_left.vert]),
                (cell.vert, [c_above.bl, c_above.horiz, cell.horiz]),
                (cell.tl, [c_above.bl, cell.vert]),
                (cell.tr, [c_above.br, cell.tl]),
                (cell.bl, [cell.tl, cell.horiz]),
                (cell.br, [cell.bl, cell.tr]),
            ]
        for edge, others in checks:
            check_collisions(edge, others, collision_tries, e)
                    
    # done generating grid description. render everything.
    for x, y, cell, c_left, c_above, odd_cell in itercells(cells):
        if not odd_cell:
            # corner piece is hexagonal.
            # this is a real beast since it might be halved or even quartered.
            path = QPainterPath()
            
            # upper half
            path.moveTo((x + (0. if x==0 else -x2)) * cellWidth, y * cellHeight)
            if y==0:
                path.lineTo((x + (0. if x==xCount else x2)) * cellWidth, 0.0)
            else:
                if x==0:
                    path.lineTo(c_above.horiz.unit_x.p1())
                else:
                    e.add_plug_to_path(path, cells[x-1][y-1].br, True)
                e.add_plug_to_path(path, c_above.horiz, False)
                if x==xCount:
                    path.lineTo(xCount*cellWidth, y*cellHeight)
                else:
                    e.add_plug_to_path(path, c_above.bl)
            # lower half
            if y==yCount:
                path.lineTo((x + (0. if x==0 else -x2)) * cellWidth, y*cellHeight)
            else:
                if x==xCount:
                    path.lineTo(cell.horiz.unit_x.p2())
                else:
                    e.add_plug_to_path(path, cell.tl, False)
                e.add_plug_to_path(path, cell.horiz, True)
                if x==0:
                    path.lineTo(x*cellWidth, y*cellHeight)
                else:
                    e.add_plug_to_path(path, c_left.tr, True)
            e.make_piece_from_path(cell.id_corner, path)
            
            # triangle piece
            if x < xCount:
                path = QPainterPath()
                path.moveTo(cell.tl.unit_x.p1())
                if y==0:
                    path.lineTo((x+x4) * cellWidth, 0.)
                else:
                    e.add_plug_to_path(path, c_above.br, True)
                e.add_plug_to_path(path, cell.vert, False)
                if y==yCount:
                    path.lineTo(cell.tl.unit_x.p1())
                else:
                    e.add_plug_to_path(path, cell.tr, True)
                e.make_piece_from_path(cell.id_tri, path)
                
        else: # odd cell
            # rect piece
            # might be halved or quartered.
            path = QPainterPath()
            path.moveTo((x + (0. if x==0 else -x1)) * cellWidth, (y+(0. if y==0 else -y2))*cellHeight)
            if y==0:
                path.lineTo((x + (0. if x==xCount else x1))*cellWidth, 0.)
            else:
                e.add_plug_to_path(path, c_above.horiz, False)
            if x==xCount:
                path.lineTo(xCount*cellWidth, (y + (0. if y==yCount else y2))*cellHeight)
            else:
                e.add_plug_to_path(path, cell.vert, False)
            if y==yCount:
                path.lineTo((x + (0. if x==0 else -x1))*cellWidth, y*cellHeight)
            else:
                e.add_plug_to_path(path, cell.horiz, True)
            if x==0:
                path.lineTo(0., (y + (0. if y==0 else -y2))*cellHeight)
            else:
                e.add_plug_to_path(path, c_left.vert, True)
            e.make_piece_from_path(cell.id_corner, path)
            
            # triangle piece
            if x < xCount:
                path = QPainterPath()
                path.moveTo(cell.tl.unit_x.p1())
                if y==yCount:
                    path.lineTo((x+x1)*cellWidth, yCount*cellHeight)
                else:
                    e.add_plug_to_path(path, cell.tl, False)
                e.add_plug_to_path(path, cell.vert, True)
                if y==0:
                    path.lineTo(cell.tl.unit_x.p1())
                else:
                    e.add_plug_to_path(path, c_above.bl, False)
                e.make_piece_from_path(cell.id_tri, path)
                
        # inner rect piece: same topology for even and odd cell
        if x<xCount and y<yCount:
            path = QPainterPath()
            path.moveTo(cell.tr.unit_x.p1())
            e.add_plug_to_path(path, cell.tr, False)
            e.add_plug_to_path(path, cell.br, False)
            e.add_plug_to_path(path, cell.bl, True)
            e.add_plug_to_path(path, cell.tl, True)
            e.make_piece_from_path(cell.id_rect, path)
                
    # generate relations
    for x, y, cell, c_left, c_above, odd_cell in itercells(cells):
        # Each cell takes care of the relations corresponding to the borders it contains.
        # horiz
        if y<yCount:
            e.add_relation(cell.id_corner, cells[x][y+1].id_corner)
        # vert
        if x<xCount:
            e.add_relation(cell.id_tri, cells[x+(0 if odd_cell else 1)][y].id_corner)
            
        # inner-cell borders
        if y<yCount and x<xCount:
            e.add_relation(cell.id_tri, cell.id_rect)
            e.add_relation(cell.id_rect, cells[x][y+1].id_tri)
            e.add_relation(cell.id_rect, cells[x  ][y + (1 if odd_cell else 0)].id_corner)
            e.add_relation(cell.id_rect, cells[x+1][y + (0 if odd_cell else 1)].id_corner)
            
                           