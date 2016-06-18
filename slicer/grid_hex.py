
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

from PyQt4.QtCore import QLineF
from PyQt4.QtGui import QPainterPath
 
from .util import getBestFitExtended

rotations = 6

class HexCell(object):
    def __init__(self, uleft, lleft, horiz, id):
        # the border at the left edge, upper one
        self.uleft = uleft
        # the border at the left edge, lower one
        self.lleft = lleft
        # the horizontal border, either at the top cell edge
        # or vertically in the middle (odd cell)
        self.horiz = horiz

        # id of piece in cell (upper one for odd column)
        self.id = id
        
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
    ONE_SIXTH = 1/6.0
    
    # number of tries to resolve collision
    collision_tries = int(10 * e.settings.plug_size * e.settings.plug_size)
    if (collision_tries < 5): collision_tries = 5
    
    piece_ids = it.count()
    xCount, yCount = getBestFitExtended(1.0*image_width/image_height*1.7320508075689 / 1.5, piece_count, 1.0, 0., 0.5, 0.)
    cellWidth = 1.0 * image_width / xCount
    cellHeight = 1.0 * image_height / yCount
    
    # rationale: knobs should visually cover the same fraction of area as for the rect grid.
    length_base = sqrt(cellWidth * cellHeight) * e.settings.plug_size;
    # generate borders
    cells = []
    
    # grid is made 1 unit larger in both dimensions, to store the right and bottom borders.
    for x in range(xCount+1):
        cellRow = []
        cells.append(cellRow)
        for y in range(yCount+1):
            odd_column = (x%2==1)
            # generate usual borders first, and cater for the "edge" cases afterwards.
            cell = HexCell(
                uleft= e.init_edge(None, length_base, is_straight=False),
                lleft=e.init_edge(None, length_base, is_straight=False),
                horiz=e.init_edge(None, length_base, is_straight=False),
                id=next(piece_ids)
            )
            cellRow.append(cell)
            
            # determine border direction
            cell.horiz.flipped ^= (not e.settings.alternate_flip)
            cell.uleft.flipped ^= (not odd_column)
            cell.lleft.flipped ^= (odd_column ^ e.settings.alternate_flip)
            
            if (e.settings.alternate_flip and (y%2==1)):
                cell.horiz.flipped ^= (not odd_column)
                cell.uleft.flipped = not cell.uleft.flipped
                cell.lleft.flipped = not cell.lleft.flipped
            
            # determine border vectors
            if odd_column:
                xleft1 = (x-ONE_SIXTH) * cellWidth
                xleft2 = (x+ONE_SIXTH) * cellWidth
            else:
                xleft1 = (x + ONE_SIXTH) * cellWidth
                xleft2 = (x - ONE_SIXTH) * cellWidth
            xright = (x+1-ONE_SIXTH) * cellWidth;
            
            if x==0 or x == xCount:
                xleft1 = x * cellWidth
                xleft2 = x * cellWidth
            if x == xCount - 1:
                xright = (x+1)*cellWidth
            
            # and set
            cell.uleft.unit_x = QLineF(xleft1, y * cellHeight, xleft2, (y + 0.5) * cellHeight);
            cell.lleft.unit_x = QLineF(xleft2, (y + 0.5) * cellHeight, xleft1, (y + 1.0) * cellHeight);
            if odd_column:
                cell.horiz.unit_x = QLineF(
                    xleft2, (y + 0.5) * cellHeight, 
                    xright, (y + 0.5) * cellHeight
                )
            else:
                cell.horiz.unit_x = QLineF(
                    xleft1, y * cellHeight, 
                    xright, y * cellHeight
                )
                
            # frame borders
            if x==0 or x == xCount:
                cell.uleft.is_straight = True
                cell.lleft.is_straight = True
            if (y==0 or y == yCount) and not odd_column:
                cell.horiz.is_straight = True
                
            
            # collision checking
            # don't bother with the "outer" cells, they do not matter.
            if x < xCount and y < yCount:
                # ULEFT
                def uleft_collisions(uleft):
                    offenders = []
                    if x!=0: uleft.intersects(cells[x-1][y].horiz, offenders)
                    if y!=0: uleft.intersects(cells[x][y-1].lleft, offenders)
                    if y==0: 
                        if e.out_of_bounds(uleft): offenders.append(uleft)
                    return offenders
                
                # LLEFT
                def lleft_collisions(lleft):
                    offenders = []
                    lleft.intersects(cell.uleft, offenders)
                    if x!=0:
                        if odd_column:
                            lleft.intersects(cells[x-1][y+1].horiz, offenders)
                        else:
                            lleft.intersects(cells[x-1][y].horiz, offenders)
                    if y==yCount-1:
                        if e.out_of_bounds(lleft): offenders.append(lleft)
                    return offenders
                # HORIZ
                def horiz_collisions(horiz):
                    offenders = []
                    horiz.intersects(cell.uleft, offenders)
                    if odd_column:
                        horiz.intersects(cell.lleft, offenders)
                    else:
                        if y!=0:
                            horiz.intersects(cells[x][y-1].lleft, offenders)
                    return offenders
                    
                check_collisions(cell.uleft, uleft_collisions, collision_tries)
                check_collisions(cell.lleft, lleft_collisions, collision_tries)
                check_collisions(cell.horiz, horiz_collisions, collision_tries)
    
    # done generating grid description, render everything.

    for x, y in it.product(range(xCount), range(yCount+1)):
        path = QPainterPath()
        odd_column = (x%2==1)

        if y==yCount and not odd_column: continue

        path.moveTo(cells[x][y].uleft.unit_x.p1())
        if not odd_column:
            e.add_plug_to_path(path, cells[x][y].horiz, False)
            e.add_plug_to_path(path, cells[x+1][y].uleft, False)
            e.add_plug_to_path(path, cells[x+1][y].lleft, False)
            e.add_plug_to_path(path, cells[x][y+1].horiz, True)
            e.add_plug_to_path(path, cells[x][y].lleft, True)
            e.add_plug_to_path(path, cells[x][y].uleft, True)
        else:
            # now we have to deal with the half pieces
            if y==0:
                path.lineTo(cells[x+1][y].uleft.unit_x.p1())
            else:
                e.add_plug_to_path(path, cells[x][y-1].lleft, True)
                e.add_plug_to_path(path, cells[x][y-1].horiz, False)
                e.add_plug_to_path(path, cells[x+1][y-1].lleft, False)
            if y==yCount:
                path.lineTo(cells[x][y].uleft.unit_x.p1())
            else:
                e.add_plug_to_path(path, cells[x+1][y].uleft, False)
                e.add_plug_to_path(path, cells[x][y].horiz, True)
                e.add_plug_to_path(path, cells[x][y].uleft, True)

        e.make_piece_from_path(cells[x][y].id, path)

    # generate relations
    for x, y in it.product(range(xCount), range(yCount+1)):
        # piece above
        if y>0 and (y<yCount + x%2): e.add_relation(cells[x][y].id, cells[x][y-1].id)
        # piece to the right
        if x>0 and y < yCount: e.add_relation(cells[x][y].id, cells[x-1][y].id)
        # other piece to the right
        if x%2==1:
            if y>0: e.add_relation(cells[x][y].id, cells[x-1][y-1].id)
        else:
            if x>0 and y<yCount: e.add_relation(cells[x][y].id, cells[x-1][y+1].id)