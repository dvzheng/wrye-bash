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

"""This module contains the oblivion MultitweakItem patcher classes that tweak
races records. As opposed to the rest of the multitweak items these are not
grouped by a MultiTweaker but by the RacePatcher (also in this module) which
is a special patcher. Notice the PBash ones do not log in buildPatch - the
RacesTweaker patcher was calling their "log" method - now super's _patchLog()
"""

from __future__ import print_function
import random
import re
from collections import Counter
# Internal
from ... import bosh, bush
from ...bolt import GPath, deprint
from ...brec import MreRecord, MelObject, strFid
from ...exception import BoltError
from ...mod_files import ModFile, LoadFactory
from ...patcher.base import AMultiTweaker
from .base import MultiTweakItem, ListPatcher

# Patchers: 40 ----------------------------------------------------------------
_main_master = GPath(bush.game.master_file)

class RaceTweaker_BiggerOrcsAndNords(MultiTweakItem):
    """Adjusts the Orc and Nord race records to be taller/heavier."""
    tweak_read_classes = 'RACE',
    tweak_name = _(u'Bigger Nords and Orcs')
    tweak_tip = _(u'Adjusts the Orc and Nord race records to be '
                  u'taller/heavier - to be more lore friendly.')

    def __init__(self):
        super(RaceTweaker_BiggerOrcsAndNords, self).__init__(
            u'BiggerOrcsandNords',
            # ('Example',(Nordmaleheight,NordFheight,NordMweight,
            # NordFweight,Orcmaleheight,OrcFheight,OrcMweight,OrcFweight))
            (u'Bigger Nords and Orcs',
             ((1.09, 1.09, 1.13, 1.06), (1.09, 1.09, 1.13, 1.0))),
            (u'MMM Resized Races',
                ((1.08, 1.07, 1.28, 1.19), (1.09, 1.06, 1.36, 1.3))),
            (u'RBP', ((1.075,1.06,1.20,1.125),(1.06,1.045,1.275,1.18))))
        self.logMsg = u'* '+ _(u'Races tweaked') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.RACE
        for record in modFile.RACE.getActiveRecords():
            if not record.full: continue
            if not u'orc' in record.full.lower() and not u'nord' in \
                    record.full.lower(): continue
            record = record.getTypeCopy(mapper)
            patchRecords.setRecord(record)

    def buildPatch(self, progress, patchFile, extra_):
        """Edits patch file as desired."""
        count = self.count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.RACE.records:
            if not record.full: continue
            if u'nord' in record.full.lower():
                for attr, value in zip(
                        ['maleHeight', 'femaleHeight', 'maleWeight',
                         'femaleWeight'],
                        self.choiceValues[self.chosen][0][0]):
                    setattr(record,attr,value)
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
                continue
            elif u'orc' in record.full.lower():
                for attr, value in zip(
                        ['maleHeight', 'femaleHeight', 'maleWeight',
                         'femaleWeight'],
                        self.choiceValues[self.chosen][0][1]):
                    setattr(record,attr,value)
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1

