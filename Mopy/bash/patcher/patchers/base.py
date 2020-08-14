# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module contains base patcher classes."""
from __future__ import print_function
from collections import Counter
from itertools import chain
# Internal
from .. import getPatchesPath
from ..base import AMultiTweakItem, AMultiTweaker, Patcher, AListPatcher, \
    AImportPatcher
from ... import load_order, bush
from ...bolt import GPath, CsvReader, deprint
from ...brec import MreRecord

# Patchers 1 ------------------------------------------------------------------
class ListPatcher(AListPatcher,Patcher): pass

class MultiTweakItem(AMultiTweakItem):
    # Notice the differences from Patcher in scanModFile and buildPatch
    # TODO: scanModFile() have VERY similar code - use getReadClasses here ?

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return self.__class__.tweak_read_classes

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return self.__class__.tweak_read_classes

    def scanModFile(self,modFile,progress,patchFile): # extra param: patchFile
        """Scans specified mod file to extract info. May add record to patch
        mod, but won't alter it. If adds record, should first convert it to
        long fids."""
        pass

    def buildPatch(self,log,progress,patchFile): # extra param: patchFile
        """Edits patch file as desired. Should write to log."""
        pass ##: raise AbstractError ?

class MultiTweaker(AMultiTweaker,Patcher):

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return chain.from_iterable(tweak.getReadClasses()
            for tweak in self.enabled_tweaks) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return chain.from_iterable(tweak.getWriteClasses()
            for tweak in self.enabled_tweaks) if self.isActive else ()

    def scanModFile(self,modFile,progress):
        for tweak in self.enabled_tweaks:
            tweak.scanModFile(modFile,progress,self.patchFile)

    def buildPatch(self,log,progress):
        """Applies individual tweaks."""
        if not self.isActive: return
        log.setHeader(u'= ' + self._patcher_name, True)
        for tweak in self.enabled_tweaks:
            tweak.buildPatch(log,progress,self.patchFile)

# Patchers: 10 ----------------------------------------------------------------
class AliasesPatcher(Patcher):
    """Specify mod aliases for patch files."""
    scanOrder = 10
    editOrder = 10
    group = _(u'General')

class PatchMerger(ListPatcher):
    """Merges specified patches into Bashed Patch."""
    scanOrder = 10
    editOrder = 10
    group = _(u'General')

    def __init__(self, p_name, p_file, p_sources):
        super(PatchMerger, self).__init__(p_name, p_file, p_sources)
        if not self.isActive: return
        #--WARNING: Since other patchers may rely on the following update
        # during their __init__, it's important that PatchMerger runs first
        p_file.set_mergeable_mods(self.srcs)

class UpdateReferences(ListPatcher):
    # TODO move this to a file it's imported after MreRecord.simpleTypes is set
    """Imports Form Id replacers into the Bashed Patch."""
    scanOrder = 15
    editOrder = 15
    group = _(u'General')

    def __init__(self, p_name, p_file, p_sources):
        super(UpdateReferences, self).__init__(p_name, p_file,
                                               p_sources)
        self.old_new = {} #--Maps old fid to new fid
        self.old_eid = {} #--Maps old fid to old editor id
        self.new_eid = {} #--Maps new fid to new editor id

    def readFromText(self,textPath):
        """Reads replacement data from specified text file."""
        old_new,old_eid,new_eid = self.old_new,self.old_eid,self.new_eid
        aliases = self.patchFile.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 7 or fields[2][:2] != u'0x' or fields[6][:2] != u'0x': continue
                oldMod,oldObj,oldEid,newEid,newMod,newObj = fields[1:7]
                oldMod,newMod = map(GPath,(oldMod,newMod))
                oldId = (GPath(aliases.get(oldMod,oldMod)),int(oldObj,16))
                newId = (GPath(aliases.get(newMod,newMod)),int(newObj,16))
                old_new[oldId] = newId
                old_eid[oldId] = oldEid
                new_eid[newId] = newEid

    def initData(self,progress):
        """Get names from source files."""
        if not self.isActive: return
        progress.setFull(len(self.srcs))
        for srcFile in self.srcs:
            srcPath = GPath(srcFile)
            try: self.readFromText(getPatchesPath(srcFile))
            except OSError: deprint(
                u'%s is no longer in patches set' % srcPath, traceback=True)
            progress.plus()

    def getReadClasses(self):
        return tuple(
            MreRecord.simpleTypes | ({'CELL', 'WRLD', 'REFR', 'ACHR', 'ACRE'}))

    def getWriteClasses(self):
        return tuple(
            MreRecord.simpleTypes | ({'CELL', 'WRLD', 'REFR', 'ACHR', 'ACRE'}))

    def scanModFile(self,modFile,progress):
        """Scans specified mod file to extract info. May add record to patch mod,
        but won't alter it."""
        mapper = modFile.getLongMapper()
        patchCells = self.patchFile.CELL
        patchWorlds = self.patchFile.WRLD
        modFile.convertToLongFids(('CELL','WRLD','REFR','ACRE','ACHR'))
