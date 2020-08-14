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
to the Assorted Multitweaker - as well as the AssortedTweaker itself."""
from __future__ import division
import random
import re
from collections import Counter
# Internal
from ... import bush, load_order
from ...bolt import GPath
from ...brec import MreRecord
from ...patcher.base import DynamicNamedTweak
from ...patcher.patchers.base import MultiTweakItem, MultiTweaker

# Patchers: 30 ----------------------------------------------------------------
class AssortedTweak_ArmorShows(DynamicNamedTweak, MultiTweakItem):
    """Fix armor to show amulets/rings."""
    tweak_read_classes = 'ARMO',

    def __init__(self, tweak_name, tweak_tip, key):
        super(AssortedTweak_ArmorShows, self).__init__(tweak_name, tweak_tip,
                                                       key)
        self.hidesBit = {u'armorShowsRings':16,u'armorShowsAmulets':17}[key]
        self.logMsg = u'* '+_(u'Armor Pieces Tweaked') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.ARMO
        hidesBit = self.hidesBit
        for record in modFile.ARMO.getActiveRecords():
            if record.flags[hidesBit] and not record.flags.notPlayable:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        hidesBit = self.hidesBit
        for record in patchFile.ARMO.records:
            if record.flags[hidesBit] and not record.flags.notPlayable:
                record.flags[hidesBit] = False
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

#------------------------------------------------------------------------------
class AssortedTweak_ClothingShows(DynamicNamedTweak, MultiTweakItem):
    """Fix robes, gloves and the like to show amulets/rings."""
    tweak_read_classes = 'CLOT',

    def __init__(self, tweak_name, tweak_tip, key):
        super(AssortedTweak_ClothingShows, self).__init__(tweak_name,
                                                          tweak_tip, key)
        self.hidesBit = \
            {u'ClothingShowsRings': 16, u'ClothingShowsAmulets': 17}[key]
        self.logMsg = u'* '+_(u'Clothing Pieces Tweaked') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.CLOT
        hidesBit = self.hidesBit
        for record in modFile.CLOT.getActiveRecords():
            if record.flags[hidesBit] and not record.flags.notPlayable:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        hidesBit = self.hidesBit
        for record in patchFile.CLOT.records:
            if record.flags[hidesBit] and not record.flags.notPlayable:
                record.flags[hidesBit] = False
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

#------------------------------------------------------------------------------
class AssortedTweak_BowReach(MultiTweakItem):
    """Fix bows to have reach = 1.0."""
    tweak_read_classes = 'WEAP',
    tweak_name = _(u'Bow Reach Fix')
    tweak_tip = _(u'Fix bows with zero reach. (Zero reach causes CTDs.)')

    def __init__(self):
        super(AssortedTweak_BowReach, self).__init__(u'BowReach',
            (u'1.0', u'1.0'))
        self.defaultEnabled = True
        self.logMsg = u'* '+_(u'Bows fixed') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.WEAP
        for record in modFile.WEAP.getActiveRecords():
            if record.weaponType == 5 and record.reach <= 0:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.WEAP.records:
            if record.weaponType == 5 and record.reach <= 0:
                record.reach = 1
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

#------------------------------------------------------------------------------
class AssortedTweak_SkyrimStyleWeapons(MultiTweakItem):
    """Sets all one handed weapons as blades, two handed weapons as blunt."""
    tweak_read_classes = 'WEAP',
    tweak_name = _(u'Skyrim-style Weapons')
    tweak_tip = _(u'Sets all one handed weapons as blades, two handed weapons '
                  u'as blunt.')

    def __init__(self):
        super(AssortedTweak_SkyrimStyleWeapons, self).__init__(
            u'skyrimweaponsstyle', (u'1.0', u'1.0'))
        self.logMsg = u'* '+_(u'Weapons Adjusted') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.WEAP
        for record in modFile.WEAP.getActiveRecords():
            if record.weaponType in [1,2]:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.WEAP.records:
            if record.weaponType == 1:
                record.weaponType = 3
                keep(record.fid)
                count[record.fid[0]] += 1
            elif record.weaponType == 2:
                record.weaponType = 0
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

#------------------------------------------------------------------------------
class AssortedTweak_ConsistentRings(MultiTweakItem):
    """Sets rings to all work on same finger."""
    tweak_read_classes = 'CLOT',
    tweak_name = _(u'Right Hand Rings')
    tweak_tip = _(u'Fixes rings to unequip consistently by making them '
                  u'prefer the right hand.')

    def __init__(self):
        super(AssortedTweak_ConsistentRings, self).__init__(
            u'ConsistentRings', (u'1.0', u'1.0'))
        self.defaultEnabled = True
        self.logMsg = u'* '+_(u'Rings fixed') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.CLOT
        for record in modFile.CLOT.getActiveRecords():
            if record.flags.leftRing:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.CLOT.records:
            if record.flags.leftRing:
                record.flags.leftRing = False
                record.flags.rightRing = True
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

#------------------------------------------------------------------------------
rePlayableSkips = re.compile(
    u'(?:skin)|(?:test)|(?:mark)|(?:token)|(?:willful)|(?:see.*me)|('
    u'?:werewolf)|(?:no wings)|(?:tsaesci tail)|(?:widget)|(?:dummy)|('
    u'?:ghostly immobility)|(?:corpse)', re.I)

class AssortedTweak_ClothingPlayable(MultiTweakItem):
    """Sets all clothes to playable"""
    tweak_read_classes = 'CLOT',
    tweak_name = _(u'All Clothing Playable')
    tweak_tip = _(u'Sets all clothing to be playable.')

    def __init__(self):
        super(AssortedTweak_ClothingPlayable, self).__init__(
            u'PlayableClothing', (u'1.0', u'1.0'))
        self.logHeader = u'=== '+_(u'Playable Clothes')
        self.logMsg = u'* '+_(u'Clothes set as playable') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.CLOT
        for record in modFile.CLOT.getActiveRecords():
            if record.flags.notPlayable:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.CLOT.records:
            if record.flags.notPlayable:
                full = record.full
                if not full: continue
                if record.script: continue
                if rePlayableSkips.search(full): continue  # probably truly
                # shouldn't be playable
                # If only the right ring and no other body flags probably a
                # token that wasn't zeroed (which there are a lot of).
                if record.flags.leftRing != 0 or record.flags.foot != 0 or \
                                record.flags.hand != 0 or \
                                record.flags.amulet != 0 or \
                                record.flags.lowerBody != 0 or \
                                record.flags.upperBody != 0 or \
                                record.flags.head != 0 or record.flags.hair \
                        != 0 or record.flags.tail != 0:
                    record.flags.notPlayable = 0
                    keep(record.fid)
                    count[record.fid[0]] += 1
        self._patchLog(log,count)


class AssortedTweak_ArmorPlayable(MultiTweakItem):
    """Sets all armors to be playable"""
    tweak_read_classes = 'ARMO',
    tweak_name = _(u'All Armor Playable')
    tweak_tip = _(u'Sets all armor to be playable.')

    def __init__(self):
        super(AssortedTweak_ArmorPlayable, self).__init__(u'PlayableArmor',
            (u'1.0', u'1.0'))
        self.logHeader = u'=== '+_(u'Playable Armor')
        self.logMsg = u'* '+_(u'Armor pieces set as playable') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.ARMO
        for record in modFile.ARMO.getActiveRecords():
            if record.flags.notPlayable:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.ARMO.records:
            if record.flags.notPlayable:
                full = record.full
                if not full: continue
                if record.script: continue
                if rePlayableSkips.search(full): continue  # probably truly
                # shouldn't be playable
                # We only want to set playable if the record has at least
                # one body flag... otherwise most likely a token.
                if record.flags.leftRing != 0 or record.flags.rightRing != 0\
                        or record.flags.foot != 0 or record.flags.hand != 0 \
                        or record.flags.amulet != 0 or \
                                record.flags.lowerBody != 0 or \
                                record.flags.upperBody != 0 or \
                                record.flags.head != 0 or record.flags.hair \
                        != 0 or record.flags.tail != 0 or \
                                record.flags.shield != 0:
                    record.flags.notPlayable = 0
                    keep(record.fid)
                    count[record.fid[0]] += 1
        self._patchLog(log,count)

#------------------------------------------------------------------------------
class AssortedTweak_DarnBooks(MultiTweakItem):
    """DarNifies books."""
    reColor = re.compile(u'<font color="?([a-fA-F0-9]+)"?>', re.I + re.M)
    reTagInWord = re.compile(u'([a-z])<font face=1>', re.M)
    reFont1 = re.compile(u'(<?<font face=1( ?color=[0-9a-zA]+)?>)+', re.I|re.M)
    reDiv = re.compile(u'<div', re.I + re.M)
    reFont = re.compile(u'<font', re.I + re.M)
    reHead2 = re.compile(u'' r'^(<<|\^\^|>>|)==\s*(\w[^=]+?)==\s*\r\n', re.M)
    reHead3 = re.compile(u'' r'^(<<|\^\^|>>|)===\s*(\w[^=]+?)\r\n', re.M)
    reBold = re.compile(u'' r'(__|\*\*|~~)')
    reAlign = re.compile(u'' r'^(<<|\^\^|>>)', re.M)
    tweak_read_classes = 'BOOK',
    tweak_name = _(u'DarNified Books')
    tweak_tip = _(u'Books will be reformatted for DarN UI.')

    def __init__(self):
        super(AssortedTweak_DarnBooks, self).__init__(u'DarnBooks',
            (u'default', u'default'))
        self.logMsg = u'* '+_(u'Books DarNified') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        # maxWeight = self.choiceValues[self.chosen][0] # TODO: is this
        # supposed to be used ?
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.BOOK
        id_records = patchBlock.id_records
        for record in modFile.BOOK.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if not record.enchantment:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        reColor = self.__class__.reColor
        reTagInWord = self.__class__.reTagInWord
        reFont1 = self.__class__.reFont1
        reDiv = self.__class__.reDiv
        reFont = self.__class__.reFont
        reHead2 = self.__class__.reHead2
        reHead3 = self.__class__.reHead3
        reBold = self.__class__.reBold
        reAlign = self.__class__.reAlign
        keep = patchFile.getKeeper()
        align_text = {u'^^':u'center',u'<<':u'left',u'>>':u'right'}
        self.inBold = False
        def replaceBold(mo):
            self.inBold = not self.inBold
            return u'<font face=3 color=%s>' % (
                u'440000' if self.inBold else u'444444')
        def replaceAlign(mo):
            return u'<div align=%s>' % align_text[mo.group(1)]
        for record in patchFile.BOOK.records:
            if record.text and not record.enchantment:
                rec_text = record.text
                rec_text = rec_text.replace(u'\u201d', u'')  # there are some FUNKY
                # quotes that don't translate properly. (they are in *latin*
                # encoding not even cp1252 or something normal but non-unicode)
                if reHead2.match(rec_text):
                    self.inBold = False
                    rec_text = reHead2.sub(
                        u'' r'\1<font face=1 color=220000>\2<font face=3 '
                        u'' r'color=444444>\r\n', rec_text)
                    rec_text = reHead3.sub(
                        u'' r'\1<font face=3 color=220000>\2<font face=3 '
                        u'' r'color=444444>\r\n',
                        rec_text)
                    rec_text = reAlign.sub(replaceAlign,rec_text)
                    rec_text = reBold.sub(replaceBold,rec_text)
                    rec_text = re.sub(u'' r'\r\n', u'' r'<br>\r\n', rec_text)
                else:
                    maColor = reColor.search(rec_text)
                    if maColor:
                        color = maColor.group(1)
                    elif record.flags.isScroll:
                        color = u'000000'
                    else:
                        color = u'444444'
                    fontFace = u'<font face=3 color='+color+u'>'
                    rec_text = reTagInWord.sub(u'' r'\1', rec_text)
                    if reDiv.search(rec_text) and not reFont.search(rec_text):
                        rec_text = fontFace+rec_text
                    else:
                        rec_text = reFont1.sub(fontFace,rec_text)
                if rec_text != record.text:
                    record.text = rec_text
                    keep(record.fid)
                    count[record.fid[0]] += 1
        self._patchLog(log,count)

#------------------------------------------------------------------------------
class AssortedTweak_FogFix(MultiTweakItem):
    """Fix fog in cell to be non-zero."""
    tweak_name = _(u'Nvidia Fog Fix')
    tweak_tip = _(u'Fix fog related Nvidia black screen problems.')
    tweak_read_classes = 'CELL', 'WRLD',

    def __init__(self):
        super(AssortedTweak_FogFix, self).__init__(u'FogFix',
            (u'0.0001', u'0.0001'))
        self.logMsg = u'* '+_(u'Cells with fog tweaked to 0.0001') + u': %d'
        self.defaultEnabled = True

    def scanModFile(self, modFile, progress,patchFile):
        """Add lists from modFile."""
        if 'CELL' not in modFile.tops: return
        patchCells = patchFile.CELL
        modFile.convertToLongFids(('CELL',))
        for cellBlock in modFile.CELL.cellBlocks:
            cell = cellBlock.cell
            if not (cell.fogNear or cell.fogFar or cell.fogClip):
                patchCells.setCell(cell)

    def buildPatch(self,log,progress,patchFile):
        """Adds merged lists to patchfile."""
        keep = patchFile.getKeeper()
        count = Counter()
        for cellBlock in patchFile.CELL.cellBlocks:
            cell = cellBlock.cell
            if not (cell.fogNear or cell.fogFar or cell.fogClip):
                cell.fogNear = 0.0001
                keep(cell.fid)
                count[cell.fid[0]] += 1
        self._patchLog(log, count)

#------------------------------------------------------------------------------
class AssortedTweak_NoLightFlicker(MultiTweakItem):
    """Remove light flickering for low end machines."""
    tweak_read_classes = 'LIGH',
    tweak_name = _(u'No Light Flicker')
    tweak_tip = _(u'Remove flickering from lights. For use on low-end '
                  u'machines.')

    def __init__(self):
        super(AssortedTweak_NoLightFlicker, self).__init__(u'NoLightFlicker',
            (u'1.0', u'1.0'))
        self.logMsg = u'* '+_(u'Lights unflickered') + u': %d'
        self.flags = flags = MreRecord.type_class['LIGH']._flags()
        flags.flickers = flags.flickerSlow = flags.pulse = flags.pulseSlow =\
            True

    def scanModFile(self,modFile,progress,patchFile):
        flickerFlags = self.flags
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.LIGH
        for record in modFile.LIGH.getActiveRecords():
            if record.flags & flickerFlags:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        flickerFlags = self.flags
        notFlickerFlags = ~flickerFlags
        keep = patchFile.getKeeper()
        for record in patchFile.LIGH.records:
            if int(record.flags & flickerFlags):
                record.flags &= notFlickerFlags
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

#------------------------------------------------------------------------------
class MultiTweakItem_Weight(MultiTweakItem):

    @property
    def weight(self): return self.choiceValues[self.chosen][0]

    def _patchLog(self, log, count):
        """Will write to log for a class that has a weight field"""
        log.setHeader(self.logHeader)
        log(self.logWeightValue % self.weight)
        log(self.logMsg % sum(count.values()))
        for srcMod in load_order.get_ordered(count.keys()):
            log(u'  * %s: %d' % (srcMod.s,count[srcMod]))

class AssortedTweak_PotionWeight(MultiTweakItem_Weight):
    """Reweighs standard potions down to 0.1."""
    tweak_read_classes = 'ALCH',
    tweak_name = _(u'Reweigh: Potions (Maximum)')
    tweak_tip = _(u'Potion weight will be capped.')

    def __init__(self):
        super(AssortedTweak_PotionWeight, self).__init__(
            u'MaximumPotionWeight', (u'0.1', 0.1), (u'0.2', 0.2),
            (u'0.4', 0.4), (u'0.6', 0.6), (_(u'Custom'), 0.0))
        self.logWeightValue = _(u'Potions set to maximum weight of ') + u'%f'
        self.logMsg = u'* '+_(u'Potions Reweighed') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        maxWeight = self.weight
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.ALCH
        id_records = patchBlock.id_records
        for record in modFile.ALCH.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if maxWeight < record.weight < 1:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        maxWeight = self.weight
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.ALCH.records:
            ##: Skips OBME records - rework to support them
            if (maxWeight < record.weight < 1 and
                record.obme_record_version is None and
                    ('SEFF', 0) not in record.getEffects()):
                record.weight = maxWeight
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log, count)

#------------------------------------------------------------------------------
class AssortedTweak_IngredientWeight(MultiTweakItem_Weight):
    """Reweighs standard ingredients down to 0.1."""
    tweak_read_classes = 'INGR',
    tweak_name = _(u'Reweigh: Ingredients')
    tweak_tip = _(u'Ingredient weight will be capped.')

    def __init__(self):
        super(AssortedTweak_IngredientWeight, self).__init__(
            u'MaximumIngredientWeight', (u'0.1', 0.1), (u'0.2', 0.2),
            (u'0.4', 0.4), (u'0.6', 0.6), (_(u'Custom'), 0.0))
        self.logWeightValue = _(u'Ingredients set to maximum weight of') + \
                              u' %f'
        self.logMsg = u'* '+_(u'Ingredients Reweighed') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        maxWeight = self.weight
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.INGR
        id_records = patchBlock.id_records
        for record in modFile.INGR.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.weight > maxWeight:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        maxWeight = self.weight
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.INGR.records:
            if record.weight > maxWeight:
                record.weight = maxWeight
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log, count)

#------------------------------------------------------------------------------
class AssortedTweak_PotionWeightMinimum(MultiTweakItem_Weight):
    """Reweighs any potions up to 4."""
    tweak_read_classes = 'ALCH',
    tweak_name = _(u'Reweigh: Potions (Minimum)')
    tweak_tip = _(u'Potion weight will be floored.')

    def __init__(self):
        super(AssortedTweak_PotionWeightMinimum, self).__init__(
            u'MinimumPotionWeight', (u'1', 1), (u'2', 2), (u'3', 3), (u'4', 4),
            (_(u'Custom'), 0.0))
        self.logWeightValue = _(u'Potions set to minimum weight of ') + u'%f'
        self.logMsg = u'* '+_(u'Potions Reweighed') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        minWeight = self.weight
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.ALCH
        id_records = patchBlock.id_records
        for record in modFile.ALCH.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.weight < minWeight:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        minWeight = self.weight
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.ALCH.records:
            if record.weight < minWeight:
                record.weight = minWeight
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log, count)

#------------------------------------------------------------------------------
class AssortedTweak_StaffWeight(MultiTweakItem_Weight):
    """Reweighs staffs."""
    tweak_read_classes = 'WEAP',
    tweak_name = _(u'Reweigh: Staffs/Staves')
    tweak_tip =  _(u'Staff weight will be capped.')

    def __init__(self):
        super(AssortedTweak_StaffWeight, self).__init__(u'StaffWeight',
            (u'1', 1.0), (u'2', 2.0), (u'3', 3.0), (u'4', 4.0), (u'5', 5.0),
            (u'6', 6.0), (u'7', 7.0), (u'8', 8.0), (_(u'Custom'), 0.0))
        self.logWeightValue = _(u'Staffs/Staves set to maximum weight of') + \
                              u' %f'
        self.logMsg = u'* '+_(u'Staffs/Staves Reweighed') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        maxWeight = self.weight
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.WEAP
        id_records = patchBlock.id_records
        for record in modFile.WEAP.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.weaponType == 4 and record.weight > maxWeight:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        maxWeight = self.weight
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.WEAP.records:
            if record.weaponType == 4 and record.weight > maxWeight:
                record.weight = maxWeight
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log, count)

#------------------------------------------------------------------------------
class AssortedTweak_ArrowWeight(MultiTweakItem_Weight):
    tweak_read_classes = 'AMMO',
    tweak_name = _(u'Reweigh: Arrows')
    tweak_tip = _(u'Arrow weights will be capped.')

    def __init__(self):
        super(AssortedTweak_ArrowWeight, self).__init__(u'MaximumArrowWeight',
            (u'0', 0.0), (u'0.1', 0.1), (u'0.2', 0.2), (u'0.4', 0.4),
            (u'0.6', 0.6), (_(u'Custom'), 0.0))
        self.logWeightValue = _(u'Arrows set to maximum weight of ') + u'%f'
        self.logMsg = u'* '+_(u'Arrows Reweighed') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        maxWeight = self.weight
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.AMMO
        id_records = patchBlock.id_records
        for record in modFile.AMMO.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.weight > maxWeight:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        maxWeight = self.weight
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.AMMO.records:
            if record.weight > maxWeight:
                record.weight = maxWeight
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log, count)

#------------------------------------------------------------------------------
class AssortedTweak_ScriptEffectSilencer(MultiTweakItem):
    """Silences the script magic effect and gives it an extremely high
    speed."""
    tweak_read_classes = 'MGEF',
    tweak_name = _(u'Magic: Script Effect Silencer')
    tweak_tip = _(u'Script Effect will be silenced and have no graphics.')

    def __init__(self):
        super(AssortedTweak_ScriptEffectSilencer, self).__init__(
            u'SilentScriptEffect', (u'0', 0))
        self.defaultEnabled = True

    def _patchLog(self,log):
        log.setHeader(self.logHeader)
        log(_(u'Script Effect silenced.'))

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.MGEF
        id_records = patchBlock.id_records
        modFile.convertToLongFids(('MGEF',))
        for record in modFile.MGEF.getActiveRecords():
            fid = record.fid
            if not record.longFids: fid = mapper(fid)
            if fid in id_records: continue
            if record.eid != 'SEFF': continue
            patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        nullRef = (GPath(bush.game.master_file), 0)
        silentattrs = {
            'model': None,
            'projectileSpeed' : 9999,
            'light' : nullRef,
            'effectShader' : nullRef,
            'enchantEffect' : nullRef,
            'castingSound' : nullRef,
            'boltSound' : nullRef,
            'hitSound' : nullRef,
            'areaSound' : nullRef}
        keep = patchFile.getKeeper()
        for record in patchFile.MGEF.records:
            if record.eid != 'SEFF' or not record.longFids: continue
            record.flags.noHitEffect = True
            for attr in silentattrs:
                if getattr(record,attr) != silentattrs[attr]:
                    setattr(record,attr,silentattrs[attr])
                    keep(record.fid)
        self._patchLog(log)

#------------------------------------------------------------------------------
class AssortedTweak_HarvestChance(MultiTweakItem):
    """Adjust Harvest Chances."""
    tweak_read_classes = 'FLOR',
    tweak_name = _(u'Harvest Chance')
    tweak_tip = _(u'Harvest chances on all plants will be set to the chosen '
                  u'percentage.')

    def __init__(self):
        super(AssortedTweak_HarvestChance, self).__init__(u'HarvestChance',
            (u'10%', 10), (u'20%', 20), (u'30%', 30), (u'40%', 40),
            (u'50%', 50), (u'60%', 60), (u'70%', 70), (u'80%', 80),
            (u'90%', 90), (u'100%', 100), (_(u'Custom'), 0))
        self.logMsg = u'* '+_(u'Harvest Chances Changed') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        modFile.convertToLongFids(self.tweak_read_classes)
        chance = self.choiceValues[self.chosen][0]
        patchBlock = patchFile.FLOR
        id_records = patchBlock.id_records
        for record in modFile.FLOR.getActiveRecords():
            if record.fid not in id_records:
                patchBlock.setRecord(record.getTypeCopy())

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        chance = self.choiceValues[self.chosen][0]
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.FLOR.records:
            if record.eid.startswith(u'Nirnroot'): continue # skip Nirnroots
            chances_changed = False
            for attr in (u'spring', u'summer', u'fall', u'winter'):
                if getattr(record, attr) != chance:
                    setattr(record, attr, chance)
                    chances_changed = True
            if chances_changed:
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

#------------------------------------------------------------------------------
class AssortedTweak_WindSpeed(MultiTweakItem):
    """Disables Weather winds."""
    tweak_read_classes = 'WTHR',
    tweak_name = _(u'Disable Wind')
    tweak_tip = _(u'Disables the wind on all weathers.')

    def __init__(self):
        super(AssortedTweak_WindSpeed, self).__init__(u'windSpeed',
            (_(u'Disable'), 0))
        self.logMsg = u'* '+_(u'Winds Disabled') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.WTHR
        id_records = patchBlock.id_records
        for record in modFile.WTHR.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.windSpeed != 0:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.WTHR.records:
            if record.windSpeed != 0:
                record.windSpeed = 0
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

#------------------------------------------------------------------------------
class AssortedTweak_UniformGroundcover(MultiTweakItem):
    """Eliminates random variation in groundcover."""
    tweak_read_classes = 'GRAS',
    tweak_name = _(u'Uniform Groundcover')
    tweak_tip = _(u'Eliminates random variation in groundcover (grasses, '
                  u'shrubs, etc.).')

    def __init__(self):
        super(AssortedTweak_UniformGroundcover, self).__init__(
            u'UniformGroundcover', (u'1.0', u'1.0'))
        self.logMsg = u'* '+_(u'Grasses Normalized') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.GRAS
        id_records = patchBlock.id_records
        for record in modFile.GRAS.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.heightRange != 0:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.GRAS.records:
            if record.heightRange != 0:
                record.heightRange = 0
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

#------------------------------------------------------------------------------
class AssortedTweak_SetCastWhenUsedEnchantmentCosts(MultiTweakItem):
    """Sets Cast When Used Enchantment number of uses."""
    tweak_read_classes = 'ENCH',
    tweak_name = _(
        u'Number of uses for pre-enchanted weapons and Staffs/Staves')
    tweak_tip = _(
        u'The charge amount and cast cost will be edited so that all '
        u'enchanted weapons and Staffs/Staves have the amount of uses '
        u'specified. Cost will be rounded up to 1 (unless set to unlimited) '
        u'so number of uses may not exactly match for all weapons.')

    def __init__(self):
        super(AssortedTweak_SetCastWhenUsedEnchantmentCosts, self).__init__(
            u'Number of uses:', (u'1', 1), (u'5', 5), (u'10', 10), (u'20', 20),
            (u'30', 30), (u'40', 40), (u'50', 50), (u'80', 80), (u'100', 100),
            (u'250', 250), (u'500', 500), (_(u'Unlimited'), 0),
            (_(u'Custom'), 0))
        self.logHeader = u'=== '+_(u'Set Enchantment Number of Uses')
        self.logMsg = u'* '+_(u'Enchantments set') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.ENCH
        id_records = patchBlock.id_records
        for record in modFile.ENCH.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.itemType in [1,2]:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.ENCH.records:
            if record.itemType in [1,2]:
                uses = self.choiceValues[self.chosen][0]
                cost = uses
                if uses != 0:
                    cost = max(record.chargeAmount/uses,1)
                record.enchantCost = cost
                record.chargeAmount = cost * uses
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

#------------------------------------------------------------------------------
class AssortedTweak_DefaultIcons(MultiTweakItem):
    """Sets a default icon for any records that don't have any icon
    assigned."""
    tweak_name = _(u'Default Icons')
    tweak_tip = _(u"Sets a default icon for any records that don't have any "
                  u"icon assigned")
    tweak_read_classes = (
        'ALCH', 'AMMO', 'APPA', 'ARMO', 'BOOK', 'BSGN', 'CLAS', 'CLOT', 'FACT',
        'INGR', 'KEYM', 'LIGH', 'MISC', 'QUST', 'SGST', 'SLGM', 'WEAP',)

    def __init__(self):
        super(AssortedTweak_DefaultIcons,self).__init__(u'icons', (u'1', 1))
        self.defaultEnabled = True
        self.logMsg = u'* '+_(u'Default Icons set') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        for blockType in self.tweak_read_classes:
            if blockType not in modFile.tops: continue
            modBlock = getattr(modFile,blockType)
            patchBlock = getattr(patchFile,blockType)
            id_records = patchBlock.id_records
            for record in modBlock.getActiveRecords():
                if mapper(record.fid) not in id_records:
                    record = record.getTypeCopy(mapper)
                    patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        count = Counter()
        keep = patchFile.getKeeper()
        for type_ in self.tweak_read_classes:
            if type_ not in patchFile.tops: continue
            for record in patchFile.tops[type_].records:
                if getattr(record, 'iconPath', None): continue
                if getattr(record, 'maleIconPath', None): continue
                if getattr(record, 'femaleIconPath', None): continue
                changed = False
                if type_ == 'ALCH':
                    record.iconPath = u"Clutter\\Potions\\IconPotion01.dds"
                    changed = True
                elif type_ == 'AMMO':
                    record.iconPath = u"Weapons\\IronArrow.dds"
                    changed = True
                elif type_ == 'APPA':
                    record.iconPath = u"Clutter\\IconMortarPestle.dds"
                    changed = True
                elif type_ == 'AMMO':
                    record.iconPath = u"Weapons\\IronArrow.dds"
                    changed = True
                elif type_ == 'ARMO':
                    if record.flags.notPlayable: continue
                    #choose based on body flags:
                    if record.flags.upperBody != 0:
                        record.maleIconPath = u"Armor\\Iron\\M\\Cuirass.dds"
                        record.femaleIconPath = u"Armor\\Iron\\F\\Cuirass.dds"
                        changed = True
                    elif record.flags.lowerBody != 0:
                        record.maleIconPath = u"Armor\\Iron\\M\\Greaves.dds"
                        record.femaleIconPath = u"Armor\\Iron\\F\\Greaves.dds"
                        changed = True
                    elif record.flags.head != 0 or record.flags.hair != 0:
                        record.maleIconPath = u"Armor\\Iron\\M\\Helmet.dds"
                        changed = True
                    elif record.flags.hand != 0:
                        record.maleIconPath = u"Armor\\Iron\\M\\Gauntlets.dds"
                        record.femaleIconPath =u"Armor\\Iron\\F\\Gauntlets.dds"
                        changed = True
                    elif record.flags.foot != 0:
                        record.maleIconPath = u"Armor\\Iron\\M\\Boots.dds"
                        changed = True
                    elif record.flags.shield != 0:
                        record.maleIconPath = u"Armor\\Iron\\M\\Shield.dds"
                        changed = True
                    else: #Default icon, probably a token or somesuch
                        record.maleIconPath = u"Armor\\Iron\\M\\Shield.dds"
                        changed = True
                elif type_ in ['BOOK', 'BSGN', 'CLAS']:  # just a random book
                    # icon for class/birthsign as well.
                    record.iconPath = u"Clutter\\iconbook%d.dds" % (
                        random.randint(1, 13))
                    changed = True
                elif type_ == 'CLOT':
                    if record.flags.notPlayable: continue
                    #choose based on body flags:
                    if record.flags.upperBody != 0:
                        record.maleIconPath = \
                            u"Clothes\\MiddleClass\\01\\M\\Shirt.dds"
                        record.femaleIconPath = \
                            u"Clothes\\MiddleClass\\01\\F\\Shirt.dds"
                        changed = True
                    elif record.flags.lowerBody != 0:
                        record.maleIconPath = \
                            u"Clothes\\MiddleClass\\01\\M\\Pants.dds"
                        record.femaleIconPath = \
                            u"Clothes\\MiddleClass\\01\\F\\Pants.dds"
                        changed = True
                    elif record.flags.head or record.flags.hair:
                        record.maleIconPath = \
                            u"Clothes\\MythicDawnrobe\\hood.dds"
                        changed = True
                    elif record.flags.hand != 0:
                        record.maleIconPath = \
                         u"Clothes\\LowerClass\\Jail\\M\\JailShirtHandcuff.dds"
                        changed = True
                    elif record.flags.foot != 0:
                        record.maleIconPath = \
                            u"Clothes\\MiddleClass\\01\\M\\Shoes.dds"
                        record.femaleIconPath = \
                            u"Clothes\\MiddleClass\\01\\F\\Shoes.dds"
                        changed = True
                    elif record.flags.leftRing or record.flags.rightRing:
                        record.maleIconPath = u"Clothes\\Ring\\RingNovice.dds"
                        changed = True
                    else: #amulet
                        record.maleIconPath = \
                            u"Clothes\\Amulet\\AmuletSilver.dds"
                        changed = True
                elif type_ == 'FACT':
                    #todo
                    #changed = True
                    pass
                elif type_ == 'INGR':
                    record.iconPath = u"Clutter\\IconSeeds.dds"
                    changed = True
                elif type_ == 'KEYM':
                    record.iconPath = \
                        [u"Clutter\\Key\\Key.dds", u"Clutter\\Key\\Key02.dds"][
                            random.randint(0, 1)]
                    changed = True
                elif type_ == 'LIGH':
                    if not record.flags.canTake: continue
                    record.iconPath = u"Lights\\IconTorch02.dds"
                    changed = True
                elif type_ == 'MISC':
                    record.iconPath = u"Clutter\\Soulgems\\AzurasStar.dds"
                    changed = True
                elif type_ == 'QUST':
                    if not record.stages: continue
                    record.iconPath = u"Quest\\icon_miscellaneous.dds"
                    changed = True
                elif type_ == 'SGST':
                    record.iconPath = u"IconSigilStone.dds"
                    changed = True
                elif type_ == 'SLGM':
                    record.iconPath = u"Clutter\\Soulgems\\AzurasStar.dds"
                    changed = True
                elif type_ == 'WEAP':
                    if record.weaponType == 0:
                        record.iconPath = u"Weapons\\IronDagger.dds"
                    elif record.weaponType == 1:
                        record.iconPath = u"Weapons\\IronClaymore.dds"
                    elif record.weaponType == 2:
                        record.iconPath = u"Weapons\\IronMace.dds"
                    elif record.weaponType == 3:
                        record.iconPath = u"Weapons\\IronBattleAxe.dds"
                    elif record.weaponType == 4:
                        record.iconPath = u"Weapons\\Staff.dds"
                    elif record.weaponType == 5:
                        record.iconPath = u"Weapons\\IronBow.dds"
                    else: #Should never reach this point
                        record.iconPath = u"Weapons\\IronDagger.dds"
                    changed = True
                if changed:
                    keep(record.fid)
                    count[record.fid[0]] += 1
        self._patchLog(log,count)

#------------------------------------------------------------------------------
# Will be refactored in inf-312-tweak-pooling
_nirnroot_words = {u'nirnroot', u'vynroot', u'vynwurz'}
def _is_nirnroot(record):
    return any(x in record.eid.lower() for x in _nirnroot_words)

class AssortedTweak_SetSoundAttenuationLevels(MultiTweakItem):
    """Sets Sound Attenuation Levels for all records except Nirnroots."""
    tweak_read_classes = 'SOUN',
    tweak_name = _(u'Set Sound Attenuation Levels')
    tweak_tip = _(u'Sets sound attenuation levels to tweak%*current level. '
                  u'Does not affect {}.').format(bush.game.nirnroots)

    def __init__(self):
        super(AssortedTweak_SetSoundAttenuationLevels, self).__init__(
            u'Attenuation%:', (u'0%', 0), (u'5%', 5), (u'10%', 10),
            (u'20%', 20), (u'50%', 50), (u'80%', 80), (_(u'Custom'), 0))
        self.logMsg = u'* '+_(u'Sounds Modified') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.SOUN
        id_records = patchBlock.id_records
        for record in modFile.SOUN.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.staticAtten and not _is_nirnroot(record):
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.SOUN.records:
            if record.staticAtten and not _is_nirnroot(record):
                record.staticAtten = record.staticAtten * \
                                     self.choiceValues[self.chosen][0] / 100
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

#------------------------------------------------------------------------------
class AssortedTweak_SetSoundAttenuationLevels_NirnrootOnly(MultiTweakItem):
    """Sets Sound Attenuation Levels for Nirnroots."""
    tweak_read_classes = 'SOUN',
    tweak_name = _(u'Set Sound Attenuation Levels: %s '
                   u'Only') % bush.game.nirnroots
    tweak_tip = _(u'Sets sound attenuation levels to tweak%*current level. '
                  u'Only affects {}.').format(bush.game.nirnroots)

    def __init__(self):
        super(AssortedTweak_SetSoundAttenuationLevels_NirnrootOnly,
              self).__init__(u'Nirnroot Attenuation%:', (u'0%', 0), (u'5%', 5),
            (u'10%', 10), (u'20%', 20), (u'50%', 50), (u'80%', 80),
            (_(u'Custom'), 0))
        self.logMsg = u'* ' + _(u'Sounds Modified') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.SOUN
        id_records = patchBlock.id_records
        for record in modFile.SOUN.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if _is_nirnroot(record) and record.staticAtten:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.SOUN.records:
            if _is_nirnroot(record) and record.staticAtten:
                record.staticAtten = record.staticAtten * \
                                     self.choiceValues[self.chosen][0] / 100
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

#------------------------------------------------------------------------------
class AssortedTweak_FactioncrimeGoldMultiplier(MultiTweakItem):
    """Fix factions with unset crime gold multiplier to have a
    crime gold multiplier of 1.0."""
    tweak_read_classes = b'FACT',
    tweak_name = _(u'Faction Crime Gold Multiplier Fix')
    tweak_tip = _(u'Fix factions with unset Crime Gold Multiplier to have a '
                  u'Crime Gold Multiplier of 1.0.')

    def __init__(self):
        super(AssortedTweak_FactioncrimeGoldMultiplier, self).__init__(
            u'FactioncrimeGoldMultiplier', (u'1.0', u'1.0'))
        self.logMsg = u'* '+_(u'Factions fixed') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.FACT
        for record in modFile.FACT.getActiveRecords():
            if record.crime_gold_multiplier is None:
                patchRecords.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.FACT.records:
            if record.crime_gold_multiplier is None:
                record.crime_gold_multiplier = 1.0
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

#------------------------------------------------------------------------------
class AssortedTweak_LightFadeValueFix(MultiTweakItem):
    """Remove light flickering for low end machines."""
    tweak_read_classes = 'LIGH',
    tweak_name = _(u'No Light Fade Value Fix')
    tweak_tip = _(u"Sets Light's Fade values to default of 1.0 if not set.")

    def __init__(self):
        super(AssortedTweak_LightFadeValueFix, self).__init__(
            u'NoLightFadeValueFix', (u'1.0', u'1.0'))
        self.logMsg = u'* ' + _(u'Lights with fade values added') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.LIGH
        for record in modFile.LIGH.getActiveRecords():
            if not isinstance(record.fade,float):
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.LIGH.records:
            if not isinstance(record.fade,float):
                record.fade = 1.0
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

#------------------------------------------------------------------------------
class AssortedTweak_TextlessLSCRs(MultiTweakItem):
    """Removes the description from loading screens."""
    tweak_read_classes = 'LSCR',
    tweak_name = _(u'No Description Loading Screens')
    tweak_tip = _(u'Removes the description from loading screens.')

    def __init__(self):
        super(AssortedTweak_TextlessLSCRs, self).__init__(u'NoDescLSCR',
            (u'1.0', u'1.0'))
        self.logMsg = u'* '+_(u'Loading screens tweaked') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.LSCR
        for record in modFile.LSCR.getActiveRecords():
            if record.text:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.LSCR.records:
            if record.text:
                record.text = u''
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class AssortedTweaker(MultiTweaker):
    """Tweaks assorted stuff. Sub-tweaks behave like patchers themselves."""
    scanOrder = 32
    editOrder = 32

    @classmethod
    def tweak_instances(cls):
        return sorted([
            AssortedTweak_ArmorShows(_(u"Armor Shows Amulets"),
                _(u"Prevents armor from hiding amulets."),
                u'armorShowsAmulets',
                ),
            AssortedTweak_ArmorShows(_(u"Armor Shows Rings"),
                _(u"Prevents armor from hiding rings."),
                u'armorShowsRings',
                ),
            AssortedTweak_ClothingShows(_(u"Clothing Shows Amulets"),
                _(u"Prevents Clothing from hiding amulets."),
                u'ClothingShowsAmulets',
                ),
            AssortedTweak_ClothingShows(_(u"Clothing Shows Rings"),
                _(u"Prevents Clothing from hiding rings."),
                u'ClothingShowsRings',
                ),
            AssortedTweak_ArmorPlayable(),
            AssortedTweak_ClothingPlayable(),
            AssortedTweak_BowReach(),
            AssortedTweak_ConsistentRings(),
            AssortedTweak_DarnBooks(),
            AssortedTweak_FogFix(),
            AssortedTweak_NoLightFlicker(),
            AssortedTweak_PotionWeight(),
            AssortedTweak_PotionWeightMinimum(),
            AssortedTweak_StaffWeight(),
            AssortedTweak_SetCastWhenUsedEnchantmentCosts(),
            AssortedTweak_WindSpeed(),
            AssortedTweak_UniformGroundcover(),
            AssortedTweak_HarvestChance(),
            AssortedTweak_IngredientWeight(),
            AssortedTweak_ArrowWeight(),
            AssortedTweak_ScriptEffectSilencer(),
            AssortedTweak_DefaultIcons(),
            AssortedTweak_SetSoundAttenuationLevels(),
            AssortedTweak_SetSoundAttenuationLevels_NirnrootOnly(),
            AssortedTweak_FactioncrimeGoldMultiplier(),
            AssortedTweak_LightFadeValueFix(),
            AssortedTweak_SkyrimStyleWeapons(),
            AssortedTweak_TextlessLSCRs(),
            ],key=lambda a: a.tweak_name.lower())
