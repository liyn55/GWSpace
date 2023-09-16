#!/usr/bin/env python
#-*- coding: utf-8 -*-  
#==================================
# File Name: ORF.py
# Author: ekli
# Mail: lekf123@163.com
# Created Time: 2023-09-15 14:52:04
#==================================

import numpy as np
from utils import get_uvk


def polarization_tensor(u, v):
    e_p = np.zeros((3,3))
    e_c = np.zeros((3,3))

    for i in range(3):
        for j in range(3):
            e_p[i,j] = u[i] * u[j] - v[i] * v[j]
            e_c[i,j] = u[i] * v[j] + v[i] * u[j]

    return (e_p, e_c)

def transfer_single_arm(f, kn, kpr, kps, LT):
    return (0.5 * np.sinc(np.pi * f *LT*(1-kn)) * 
            np.exp(-1j * np.pi * f* (LT + kpr + kps)) )

class OverlapReductionFunc(object):
    '''
    Calculate ORF
    '''