##        for type in MreRecord.simpleTypes:
##            for record in getattr(modFile,type).getActiveRecords():
##                record = record.getTypeCopy(mapper)
##                if record.fid in self.old_new:
##                    getattr(self.patchFile,type).setRecord(record)
        if 'CELL' in modFile.tops:
            for cellBlock in modFile.CELL.cellBlocks:
                cellImported = False
                if cellBlock.cell.fid in patchCells.id_cellBlock:
                    patchCells.id_cellBlock[cellBlock.cell.fid].cell = cellBlock.cell
                    cellImported = True
                for record in cellBlock.temp_refs:
                    if record.base in self.old_new:
                        if not cellImported:
                            patchCells.setCell(cellBlock.cell)
                            cellImported = True
                        for newRef in patchCells.id_cellBlock[cellBlock.cell.fid].temp_refs:
                            if newRef.fid == record.fid:
                                loc = patchCells.id_cellBlock[cellBlock.cell.fid].temp_refs.index(newRef)
                                patchCells.id_cellBlock[cellBlock.cell.fid].temp_refs[loc] = record
                                break
                        else:
                            patchCells.id_cellBlock[cellBlock.cell.fid].temp_refs.append(record)
                for record in cellBlock.persistent_refs:
                    if record.base in self.old_new:
                        if not cellImported:
                            patchCells.setCell(cellBlock.cell)
                            cellImported = True
                        for newRef in patchCells.id_cellBlock[cellBlock.cell.fid].persistent_refs:
                            if newRef.fid == record.fid:
                                loc = patchCells.id_cellBlock[cellBlock.cell.fid].persistent_refs.index(newRef)
                                patchCells.id_cellBlock[cellBlock.cell.fid].persistent_refs[loc] = record
                                break
                        else:
                            patchCells.id_cellBlock[cellBlock.cell.fid].persistent_refs.append(record)
        if 'WRLD' in modFile.tops:
            for worldBlock in modFile.WRLD.worldBlocks:
                worldImported = False
                if worldBlock.world.fid in patchWorlds.id_worldBlocks:
                    patchWorlds.id_worldBlocks[worldBlock.world.fid].world = worldBlock.world
                    worldImported = True
                for cellBlock in worldBlock.cellBlocks:
                    cellImported = False
                    if worldBlock.world.fid in patchWorlds.id_worldBlocks and cellBlock.cell.fid in patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock:
                        patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].cell = cellBlock.cell
                        cellImported = True
                    for record in cellBlock.temp_refs:
                        if record.base in self.old_new:
                            if not worldImported:
                                patchWorlds.setWorld(worldBlock.world)
                                worldImported = True
                            if not cellImported:
                                patchWorlds.id_worldBlocks[worldBlock.world.fid].setCell(cellBlock.cell)
                                cellImported = True
                            for newRef in patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].temp_refs:
                                if newRef.fid == record.fid:
                                    loc = patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].temp_refs.index(newRef)
                                    patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].temp_refs[loc] = record
                                    break
                            else:
                                patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].temp_refs.append(record)
                    for record in cellBlock.persistent_refs:
                        if record.base in self.old_new:
                            if not worldImported:
                                patchWorlds.setWorld(worldBlock.world)
                                worldImported = True
                            if not cellImported:
                                patchWorlds.id_worldBlocks[worldBlock.world.fid].setCell(cellBlock.cell)
                                cellImported = True
                            for newRef in patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].persistent_refs:
                                if newRef.fid == record.fid:
                                    loc = patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].persistent_refs.index(newRef)
                                    patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].persistent_refs[loc] = record
                                    break
                            else:
                                patchWorlds.id_worldBlocks[worldBlock.world.fid].id_cellBlock[cellBlock.cell.fid].persistent_refs.append(record)

    def buildPatch(self,log,progress):
        """Adds merged fids to patchfile."""
        if not self.isActive: return
        old_new,old_eid,new_eid = self.old_new,self.old_eid,self.new_eid
        keep = self.patchFile.getKeeper()
        count = Counter()
        def swapper(oldId):
            newId = old_new.get(oldId,None)
            return newId if newId else oldId
