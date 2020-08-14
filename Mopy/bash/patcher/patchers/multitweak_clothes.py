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
to the Clothes Multitweaker - as well as the ClothesTweaker itself."""
import itertools
from ...patcher.base import DynamicNamedTweak
from ...patcher.patchers.base import MultiTweakItem, MultiTweaker

# Patchers: 30 ----------------------------------------------------------------
class ClothesTweak(DynamicNamedTweak, MultiTweakItem):
    tweak_read_classes = 'CLOT',
    clothes_flags = {
        u'hoods':    0x00000002,
        u'shirts':   0x00000004,
        u'pants':    0x00000008,
        u'gloves':   0x00000010,
        u'amulets':  0x00000100,
        u'rings2':   0x00010000,
        u'amulets2': 0x00020000,
        #--Multi
        u'robes':    0x0000000C,
        u'rings':    0x000000C0,
        }
        # u'robes':   (1<<2) + (1<<3),
        # u'rings':   (1<<6) + (1<<7),

    def __init__(self, tweak_name, tweak_tip, key, *choices):
        super(ClothesTweak, self).__init__(tweak_name, tweak_tip, key,
                                            *choices)
        typeKey = key[:key.find(u'.')]
        self.orTypeFlags = typeKey == u'rings'
        self.typeFlags = self.__class__.clothes_flags[typeKey]

    def isMyType(self,record):
        """Returns true to save record for late processing."""
        if record.flags.notPlayable: return False #--Ignore non-playable items.
        recTypeFlags = int(record.flags) & 0xFFFF
        myTypeFlags = self.typeFlags
        return ((recTypeFlags == myTypeFlags) or (
            self.orTypeFlags and (recTypeFlags & myTypeFlags == recTypeFlags)))

#------------------------------------------------------------------------------
class ClothesTweak_MaxWeight(ClothesTweak):
    """Enforce a max weight for specified clothes."""

    def buildPatch(self,patchFile,keep,log):
        """Build patch."""
        tweakCount = 0
        maxWeight = self.choiceValues[self.chosen][0]
        superWeight = max(10,5*maxWeight) #--Guess is intentionally overweight
        for record in patchFile.CLOT.records:
            weight = record.weight
            if self.isMyType(record) and maxWeight < weight < superWeight:
                record.weight = maxWeight
                keep(record.fid)
                tweakCount += 1
        log(u'* %s: [%4.2f]: %d' % (self.tweak_name,maxWeight,tweakCount))

#------------------------------------------------------------------------------
class ClothesTweak_Unblock(ClothesTweak):
    """Unlimited rings, amulets."""

    def __init__(self, tweak_name, tweak_tip, key, *choices):
        super(ClothesTweak_Unblock, self).__init__(tweak_name, tweak_tip, key,
                                                   *choices)
        self.unblockFlags = self.__class__.clothes_flags[
            key[key.rfind('.') + 1:]]

    def buildPatch(self,patchFile,keep,log):
        """Build patch."""
        tweakCount = 0
        for record in patchFile.CLOT.records:
            if self.isMyType(record) and int(record.flags & self.unblockFlags):
                record.flags &= ~self.unblockFlags
                keep(record.fid)
                tweakCount += 1
        log(u'* %s: %d' % (self.tweak_name,tweakCount))

#------------------------------------------------------------------------------
class ClothesTweaker(MultiTweaker):
    """Patches clothes in miscellaneous ways."""
    _read_write_records = ('CLOT',)
    _unblock = ((_(u"Unlimited Amulets"),
                 _(u"Wear unlimited number of amulets - but they won't display."),
                 u'amulets.unblock.amulets',),
                (_(u"Unlimited Rings"),
                 _(u"Wear unlimited number of rings - but they won't display."),
                 u'rings.unblock.rings'),
                (_(u"Gloves Show Rings"),
                 _(u"Gloves will always show rings. (Conflicts with Unlimited "
                   u"Rings.)"),
                 u'gloves.unblock.rings2'),
                (_(u"Robes Show Pants"),
                _(u"Robes will allow pants, greaves, skirts - but they'll clip."),
                u'robes.unblock.pants'),
                (_(u"Robes Show Amulets"),
                _(u"Robes will always show amulets. (Conflicts with Unlimited "
                  u"Amulets.)"),
                u'robes.show.amulets2'),)
    _max_weight = ((_(u"Max Weight Amulets"),
                _(u"Amulet weight will be capped."),
                u'amulets.maxWeight',
                (u'0.0',0),
                (u'0.1',0.1),
                (u'0.2',0.2),
                (u'0.5',0.5),
                (_(u'Custom'),0),),
                (_(u"Max Weight Rings"),
                _(u'Ring weight will be capped.'),
                u'rings.maxWeight',
                (u'0.0',0.0),
                (u'0.1',0.1),
                (u'0.2',0.2),
                (u'0.5',0.5),
                (_(u'Custom'),0.0),),
                (_(u"Max Weight Hoods"),
                _(u'Hood weight will be capped.'),
                u'hoods.maxWeight',
                (u'0.2',0.2),
                (u'0.5',0.5),
                (u'1.0',1.0),
                (_(u'Custom'),0.0),),)
    scanOrder = 31
    editOrder = 31

    @classmethod
    def tweak_instances(cls):
        return sorted(itertools.chain(
            (ClothesTweak_Unblock(*x) for x in cls._unblock),
            (ClothesTweak_MaxWeight(*x) for x in cls._max_weight)),
                      key=lambda a: a.tweak_name.lower())

    def scanModFile(self,modFile,progress):
        if not self.isActive or 'CLOT' not in modFile.tops: return
        mapper = modFile.getLongMapper()
        patchRecords = self.patchFile.CLOT
        id_records = patchRecords.id_records
        for record in modFile.CLOT.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            for tweak in self.enabled_tweaks:
                if tweak.isMyType(record):
                    record = record.getTypeCopy(mapper)
                    patchRecords.setRecord(record)
                    break

    def buildPatch(self,log,progress):
        """Applies individual clothes tweaks."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        log.setHeader(u'= ' + self._patcher_name)
        for tweak in self.enabled_tweaks:
            tweak.buildPatch(self.patchFile,keep,log)