class RaceTweaker_MergeSimilarRaceHairs(MultiTweakItem):
    """Merges similar race's hairs (kinda specifically designed for SOVVM's
    bearded races)."""
    tweak_read_classes = 'RACE',
    tweak_name = _(u'Merge Hairs from similar races')
    tweak_tip = _(u'Merges hair lists from similar races (f.e. give RBP '
                  u'khajit hair to all the other varieties of khajits in '
                  u'Elsweyr)')

    def __init__(self):
        super(RaceTweaker_MergeSimilarRaceHairs, self).__init__(
            u'MergeSimilarRaceHairLists',
            (_(u'Merge hairs only from vanilla races'), 1),
            (_(u'Full hair merge between similar races'), 0))
        self.logMsg = u'* '+ _(u'Races tweaked') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.RACE
        for record in modFile.RACE.getActiveRecords():
            if not record.full: continue
            patchRecords.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self, progress, patchFile, extra_):
        """Edits patch file as desired."""
        count = self.count = Counter()
        #process hair lists
        changedHairs = {}
        vanilla = ['argonian', 'breton', 'dremora', 'dark elf', 'dark seducer',
                   'golden saint', 'high elf', 'imperial', 'khajiit', 'nord',
                   'orc', 'redguard', 'wood elf']
        if self.choiceValues[self.chosen][0] == 1:  # merge hairs only from
            # vanilla races to custom hairs.
            for race in extra_:
                for r in vanilla:
                    if r in race:
                        if extra_[r]['hairs'] != extra_[race]['hairs']:
                            changedHairs[race] = list(set(
                                extra_[r]['hairs'] + extra_[race][
                                    'hairs']))  # yuach nasty but quickly
                                    # and easily removes duplicates.
        else: # full back and forth merge!
            for race in extra_:
                #nasty processing slog
                rs = race.split('(')
                rs = rs[0].split()
                if len(rs) > 1 and rs[1] in ['elf','seducer']:
                    rs[0] = rs[0]+' '+rs[1]
                    del(rs[1])
                for r in extra_:
                    if r == race: continue
                    for s in rs:
                        if s in r:
                            if extra_[r]['hairs'] != extra_[race]['hairs']:
                                changedHairs[race] = list(set(
                                    extra_[r]['hairs'] + extra_[race]['hairs']))
                                # list(set([]) disgusting thing again
        keep = patchFile.getKeeper()
        for record in patchFile.RACE.records:
            if not record.full: continue
            if not record.full.lower() in changedHairs: continue
            record.hairs = changedHairs[record.full.lower()]
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1

class RaceTweaker_MergeSimilarRaceEyes(MultiTweakItem):
    """Merges similar race's eyes."""
    tweak_read_classes = 'RACE',
    tweak_name = _(u'Merge Eyes from similar races')
    tweak_tip = _(u'Merges eye lists from similar races (f.e. give RBP khajit '
                  u'eyes to all the other varieties of khajits in Elsweyr)')

    def __init__(self):
        super(RaceTweaker_MergeSimilarRaceEyes, self).__init__(
            u'MergeSimilarRaceEyeLists',
            (_(u'Merge eyes only from vanilla races'), 1),
            (_(u'Full eye merge between similar races'), 0))
        self.logMsg = u'* '+ _(u'Races tweaked') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.RACE
        for record in modFile.RACE.getActiveRecords():
            if not record.full: continue
            patchRecords.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self, progress, patchFile, extra_):
        """Edits patch file as desired."""
        count = self.count = Counter()
        #process hair lists
        changedEyes = {}
        vanilla = ['argonian', 'breton', 'dremora', 'dark elf', 'dark seducer',
                   'golden saint', 'high elf', 'imperial', 'khajiit', 'nord',
                   'orc', 'redguard', 'wood elf']
        if self.choiceValues[self.chosen][0] == 1:  # merge eyes only from
            # vanilla races to custom eyes.
            for race in extra_:
                for r in vanilla:
                    if r in race:
                        if extra_[r]['eyes'] != extra_[race]['eyes']:
                            changedEyes[race] = list(set(
                                extra_[r]['eyes'] + extra_[race][
                                    'eyes']))  # yuach nasty but quickly and
                                    #  easily removes duplicates.
        else: # full back and forth merge!
            for race in extra_:
                #nasty processing slog
                rs = race.split('(')
                rs = rs[0].split()
                if len(rs) > 1 and rs[1] in ['elf','seducer']:
                    rs[0] = rs[0]+' '+rs[1]
                    del(rs[1])
                for r in extra_:
                    if r == race: continue
                    for s in rs:
                        if s in r:
                            if extra_[r]['eyes'] != extra_[race]['eyes']:
                                changedEyes[race] = list(set(
                                    changedEyes.setdefault(race, []) +
                                    extra_[r]['eyes'] + extra_[race]['eyes']))
                                # list(set([]) disgusting thing again
        keep = patchFile.getKeeper()
        for record in patchFile.RACE.records:
            if not record.full: continue
            if not record.full.lower() in changedEyes: continue
            record.eyes = changedEyes[record.full.lower()]
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1