##        for type in MreRecord.simpleTypes:
##            for record in getattr(self.patchFile,type).getActiveRecords():
##                if record.fid in self.old_new:
##                    record.fid = swapper(record.fid)
##                    count.increment(record.fid[0])
####                    record.mapFids(swapper,True)
##                    record.setChanged()
##                    keep(record.fid)
        for cellBlock in self.patchFile.CELL.cellBlocks:
            for record in cellBlock.temp_refs:
                if record.base in self.old_new:
                    record.base = swapper(record.base)
                    count[cellBlock.cell.fid[0]] += 1
##                    record.mapFids(swapper,True)
                    record.setChanged()
                    keep(record.fid)
            for record in cellBlock.persistent_refs:
                if record.base in self.old_new:
                    record.base = swapper(record.base)
                    count[cellBlock.cell.fid[0]] += 1
##                    record.mapFids(swapper,True)
                    record.setChanged()
                    keep(record.fid)
        for worldBlock in self.patchFile.WRLD.worldBlocks:
            keepWorld = False
            for cellBlock in worldBlock.cellBlocks:
                for record in cellBlock.temp_refs:
                    if record.base in self.old_new:
                        record.base = swapper(record.base)
                        count[cellBlock.cell.fid[0]] += 1
##                        record.mapFids(swapper,True)
                        record.setChanged()
                        keep(record.fid)
                        keepWorld = True
                for record in cellBlock.persistent_refs:
                    if record.base in self.old_new:
                        record.base = swapper(record.base)
                        count[cellBlock.cell.fid[0]] += 1
##                        record.mapFids(swapper,True)
                        record.setChanged()
                        keep(record.fid)
                        keepWorld = True
            if keepWorld:
                keep(worldBlock.world.fid)

        log.setHeader(u'= ' + self._patcher_name)
        self._srcMods(log)
        log(u'\n=== '+_(u'Records Patched'))
        for srcMod in load_order.get_ordered(count.keys()):
            log(u'* %s: %d' % (srcMod.s,count[srcMod]))

# Patchers: 20 ----------------------------------------------------------------
class ImportPatcher(AImportPatcher, ListPatcher):
    # Override in subclasses as needed
    logMsg = u'\n=== ' + _(u'Modified Records')

    def _patchLog(self,log,type_count):
        log.setHeader(u'= ' + self._patcher_name)
        self._srcMods(log)
        self._plog(log,type_count)

    def _plog(self,log,type_count):
        """Most common logging pattern - override as needed.

        Used in:
        GraphicsPatcher, ActorImporter, KFFZPatcher, DeathItemPatcher,
        ImportFactions, ImportScripts, NamesPatcher, SoundPatcher.
        """
        log(self.__class__.logMsg)
        for type_,count in sorted(type_count.iteritems()):
            if count: log(u'* ' + _(u'Modified %(type)s Records: %(count)d')
                          % {'type': type_, 'count': count})

    def _plog1(self,log,mod_count): # common logging variation
        log(self.__class__.logMsg % sum(mod_count.values()))
        for mod in load_order.get_ordered(mod_count):
            log(u'* %s: %3d' % (mod.s,mod_count[mod]))

    def _plog2(self,log,allCounts):
        log(self.__class__.logMsg)
        for top_rec_type, count, counts in allCounts:
            if not count: continue
            typeName = bush.game.record_type_name[top_rec_type]
            log(u'* %s: %d' % (typeName, count))
            for modName in sorted(counts):
                log(u'  * %s: %d' % (modName.s, counts[modName]))
