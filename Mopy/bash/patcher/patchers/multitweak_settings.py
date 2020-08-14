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
"""This module contains oblivion multitweak item patcher classes that belong
to the Gmst Multitweaker - as well as the GmstTweaker itself. Gmst stands
for game settings."""
from __future__ import print_function
from ... import bush # for game
from ...bolt import deprint
from ...brec import MreRecord, RecHeader
from ...patcher.base import DynamicNamedTweak
from ...patcher.patchers.base import MultiTweakItem
from ...patcher.patchers.base import MultiTweaker

# Patchers: 30 ----------------------------------------------------------------
class GlobalsTweak(DynamicNamedTweak, MultiTweakItem):
    """set a global to specified value"""
    tweak_read_classes = 'GLOB',

    def buildPatch(self,patchFile,keep,log):
        """Build patch."""
        value = self.choiceValues[self.chosen][0]
        for record in patchFile.GLOB.records:
            if hasattr(record,'eid'):
                if record.eid.lower() == self.key:
                    if record.value != value:
                        record.value = value
                        keep(record.fid)
                    break
        log(u'* ' + _(u'%(label)s set to') % {
            'label': (u'%s ' % self.tweak_name)} + (u': %4.2f' % value))

#------------------------------------------------------------------------------
class GmstTweak(DynamicNamedTweak, MultiTweakItem):
    tweak_read_classes = 'GMST',

    def buildPatch(self,patchFile,keep,log):
        """Build patch."""
        eids = ((self.key,),self.key)[isinstance(self.key,tuple)]
        isOblivion = bush.game.fsName.lower() == u'oblivion'
        for eid,value in zip(eids,self.choiceValues[self.chosen]):
            if isOblivion and value < 0:
                deprint(u"GMST values can't be negative - currently %s - "
                        u'skipping setting GMST.' % value)
                return
            eidLower = eid.lower()
            for record in patchFile.GMST.records:
                if record.eid.lower() == eidLower:
                    if record.value != value:
                        record.value = value
                        keep(record.fid)
                    break
            else:
                gmst = MreRecord.type_class['GMST'](RecHeader('GMST'))
                gmst.eid,gmst.value,gmst.longFids = eid,value,True
                gmst_fid = gmst.getGMSTFid()
                gmst.fid = gmst_fid
                keep(gmst_fid)
                patchFile.GMST.setRecord(gmst)
        if len(self.choiceLabels) > 1:
            if self.choiceLabels[self.chosen].startswith(_(u'Custom')):
                if isinstance(self.choiceValues[self.chosen][0],basestring):
                    log(u'* %s: %s %s' % (
                        self.tweak_name, self.choiceLabels[self.chosen],
                        self.choiceValues[self.chosen][0]))
                else:
                    log(u'* %s: %s %4.2f' % (
                        self.tweak_name, self.choiceLabels[self.chosen],
                        self.choiceValues[self.chosen][0]))
            else:
                log(u'* %s: %s' % (
                    self.tweak_name, self.choiceLabels[self.chosen]))
        else:
            log(u'* ' + self.tweak_name)

#------------------------------------------------------------------------------
class GmstTweaker(MultiTweaker):
    """Tweaks miscellaneous gmsts in miscellaneous ways."""
    scanOrder = 29
    editOrder = 29
    _class_tweaks = [(GlobalsTweak, bush.game.GlobalsTweaks),
                    (GmstTweak, bush.game.GmstTweaks)]
    _read_write_records = ('GMST', 'GLOB')

    @classmethod
    def tweak_instances(cls):
        instances = []
        for clazz, game_tweaks in cls._class_tweaks:
            for tweak in game_tweaks:
                if isinstance(tweak, tuple):
                    instances.append(clazz(*tweak))
                elif isinstance(tweak, list):
                    args = tweak[0]
                    kwdargs = tweak[1]
                    instances.append(clazz(*args, **kwdargs))
        instances.sort(key=lambda a: a.tweak_name.lower())
        return instances

    def scanModFile(self,modFile,progress):
        mapper = modFile.getLongMapper()
        for blockType in self._read_write_records:
            if blockType not in modFile.tops: continue
            modBlock = getattr(modFile,blockType)
            patchBlock = getattr(self.patchFile,blockType)
            id_records = patchBlock.id_records
            for record in modBlock.getActiveRecords():
                if mapper(record.fid) not in id_records:
                    record = record.getTypeCopy(mapper)
                    patchBlock.setRecord(record)

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        log.setHeader(u'= '+self._patcher_name)
        for tweak in self.enabled_tweaks:
            tweak.buildPatch(self.patchFile,keep,log)
