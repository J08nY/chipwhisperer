#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2013, Colin O'Flynn <coflynn@newae.com>
# All rights reserved.
#
# Find this and more at newae.com - this file is part of the chipwhisperer
# project, http://www.assembla.com/spaces/chipwhisperer
#
#    This file is part of chipwhisperer.
#
#    chipwhisperer is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    chipwhisperer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with chipwhisperer.  If not, see <http://www.gnu.org/licenses/>.
#=================================================

import sys

try:
    from PySide.QtCore import *
    from PySide.QtGui import *
except ImportError:
    print "ERROR: PySide is required for this program"
    sys.exit()
    
sys.path.append('../common')
sys.path.append('../../openadc/controlsw/python/common')
imagePath = '../common/images/'

import numpy as np
from ExtendedParameter import ExtendedParameter

try:
    import pyqtgraph as pg
    import pyqtgraph.multiprocess as mp
    import pyqtgraph.parametertree.parameterTypes as pTypes
    from pyqtgraph.parametertree import Parameter, ParameterTree, ParameterItem, registerParameterType
    #print pg.systemInfo()    
except ImportError:
    print "ERROR: PyQtGraph is required for this program"
    sys.exit()


from functools import partial
import scipy as sp
import numpy as np
        
class ResyncSAD(QObject):
    """
    Resync by minimizing the SAD.
    """
    paramListUpdated = Signal(list)
     
    def __init__(self, parent):
        super(ResyncSAD, self).__init__()
                
        self.enabled = True
        self.rtrace = 0
        self.debugReturnSad = False
        resultsParams = [{'name':'Enabled', 'type':'bool', 'value':True, 'set':self.setEnabled},
                         {'name':'Ref Trace', 'type':'int', 'value':0, 'set':self.setRefTrace},
                         {'name':'Ref Point Start', 'type':'int', 'set':self.setRefPointStart},
                         {'name':'Ref Point End', 'type':'int', 'set':self.setRefPointEnd},  
                         {'name':'Input Window Start', 'type':'int', 'set':self.setWindowStart},
                         {'name':'Input Window End', 'type':'int', 'set':self.setWindowEnd},          
                         {'name':'Output SAD (DEBUG)', 'type':'bool', 'value':False, 'set':self.setOutputSad}         
                      ]
        
        self.params = Parameter.create(name='Minimize Sum of Absolute Difference', type='group', children=resultsParams)
        ExtendedParameter.setupExtended(self.params)
        self.parent = parent
        self.setTraceManager(parent.manageTraces.iface)
        self.ccStart = 0
        self.ccEnd = 1
        self.wdStart = 0
        self.wdEnd = 1
        
    def paramList(self):
        return [self.params]
    
    def setWindowStart(self, start):
        self.wdStart = start
        
    def setWindowEnd(self, end):
        self.wdEnd = end
    
    def setRefPointStart(self, start):
        self.ccStart = start
        
    def setRefPointEnd(self, end):
        self.ccEnd = end
    
    def setEnabled(self, enabled):
        self.enabled = enabled
   
    def setOutputSad(self, enabled):
        self.debugReturnSad = enabled
   
    def getTrace(self, n):
        if self.enabled:
            trace = self.trace.getTrace(n)
            if trace is None:
                return None
            sad = self.findSAD(trace)
            if self.debugReturnSad:
                return sad
            newmaxloc = np.argmin(sad)
            maxval = min(sad)
            #if (maxval > self.refmaxsize * 1.01) | (maxval < self.refmaxsize * 0.99):
            #    return None
            
            if maxval > self.maxthreshold:
                return None
            
            diff = newmaxloc-self.refmaxloc
            if diff < 0:
                trace = np.append(np.zeros(-diff), trace[:diff])
            elif diff > 0:
                trace = np.append(trace[diff:], np.zeros(diff))
            return trace
            
        else:
            return self.trace.getTrace(n)       
    
    def getTextin(self, n):
        return self.trace.getTextin(n)

    def getTextout(self, n):
        return self.trace.getTextout(n)
    
    def getKnownKey(self, n=None):
        return self.trace.getKnownKey()
   
    def init(self):
        self.calcRefTrace(self.rtrace)
   
    def setTraceManager(self, tmanager):
        self.trace = tmanager    
    
    def setRefTrace(self, tnum):
        self.rtrace = tnum
        
    def findSAD(self, inputtrace):
        reflen = self.ccEnd-self.ccStart
        sadlen = self.wdEnd-self.wdStart
        
        sadarray = np.empty(sadlen)
        
        for ptstart in range(self.wdStart, self.wdEnd):    
            #Find SAD        
            sadarray[ptstart-self.wdStart] = np.sum(np.abs(inputtrace[ptstart:(ptstart+reflen)] - self.reftrace))
            
        return sadarray
        
    def calcRefTrace(self, tnum):
        
        #If not enabled stop
        if self.enabled == False:
            return
        
        self.reftrace = self.trace.getTrace(tnum)[self.ccStart:self.ccEnd]
        sad = self.findSAD(self.trace.getTrace(tnum))
        self.refmaxloc = np.argmin(sad)
        self.refmaxsize = min(sad)
        self.maxthreshold = np.mean(sad)