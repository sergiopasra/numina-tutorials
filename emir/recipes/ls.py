#
# Copyright 2011-2012 Universidad Complutense de Madrid
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

'''Longslit Recipes for EMIR'''

import logging
import time

import numpy
import pyfits

from numina import RecipeBase

__all__ = ['Recipe']

_logger = logging.getLogger('emir.recipes')

class Recipe(RecipeBase):
    '''Null recipe'''

    __requires__ = []
    __provides__ = []

    def __init__(self):
        super(Recipe, self).__init__(
                        author="Universidad Complutense de Madrid <sergiopr@fis.ucm.es>",
                        version="0.1.0"
                )

    def run(self, block):

            return {'products': {} }