class RaceTweaker_AllHairs(MultiTweakItem):
    """Gives all races ALL hairs."""
    tweak_read_classes = 'RACE',
    tweak_name = _(u'Races Have All Hairs')
    tweak_tip = _(u'Gives all races every available hair.')

    def __init__(self):
        super(RaceTweaker_AllHairs, self).__init__(u'hairyraces',
            (u'get down tonight',1))
        self.logMsg = u'* '+ _(u'Races tweaked') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.RACE
        for record in modFile.RACE.getActiveRecords():
            patchRecords.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self, progress, patchFile, extra_):
        """Edits patch file as desired."""
        count = self.count = Counter()
        hairs = extra_['HAIR']
        keep = patchFile.getKeeper()
        for record in patchFile.RACE.records:
            if record.hairs == hairs: continue
            record.hairs = hairs
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1

class RaceTweaker_AllEyes(MultiTweakItem):
    """Gives all races ALL eyes."""
    tweak_read_classes = 'RACE',
    tweak_name = _(u'Races Have All Eyes')
    tweak_tip = _(u'Gives all races every available eye.')

    def __init__(self):
        super(RaceTweaker_AllEyes, self).__init__(u'eyeyraces',
            (u'what a lot of eyes you have dear', 1))
        self.logMsg = u'* '+ _(u'Races tweaked') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.RACE
        for record in modFile.RACE.getActiveRecords():
            patchRecords.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self, progress, patchFile, extra_):
        """Edits patch file as desired."""
        count = self.count = Counter()
        eyes = extra_['EYES']
        keep = patchFile.getKeeper()
        for record in patchFile.RACE.records:
            if record.eyes == eyes: continue
            record.eyes = eyes
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1

class RaceTweaker_PlayableEyes(MultiTweakItem):
    """Sets all eyes to be playable."""
    tweak_read_classes = 'EYES',
    tweak_name = _(u'Playable Eyes')
    tweak_tip = _(u'Sets all eyes to be playable.')

    def __init__(self):
        super(RaceTweaker_PlayableEyes, self).__init__(u'playableeyes',
            (u'Get it done', 1))
        self.logMsg = u'* '+ _(u'Eyes tweaked') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.EYES
        for record in modFile.EYES.getActiveRecords():
            if record.flags.playable: continue
            patchRecords.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self, progress, patchFile, extra_):
        """Edits patch file as desired."""
        count = self.count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.EYES.records:
            if record.flags.playable: continue
            record.flags.playable = True
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1

class RaceTweaker_PlayableHairs(MultiTweakItem):
    """Sets all hairs to be playable."""
    tweak_read_classes = 'HAIR',
    tweak_name = _(u'Playable Hairs')
    tweak_tip = _(u'Sets all Hairs to be playable.')

    def __init__(self):
        super(RaceTweaker_PlayableHairs, self).__init__(u'playablehairs',
            (u'Get it done', 1))
        self.logMsg = u'* '+ _(u'Hairs tweaked') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.HAIR
        for record in modFile.HAIR.getActiveRecords():
            if record.flags.playable: continue
            patchRecords.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self, progress, patchFile, extra_):
        """Edits patch file as desired."""
        count = self.count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.HAIR.records:
            if record.flags.playable: continue
            record.flags.playable = True
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1

class RaceTweaker_SexlessHairs(MultiTweakItem):
    """Sets all hairs to be playable by both males and females."""
    tweak_read_classes = 'HAIR',
    tweak_name = _(u'Sexless Hairs')
    tweak_tip = _(u'Lets any sex of character use any hair.')

    def __init__(self):
        super(RaceTweaker_SexlessHairs, self).__init__(u'sexlesshairs',
            (u'Get it done', 1))
        self.logMsg = u'* '+ _(u'Hairs tweaked') + u': %d'

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.HAIR
        for record in modFile.HAIR.getActiveRecords():
            if record.flags.notMale or record.flags.notFemale:
                patchRecords.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self, progress, patchFile, extra_):
        """Edits patch file as desired."""
        count = self.count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.HAIR.records:
            if record.flags.notMale or record.flags.notFemale:
                record.flags.notMale = 0
                record.flags.notFemale = 0
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1

def _find_vanilla_eyes():
    """Converts vanilla default_eyes to use long FormIDs and returns the
    result."""
    def _conv_fid(race_fid): return GPath(race_fid[0]), race_fid[1]
    ret = {}
    for race_fid, race_eyes in bush.game.default_eyes.iteritems():
        new_key = _conv_fid(race_fid)
        new_val = [_conv_fid(eye_fid) for eye_fid in race_eyes]
        ret[new_key] = new_val
    return ret

