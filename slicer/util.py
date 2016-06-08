from random import random
from math import exp, log, sqrt, floor, ceil, sin, cos, pi

def dotproduct(a, b):
    return a.x()*b.x() + a.y()*b.y()

def dsin(angle): 
    return sin(angle*pi/180.)

def dcos(angle):
    return cos(angle*pi/180.)

def getBestFit(target_aspect, approx_count):
    nx_exact = sqrt(approx_count * target_aspect)
    # avoid taking the sqrt again
    ny_exact = approx_count / nx_exact

    # catch very odd cases
    if (nx_exact < 1): nx_exact = 1.01
    if (ny_exact < 1): ny_exact = 1.01

    aspect1 = floor(nx_exact) / ceil(ny_exact)
    aspect2 = ceil(nx_exact) / floor(ny_exact)

    aspect1 = target_aspect - aspect1
    aspect2 = aspect2 - target_aspect

    if (aspect1 < aspect2): 
        ny_exact += 1.0 
    else:
        nx_exact += 1.0

    return int(floor(nx_exact) + 0.1), int(floor(ny_exact) + 0.1)

def getBestFitExtended(target_aspect, approx_count, tiles_per_cell, additional_tiles_per_row, additional_tiles_per_column, additional_tiles):
    '''
    solves the equations
     N = TPC * x * y  +  ATPC * x + ATPR * y + AT
     target_aspect = x / y
   
    for x, y and rounds them to the nearest integer values giving least distance to target_aspect.
    '''
    p_half = (target_aspect * additional_tiles_per_column + additional_tiles_per_row) / (2.0 * target_aspect * tiles_per_cell)
    q = (approx_count - additional_tiles) / (target_aspect * tiles_per_cell)
    
    p_half_sq = p_half*p_half
    if (p_half_sq + q < 0):
        return 1, 1
    
    ny_exact = -p_half + sqrt(p_half_sq + q)
    nx_exact = target_aspect * ny_exact

    # catch very odd cases
    if (nx_exact < 1): nx_exact = 1.01
    if (ny_exact < 1): ny_exact = 1.01

    aspect1 = floor(nx_exact) / ceil(ny_exact)
    aspect2 = ceil(nx_exact) / floor(ny_exact)
    aspect3 = ceil(nx_exact) / ceil(ny_exact)

    aspect1 = target_aspect - aspect1
    aspect2 = aspect2 - target_aspect
    aspect3 = abs(aspect3 - target_aspect)

    if (aspect1 < aspect2):
        ny_exact += 1.0 
        if (aspect3 < aspect1): nx_exact += 1.0
    else:
        nx_exact += 1.0
        if (aspect3 < aspect2): ny_exact += 1.0

    return int(floor(nx_exact) + 0.1), int(floor(ny_exact) + 0.1)

def skew_randnum(x, a):
    '''skews x with "strength" a.
    x is expected to lie within [0, 1].
    a = +/-1 is already a very strong skew.
    negative a: skew towards x=0, positive: skew towards x=1.
    '''
    if a==0: return x

    asq = exp(-2 * abs(a))
    if a>0: x = 1-x

    mp2 = (x-1) * (2/asq - 1)
    q = (x-1)*(x-1) - 1

    # We apply a function on x, which is a hyperbola through (0,0) and (1,1)
    # with (1, 0) as focal point. You really don't want to know the gory details.
    x = mp2 + sqrt(mp2*mp2 - q)

    if a>0: x = 1-x
    return x

def nonuniform_rand(min, max, sigma, skew):
    # 0.4247: sigma at which distribution function is 1/2 of max at interval boundaries

    if sigma > 0.4247:
        # "wide" distribution, use rejection sampling
        ssq = 2 * sigma * sigma
        x, y = 0., 2.
        while y > exp(-(x-0.5)*(x-0.5)/ssq):
            x = random()
            y = random()
        randNum = x
    else:
        # "narrow" distribution, use Marsaglia method until a random number within 0, 1 is found.

        randNum = -1.
        while randNum < 0.:
            q = 2
            while q>1:
                u1 = 2.*random()-1.
                u2 = 2.*random()-1.
                q = u1*u1 + u2*u2
            p = sqrt(-2 * log(q) / q) * sigma
            x1 = u1 * p + 0.5 
            x2 = u2 * p + 0.5

            if (x1>= 0 and x1 <= 1):
                randNum = x1
            elif (x2>=0 and x2<=1):
                randNum = x2
    return min + (max - min) * skew_randnum(randNum, skew)
