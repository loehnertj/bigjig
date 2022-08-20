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
 
from qtpy.QtCore import QLineF
from qtpy.QtGui import QPainterPath
 
from .util import getBestFit

rotations = 4

def generate_grid(engine, piece_count, image_width, image_height):
    e = engine
    # number of tries to resolve collision
    collision_tries = int(10 * e.settings.plug_size * e.settings.plug_size)
    if (collision_tries < 5): collision_tries = 5
    collision_shrink_factor = 0.95


    # calculate piece counts
    xCount, yCount = getBestFit(1.0 * image_width / image_height, piece_count)

    pieceWidth = int(image_width / xCount)
    pieceHeight = int(image_height / yCount)
    length_base = (pieceWidth + pieceHeight) * 0.5 * e.settings.plug_size

    horizontalPlugParams = []
    verticalPlugParams = []

    for x in range(xCount+1):
        hParamRow = []
        vParamRow = []
        horizontalPlugParams.append(hParamRow)
        verticalPlugParams.append(vParamRow)
        for y in range(yCount+1):
            odd_tile = ((x+y) % 2 == 1)
            
            #borders along X axis
            unit_x = QLineF(x*pieceWidth, y*pieceHeight, (x+1)*pieceWidth, y*pieceHeight)
            hParams = e.init_edge(unit_x, length_base, is_straight=(y==0 or y==yCount))
            hParams.flipped ^= odd_tile ^ e.settings.alternate_flip
            if (x>0 and x < xCount):
                hParams.smooth_join_to(horizontalPlugParams[x-1][y])
            hParamRow.append(hParams)
            
            #borders along Y axis
            unit_x = QLineF(x*pieceWidth, y*pieceHeight, x*pieceWidth, (y+1)*pieceHeight)
            vParams = e.init_edge(unit_x, length_base, is_straight=(x==0 or x==xCount))
            vParams.flipped ^= odd_tile
            if (y>0 and y < yCount):
                vParams.smooth_join_to(verticalPlugParams[x][y-1])
            vParamRow.append(vParams)

            # collision checking
            # vertical plug
            if (x > 0 and x < xCount):
                v_intersects = True
                for i in range(collision_tries):
                    offenders = []
                    v_intersects = vParams.intersects(horizontalPlugParams[x-1][y], offenders)
                    if (y<yCount):
                        v_intersects |= vParams.intersects(horizontalPlugParams[x-1][y+1], offenders)
                    if not v_intersects: 
                        break
                    else:
                        #qDebug() << "collision: vertical edge, x=" << x << ", y=" << y
                        vParams.size_correction *= collision_shrink_factor
                        vParams.rerandomize_edge(keep_endangles=True)
                if v_intersects:
                    vParams.is_plugless = True
                    for offender in offenders:
                        offender.is_plugless = True
                        
            if (y>0 and y < yCount):
                h_intersects = True
                for i in range(collision_tries):
                    offenders = []
                    h_intersects = hParams.intersects(verticalPlugParams[x][y-1], offenders)
                    if (x<xCount):
                        h_intersects |= hParams.intersects(verticalPlugParams[x][y], offenders)
                    if not h_intersects:
                        break
                    else:
                        #qDebug() << "collision: horizontal edge, x=" << x << " y=" << y
                        hParams.size_correction *= collision_shrink_factor
                        hParams.rerandomize_edge(keep_endangles=True)
                if (h_intersects):
                    hParams.is_plugless=True
                    for offender in offenders:
                        offender.is_plugless=True

    #create pieces
    for x in range(xCount):
        for y in range(yCount):
            #create the mask path
            path = QPainterPath()
            path.moveTo(horizontalPlugParams[x][y].unit_x.p1())

            # top, right, bottom, left plug
            e.add_plug_to_path(path, horizontalPlugParams[x][y], False)
            e.add_plug_to_path(path, verticalPlugParams[x+1][y], False)
            e.add_plug_to_path(path, horizontalPlugParams[x][y+1], True)
            e.add_plug_to_path(path, verticalPlugParams[x][y], True)

            e.make_piece_from_path(x + y * xCount, path)

    #create relations
    for x in range(xCount):
        for y in range(yCount):
            if (x != 0): e.add_relation(x + y * xCount, (x - 1) + y * xCount)
            if (y != 0): e.add_relation(x + y * xCount, x + (y - 1) * xCount)