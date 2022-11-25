'''
    This file is part of PM4Py (More Info: https://pm4py.fit.fraunhofer.de).

    PM4Py is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    PM4Py is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with PM4Py.  If not, see <https://www.gnu.org/licenses/>.
'''
from abc import ABC
from collections import Counter
from itertools import product
from typing import List, Collection, Any, Optional, Generic, Dict

from pm4py.algo.discovery.inductive.cuts import utils as cut_util
from pm4py.algo.discovery.inductive.cuts.abc import Cut, T
from pm4py.algo.discovery.inductive.dtypes.im_dfg import InductiveDFG
from pm4py.algo.discovery.inductive.dtypes.im_ds import IMDataStructureUVCL, IMDataStructureDFG
from pm4py.objects.dfg import util as dfu
from pm4py.objects.dfg.obj import DFG
from pm4py.objects.process_tree.obj import Operator, ProcessTree
from pm4py.util.compression import util as comut
from pm4py.util.compression.dtypes import UVCL


class ConcurrencyCut(Cut[T], ABC, Generic[T]):

    @classmethod
    def operator(cls, parameters: Optional[Dict[str, Any]] = None) -> ProcessTree:
        return ProcessTree(operator=Operator.PARALLEL)

    @classmethod
    def holds(cls, obj: T, parameters: Optional[Dict[str, Any]] = None) -> Optional[List[Collection[Any]]]:
        dfg = obj.dfg
        alphabet = dfu.get_vertices(dfg)
        msdw = comut.msdw(obj, comut.msd(obj)) if obj is not None and type(obj) is UVCL else None
        groups = [{a} for a in alphabet]
        if len(groups) == 0:
            return None
        edges = dfu.get_edges(dfg)
        for a, b in product(alphabet, alphabet):
            if (a, b) not in edges or (b, a) not in edges:
                groups = cut_util.merge_groups_based_on_activities(a, b, groups)
            elif msdw is not None:
                if (a in msdw and b in msdw[a]) or (b in msdw and a in msdw[b]):
                    groups = cut_util.merge_groups_based_on_activities(a, b, groups)

        groups = list(sorted(groups, key=lambda g: len(g)))
        i = 0
        while i < len(groups) and len(groups) > 1:
            if len(groups[i].intersection(set(dfg.start_activities.keys()))) > 0 and len(
                    groups[i].intersection(set(dfg.end_activities.keys()))) > 0:
                i += 1
                continue
            group = groups[i]
            del groups[i]
            if i == 0:
                groups[i].update(group)
            else:
                groups[i - 1].update(group)

        return groups if len(groups) > 1 else None


class ConcurrencyCutUVCL(ConcurrencyCut[IMDataStructureUVCL]):

    @classmethod
    def project(cls, obj: IMDataStructureUVCL, groups: List[Collection[Any]], parameters: Optional[Dict[str, Any]] = None) -> List[IMDataStructureUVCL]:
        r = list()
        for g in groups:
            c = Counter()
            for t in obj.data_structure:
                c[tuple(filter(lambda e: e in g, t))] = obj.data_structure[t]
            r.append(c)
        return list(map(lambda l: IMDataStructureUVCL(l), r))


class ConcurrencyCutDFG(ConcurrencyCut[IMDataStructureDFG]):

    @classmethod
    def project(cls, obj: IMDataStructureDFG, groups: List[Collection[Any]], parameters: Optional[Dict[str, Any]] = None) -> List[IMDataStructureDFG]:
        dfgs = []
        skippable = []
        for g in groups:
            dfn = DFG()
            for a in obj.dfg.start_activities:
                if a in g:
                    dfn.start_activities[a] = obj.dfg.start_activities[a]
            for a in obj.dfg.end_activities:
                if a in g:
                    dfn.end_activities[a] = obj.dfg.end_activities[a]
            for (a, b) in obj.dfg.graph:
                if a in g and b in g:
                    dfn.graph[(a, b)] = obj.dfg.graph[(a, b)]
            skippable.append(False)
            dfgs.append(dfn)
        r = list()
        [r.append(IMDataStructureDFG(InductiveDFG(dfg=dfgs[i], skip=skippable[i]))) for i in range(len(dfgs))]
        return r