#------------------------------------------------------------------------------
# Race Patcher ----------------------------------------------------------------
#------------------------------------------------------------------------------
class RacePatcher(AMultiTweaker, ListPatcher):
    """Race patcher - we inherit from AMultiTweaker to use tweak_instances."""
    group = _(u'Special')
    scanOrder = 40
    editOrder = 40
    _read_write_records = ('RACE', 'EYES', 'HAIR', 'NPC_',)
    _tweak_classes = [RaceTweaker_BiggerOrcsAndNords,
        RaceTweaker_MergeSimilarRaceHairs, RaceTweaker_MergeSimilarRaceEyes,
        RaceTweaker_PlayableEyes, RaceTweaker_PlayableHairs,
        RaceTweaker_SexlessHairs, RaceTweaker_AllEyes, RaceTweaker_AllHairs, ]

    def __init__(self, p_name, p_file, p_sources, enabled_tweaks):
        # NB: call the ListPatcher __init__ not the AMultiTweaker one!
        super(AMultiTweaker, self).__init__(p_name, p_file, p_sources)
        self.races_data = {'EYES':[],'HAIR':[]}
        self.raceData = {} #--Race eye meshes, hair,eyes
        self.tempRaceData = {}
        #--Restrict srcs to active/merged mods.
        self.srcs = [x for x in self.srcs if x in p_file.allSet]
        self.isActive = True #--Always enabled to support eye filtering
        self.bodyKeys = {'TailModel', 'UpperBodyPath', 'LowerBodyPath',
                         'HandPath', 'FootPath', 'TailPath'}
        self.sizeKeys = {'Height', 'Weight'}
        self.raceAttributes = {'Strength', 'Intelligence', 'Willpower',
                               'Agility', 'Speed', 'Endurance', 'Personality',
                               'Luck'}
        self.raceSkills = {'skill1', 'skill1Boost', 'skill2', 'skill2Boost',
                           'skill3', 'skill3Boost', 'skill4', 'skill4Boost',
                           'skill5', 'skill5Boost', 'skill6', 'skill6Boost',
                           'skill7', 'skill7Boost'}
        self.eyeKeys = {u'Eyes'}
        self.eye_mesh = {}
        self.scanTypes = {'RACE', 'EYES', 'HAIR', 'NPC_'}
        self.vanilla_eyes = _find_vanilla_eyes()
        self.enabled_tweaks = enabled_tweaks

    def initData(self,progress):
        """Get data from source files."""
        if not self.isActive or not self.srcs: return
        loadFactory = LoadFactory(False,MreRecord.type_class['RACE'])
        progress.setFull(len(self.srcs))
        cachedMasters = {}
        for index,srcMod in enumerate(self.srcs):
            if srcMod not in bosh.modInfos: continue
            srcInfo = bosh.modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            bashTags = srcInfo.getBashTags()
            if 'RACE' not in srcFile.tops: continue
            srcFile.convertToLongFids(('RACE',))
            self.tempRaceData = {} #so as not to carry anything over!
            if u'R.ChangeSpells' in bashTags and u'R.AddSpells' in bashTags:
                raise BoltError(
                    u'WARNING mod %s has both R.AddSpells and R.ChangeSpells '
                    u'tags - only one of those tags should be on a mod at '
                    u'one time' % srcMod.s)
            for race in srcFile.RACE.getActiveRecords():
                tempRaceData = self.tempRaceData.setdefault(race.fid,{})
                raceData = self.raceData.setdefault(race.fid,{})
                if u'Hair' in bashTags:
                    raceHair = raceData.setdefault('hairs',[])
                    for hair in race.hairs:
                        if hair not in raceHair: raceHair.append(hair)
                if self.eyeKeys & bashTags:
                    tempRaceData['rightEye'] = race.rightEye
                    tempRaceData['leftEye'] = race.leftEye
                    raceEyes = raceData.setdefault('eyes',[])
                    for eye in race.eyes:
                        if eye not in raceEyes: raceEyes.append(eye)
                if u'Voice-M' in bashTags:
                    tempRaceData['maleVoice'] = race.maleVoice
                if u'Voice-F' in bashTags:
                    tempRaceData['femaleVoice'] = race.femaleVoice
                if u'Body-M' in bashTags:
                    for key in ['male'+key for key in self.bodyKeys]:
                        tempRaceData[key] = getattr(race,key)
                if u'Body-F' in bashTags:
                    for key in ['female'+key for key in self.bodyKeys]:
                        tempRaceData[key] = getattr(race,key)
                if u'Body-Size-M' in bashTags:
                    for key in ['male'+key for key in self.sizeKeys]:
                        tempRaceData[key] = getattr(race,key)
                if u'Body-Size-F' in bashTags:
                    for key in ['female'+key for key in self.sizeKeys]:
                        tempRaceData[key] = getattr(race,key)
                if u'R.Teeth' in bashTags:
                    for key in ('teethLower','teethUpper'):
                        tempRaceData[key] = getattr(race,key)
                if u'R.Mouth' in bashTags:
                    for key in ('mouth','tongue'):
                        tempRaceData[key] = getattr(race,key)
                if u'R.Head' in bashTags:
                    tempRaceData['head'] = race.head
                if u'R.Ears' in bashTags:
                    for key in ('maleEars','femaleEars'):
                        tempRaceData[key] = getattr(race,key)
                if u'R.Relations' in bashTags:
                    relations = raceData.setdefault('relations',{})
                    for x in race.relations:
                        relations[x.faction] = x.mod
                if u'R.Attributes-F' in bashTags:
                    for key in ['female'+key for key in self.raceAttributes]:
                        tempRaceData[key] = getattr(race,key)
                if u'R.Attributes-M' in bashTags:
                    for key in ['male'+key for key in self.raceAttributes]:
                        tempRaceData[key] = getattr(race,key)
                if u'R.Skills' in bashTags:
                    for key in self.raceSkills:
                        tempRaceData[key] = getattr(race,key)
                if u'R.AddSpells' in bashTags:
                    tempRaceData['AddSpells'] = race.spells
                if u'R.ChangeSpells' in bashTags:
                    raceData['spellsOverride'] = race.spells
                if u'R.Description' in bashTags:
                    tempRaceData['text'] = race.text
            for master in srcInfo.masterNames:
                if not master in bosh.modInfos: continue  # or break
                # filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = bosh.modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    if 'RACE' not in masterFile.tops: continue
                    masterFile.convertToLongFids(('RACE',))
                    cachedMasters[master] = masterFile
                for race in masterFile.RACE.getActiveRecords():
                    if race.fid not in self.tempRaceData: continue
                    tempRaceData = self.tempRaceData[race.fid]
                    raceData = self.raceData[race.fid]
                    if 'AddSpells' in tempRaceData:
                        raceData.setdefault('AddSpells', [])
                        for spell in tempRaceData['AddSpells']:
                            if spell not in race.spells:
                                if spell not in raceData['AddSpells']:
                                    raceData['AddSpells'].append(spell)
                        del tempRaceData['AddSpells']
                    for key in tempRaceData:
                        if not tempRaceData[key] == getattr(race,key):
                            raceData[key] = tempRaceData[key]
            progress.plus()

    def scanModFile(self, modFile, progress):
        """Add appropriate records from modFile."""
        races_data = self.races_data
        eye_mesh = self.eye_mesh
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        if not (set(modFile.tops) & self.scanTypes): return
        modFile.convertToLongFids(('RACE','EYES','HAIR','NPC_'))
        srcEyes = set(
            [record.fid for record in modFile.EYES.getActiveRecords()])
        #--Eyes, Hair
        for type in ('EYES','HAIR'):
            patchBlock = getattr(self.patchFile,type)
            id_records = patchBlock.id_records
            for record in getattr(modFile,type).getActiveRecords():
                races_data[type].append(record.fid)
                if record.fid not in id_records:
                    patchBlock.setRecord(record.getTypeCopy(mapper))
        #--Npcs with unassigned eyes
        patchBlock = self.patchFile.NPC_
        id_records = patchBlock.id_records
        for record in modFile.NPC_.getActiveRecords():
            if not record.eye and record.fid not in id_records:
                patchBlock.setRecord(record.getTypeCopy(mapper))
        #--Race block
        patchBlock = self.patchFile.RACE
        id_records = patchBlock.id_records
        for record in modFile.RACE.getActiveRecords():
            if record.fid not in id_records:
                patchBlock.setRecord(record.getTypeCopy(mapper))
            if not record.rightEye or not record.leftEye:
                # Don't complain if the FULL is missing, that probably means
                # it's an internal or unused RACE
                if record.full:
                    deprint(u'No right and/or no left eye recorded in race '
                            u'%s, from mod %s' % (record.full, modName))
                continue
            for eye in record.eyes:
                if eye in srcEyes:
                    eye_mesh[eye] = (record.rightEye.modPath.lower(),
                                     record.leftEye.modPath.lower())
        for tweak in self.enabled_tweaks:
            tweak.scanModFile(modFile,progress,self.patchFile)

    def buildPatch(self,log,progress):
        """Updates races as needed."""
        debug = False
        extra_ = self.races_data
        if not self.isActive: return
        patchFile = self.patchFile
        keep = patchFile.getKeeper()
        if 'RACE' not in patchFile.tops: return
        racesPatched = []
        racesSorted = []
        racesFiltered = []
        mod_npcsFixed = {}
        reProcess = re.compile(
            u'(?:dremora)|(?:akaos)|(?:lathulet)|(?:orthe)|(?:ranyu)',
            re.I | re.U)
        #--Import race info
        for race in patchFile.RACE.records:
            #~~print 'Building',race.eid
            raceData = self.raceData.get(race.fid,None)
            if not raceData: continue
            raceChanged = False
            #-- Racial Hair and  Eye sets
            if 'hairs' in raceData and (
                        set(race.hairs) != set(raceData['hairs'])):
                race.hairs = raceData['hairs']
                raceChanged = True
            if 'eyes' in raceData:
                if set(race.eyes) != set(raceData['eyes']):
                    race.eyes = raceData['eyes']
                    raceChanged = True
            #-- Eye paths:
            if 'rightEye' in raceData:
                if not race.rightEye:
                    deprint(u'Very odd race %s found - no right eye '
                            u'assigned' % race.full)
                else:
                    if race.rightEye.modPath != raceData['rightEye'].modPath:
                        race.rightEye.modPath = raceData['rightEye'].modPath
                        raceChanged = True
            if 'leftEye' in raceData:
                if not race.leftEye:
                    deprint(u'Very odd race %s found - no left eye '
                            u'assigned' % race.full)
                else:
                    if race.leftEye.modPath != raceData['leftEye'].modPath:
                        race.leftEye.modPath = raceData['leftEye'].modPath
                        raceChanged = True
            #--Teeth/Mouth/head/ears/description
            for key in ('teethLower', 'teethUpper', 'mouth', 'tongue', 'text',
                    'head'):
                if key in raceData:
                    if getattr(race,key) != raceData[key]:
                        setattr(race,key,raceData[key])
                        raceChanged = True
            #--spells
            if 'spellsOverride' in raceData:
                race.spells = raceData['spellsOverride']
            if 'AddSpells' in raceData:
                raceData['spells'] = race.spells
                for spell in raceData['AddSpells']:
                    raceData['spells'].append(spell)
                race.spells = raceData['spells']
            #--skills
            for key in self.raceSkills:
                if key in raceData:
                    if getattr(race,key) != raceData[key]:
                        setattr(race,key,raceData[key])
                        raceChanged = True
            #--Gender info (voice, gender specific body data)
            for gender in ('male','female'):
                bodyKeys = self.bodyKeys.union(self.raceAttributes.union(
                    {'Ears', 'Voice'}))
                bodyKeys = [gender+key for key in bodyKeys]
                for key in bodyKeys:
                    if key in raceData:
                        if getattr(race,key) != raceData[key]:
                            setattr(race,key,raceData[key])
                            raceChanged = True
            #--Relations
            if 'relations' in raceData:
                relations = raceData['relations']
                oldRelations = set((x.faction,x.mod) for x in race.relations)
                newRelations = set(relations.iteritems())
                if newRelations != oldRelations:
                    del race.relations[:]
                    for faction,mod in newRelations:
                        entry = MelObject()
                        entry.faction = faction
                        entry.mod = mod
                        race.relations.append(entry)
                    raceChanged = True
            #--Changed
            if raceChanged:
                racesPatched.append(race.eid)
                keep(race.fid)
        #--Eye Mesh filtering
        eye_mesh = self.eye_mesh
        try:
            blueEyeMesh = eye_mesh[(_main_master, 0x27308)]
        except KeyError:
            print(u'error getting blue eye mesh:')
            print(u'eye meshes:', eye_mesh)
            raise
        argonianEyeMesh = eye_mesh[(_main_master, 0x3e91e)]
        if debug:
            print(u'== Eye Mesh Filtering')
            print(u'blueEyeMesh',blueEyeMesh)
            print(u'argonianEyeMesh',argonianEyeMesh)
        for eye in (
            (_main_master, 0x1a), #--Reanimate
            (_main_master, 0x54bb9), #--Dark Seducer
            (_main_master, 0x54bba), #--Golden Saint
            (_main_master, 0x5fa43), #--Ordered
            ):
            eye_mesh.setdefault(eye,blueEyeMesh)
        def setRaceEyeMesh(race,rightPath,leftPath):
            race.rightEye.modPath = rightPath
            race.leftEye.modPath = leftPath
        for race in patchFile.RACE.records:
            if debug: print(u'===', race.eid)
            if not race.eyes: continue  #--Sheogorath. Assume is handled
            # correctly.
            if not race.rightEye or not race.leftEye: continue #--WIPZ race?
            if re.match(u'^117[a-zA-Z]', race.eid, flags=re.U): continue  #--
            #  x117 race?
            raceChanged = False
            mesh_eye = {}
            for eye in race.eyes:
                if eye not in eye_mesh:
                    deprint(
                        _(u'Mesh undefined for eye %s in race %s, eye removed '
                          u'from race list.') % (
                            strFid(eye), race.eid,))
                    continue
                mesh = eye_mesh[eye]
                if mesh not in mesh_eye:
                    mesh_eye[mesh] = []
                mesh_eye[mesh].append(eye)
            currentMesh = (
                race.rightEye.modPath.lower(), race.leftEye.modPath.lower())
            try:
                maxEyesMesh = \
                    sorted(mesh_eye.keys(), key=lambda a: len(mesh_eye[a]),
                           reverse=True)[0]
            except IndexError:
                maxEyesMesh = blueEyeMesh
            #--Single eye mesh, but doesn't match current mesh?
            if len(mesh_eye) == 1 and currentMesh != maxEyesMesh:
                setRaceEyeMesh(race,*maxEyesMesh)
                raceChanged = True
            #--Multiple eye meshes (and playable)?
            if debug:
                for mesh,eyes in mesh_eye.iteritems():
                    print(mesh)
                    for eye in eyes: print(' ',strFid(eye))
            if len(mesh_eye) > 1 and (race.flags.playable or race.fid == (
                    _main_master, 0x038010)):
                #--If blueEyeMesh (mesh used for vanilla eyes) is present,
                # use that.
                if blueEyeMesh in mesh_eye and currentMesh != argonianEyeMesh:
                    setRaceEyeMesh(race,*blueEyeMesh)
                    race.eyes = mesh_eye[blueEyeMesh]
                    raceChanged = True
                elif argonianEyeMesh in mesh_eye:
                    setRaceEyeMesh(race,*argonianEyeMesh)
                    race.eyes = mesh_eye[argonianEyeMesh]
                    raceChanged = True
                #--Else figure that current eye mesh is the correct one
                elif currentMesh in mesh_eye:
                    race.eyes = mesh_eye[currentMesh]
                    raceChanged = True
                #--Else use most popular eye mesh
                else:
                    setRaceEyeMesh(race,*maxEyesMesh)
                    race.eyes = mesh_eye[maxEyesMesh]
                    raceChanged = True
            if raceChanged:
                racesFiltered.append(race.eid)
                keep(race.fid)
            if race.full:
                extra_[race.full.lower()] = {'hairs': race.hairs,
                                            'eyes': race.eyes,
                                            'relations': race.relations}
        for tweak in self.enabled_tweaks:
            tweak.buildPatch(progress,self.patchFile,extra_)
        #--Sort Eyes/Hair
        final_eyes = {}
        defaultMaleHair = {}
        defaultFemaleHair = {}
        eyeNames  = dict((x.fid,x.full) for x in patchFile.EYES.records)
        hairNames = dict((x.fid,x.full) for x in patchFile.HAIR.records)
        maleHairs = set(
            x.fid for x in patchFile.HAIR.records if not x.flags.notMale)
        femaleHairs = set(
            x.fid for x in patchFile.HAIR.records if not x.flags.notFemale)
        for race in patchFile.RACE.records:
            if (race.flags.playable or race.fid == (
                    _main_master, 0x038010)) and race.eyes:
                final_eyes[race.fid] = [x for x in
                                        self.vanilla_eyes.get(race.fid, [])
                                        if x in race.eyes]
                if not final_eyes[race.fid]:
                    final_eyes[race.fid] = [race.eyes[0]]
                defaultMaleHair[race.fid] = [x for x in race.hairs if
                                             x in maleHairs]
                defaultFemaleHair[race.fid] = [x for x in race.hairs if
                                               x in femaleHairs]
                race.hairs.sort(key=lambda x: hairNames.get(x))
                race.eyes.sort(key=lambda x: eyeNames.get(x))
                racesSorted.append(race.eid)
                keep(race.fid)
        #--Npcs with unassigned eyes/hair
        for npc in patchFile.NPC_.records:
            if npc.fid == (_main_master, 0x000007): continue  #
            # skip player
            if npc.full is not None and npc.race == (
                    _main_master, 0x038010) and not reProcess.search(
                    npc.full): continue
            raceEyes = final_eyes.get(npc.race)
            if not npc.eye and raceEyes:
                npc.eye = random.choice(raceEyes)
                srcMod = npc.fid[0]
                if srcMod not in mod_npcsFixed: mod_npcsFixed[srcMod] = set()
                mod_npcsFixed[srcMod].add(npc.fid)
                keep(npc.fid)
            raceHair = (
                (defaultMaleHair, defaultFemaleHair)[npc.flags.female]).get(
                npc.race)
            if not npc.hair and raceHair:
                npc.hair = random.choice(raceHair)
                srcMod = npc.fid[0]
                if srcMod not in mod_npcsFixed: mod_npcsFixed[srcMod] = set()
                mod_npcsFixed[srcMod].add(npc.fid)
                keep(npc.fid)
            if not npc.hairLength:
                npc.hairLength = random.random()
                srcMod = npc.fid[0]
                if srcMod not in mod_npcsFixed: mod_npcsFixed[srcMod] = set()
                keep(npc.fid)
                if npc.fid in mod_npcsFixed[srcMod]: continue
                mod_npcsFixed[srcMod].add(npc.fid)

        #--Done
        log.setHeader(u'= ' + self._patcher_name)
        self._srcMods(log)
        log(u'\n=== '+_(u'Merged'))
        if not racesPatched:
            log(u'. ~~%s~~'%_(u'None'))
        else:
            for eid in sorted(racesPatched):
                log(u'* '+eid)
        log(u'\n=== '+_(u'Eyes/Hair Sorted'))
        if not racesSorted:
            log(u'. ~~%s~~'%_(u'None'))
        else:
            for eid in sorted(racesSorted):
                log(u'* '+eid)
        log(u'\n=== '+_(u'Eye Meshes Filtered'))
        if not racesFiltered:
            log(u'. ~~%s~~'%_(u'None'))
        else:
            log(_(u"In order to prevent 'googly eyes', incompatible eyes have "
                  u"been removed from the following races."))
            for eid in sorted(racesFiltered):
                log(u'* '+eid)
        if mod_npcsFixed:
            log(u'\n=== '+_(u'Eyes/Hair Assigned for NPCs'))
            for srcMod in sorted(mod_npcsFixed):
                log(u'* %s: %d' % (srcMod.s,len(mod_npcsFixed[srcMod])))
        for tweak in self.enabled_tweaks:
            tweak._patchLog(log,tweak.count)
