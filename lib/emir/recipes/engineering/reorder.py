#
# Copyright 2010-2012 Universidad Complutense de Madrid
# 
# This file is part of PyEmir
# 
# PyEmir is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# PyEmir is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with PyEmir.  If not, see <http://www.gnu.org/licenses/>.
# 

'''Recipe for the reordering of frames.'''

import logging
from itertools import repeat, chain, izip
import os.path

import numpy
import pyfits

from numina.core import BaseRecipe, DataFrame

from emir.instrument.detector import CHANNELS_2

_logger = logging.getLogger("numina.recipes.emir")

class Recipe(BaseRecipe):
    '''Reordering Recipe.
    
    Recipe to reorder images created by the detector.
    '''
    
    def __init__(self, param, runinfo):
        super(Recipe, self).__init__(param, runinfo)
        
    def run(self, obsblock):

        f1 = lambda x: x
        f2 = lambda x: numpy.fliplr(numpy.transpose(x))
        f3 = lambda x: numpy.fliplr(numpy.flipud(x))
        f4 = lambda x: numpy.flipud(numpy.transpose(x))

        results = []
        
        for frame in obsblock.frames:
            # Using numpy memmap instead of pyfits
            # Images are a in a format unrecognized by pyfits
            _logger.debug('processing %s', frame.label)
            f = numpy.memmap(frame.label, dtype='>u2', mode='r', offset=36 * 80) 
            try:                                
                f.shape = (1024, 4096)
                rr = numpy.zeros((2048, 2048), dtype='int16')
                cc = chain(repeat(f1, 8), repeat(f2, 8), repeat(f3, 8), repeat(f4, 8))
                for idx, (channel, conv) in enumerate(izip(CHANNELS_2, cc)):
                    rr[channel] = conv(f[:, idx::32])

                basename = os.path.basename(frame.label)
                primary_headers = {'FILENAME': basename}
                hdu = pyfits.PrimaryHDU(rr, header=primary_headers)
                hdu.scale('int16', '', bzero=32768)
                hdu.writeto(basename, clobber=True)
                
                results.append(DataFrame(frame=hdu))
            finally:
                del f
        
        return {'products': results}
                                                 
