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
"""This module houses preservers. A preserver is an import patcher that simply
carries forward changes from the last tagged plugin. The goal is to eventually
absorb all of them under the _APreserver base class."""
from collections import defaultdict, Counter
from itertools import chain
from operator import attrgetter
# Internal
from ._shared import _ANamesPatcher, _ANpcFacePatcher, _ASpellsPatcher, \
    _AStatsPatcher
from .base import ImportPatcher
from .. import getPatchesPath
from ... import bush, load_order, parsers
from ...bolt import deprint, floats_equal
from ...brec import MreRecord
from ...exception import ModSigMismatchError
from ...mod_files import ModFile, LoadFactory

#------------------------------------------------------------------------------
# cache attrgetter objects
class _AttrGettersCache(dict):
    def __missing__(self, attr_name):
        return self.setdefault(attr_name, attrgetter(attr_name))

_attrgetters = _AttrGettersCache()

# noinspection PyDefaultArgument
def _setattr_deep(obj, attr, value, __attrgetters=_attrgetters,
                  __split_cache={}):
    try:
        parent_attr, leaf_attr = __split_cache[attr]
    except KeyError:
        dot_dex = attr.rfind(u'.')
        if dot_dex > 0:
            parent_attr = attr[:dot_dex]
            leaf_attr = attr[dot_dex + 1:]
        else:
            parent_attr = u''
            leaf_attr = attr
        __split_cache[attr] = parent_attr, leaf_attr
    setattr(__attrgetters[parent_attr](obj) if parent_attr else obj,
        leaf_attr, value)

#------------------------------------------------------------------------------
class _APreserver(ImportPatcher):
    """Fairly mature base class for preservers. Some parts could (read should)
    be moved to ImportPatcher and used to eliminate duplication with _AMerger.

    :type rec_attrs: dict[bytes, tuple] | dict[bytes, dict[unicode, tuple]]"""
    rec_attrs = {}
    long_types = None
    # Record attributes that are FormIDs. These will be checked to see if their
    # FormID is valid before being imported
    ##: set for more patchers?
    _fid_rec_attrs = {}
    # True if this importer is a multi-tag importer. That means its rec_attrs
    # must map record signatures to dicts mapping the tags to a tuple of the
    # subrecords to import, instead of just mapping the record signatures
    # directly to the tuples
    _multi_tag = False
    _csv_parser = None
    # A bash tag to force the import of all relevant data from a tagged mod,
    # without it being checked against the masters first. None means no such
    # tag exists for this patcher
    _force_full_import_tag = None

    def __init__(self, p_name, p_file, p_sources):
        super(_APreserver, self).__init__(p_name, p_file, p_sources)
        #--(attribute-> value) dicts keyed by long fid.
        self.id_data = defaultdict(dict)
        self.srcClasses = set() #--Record classes actually provided by src
        # mods/files.
        self.classestemp = set()
        #--Type Fields
        self._fid_rec_attrs_class = (defaultdict(dict) if self._multi_tag
                                     else defaultdict(tuple))
        self._fid_rec_attrs_class.update({MreRecord.type_class[r]: a for r, a
                                          in self._fid_rec_attrs.iteritems()})
        # We want FormID attrs in the full recAttrs as well. They're only
        # separate for checking before we import
        if self._multi_tag: ##: This is hideous
            def collect_attrs(r, tag_dict):
                return {t: a + self._fid_rec_attrs.get(r, {}).get(t, ())
                        for t, a in tag_dict.iteritems()}
        else:
            def collect_attrs(r, a):
                return a + self._fid_rec_attrs.get(r, ())
        self.recAttrs_class = {MreRecord.type_class[r]: collect_attrs(r, a)
                               for r, a in self.rec_attrs.iteritems()}
        # Check if we need to use _setattr_deep to set attributes
        if self._multi_tag:
            all_attrs = chain.from_iterable(
                v for d in self.recAttrs_class.itervalues()
                for v in d.itervalues())
        else:
            all_attrs = chain.from_iterable(self.recAttrs_class.itervalues())
        self._deep_attrs = any(u'.' in a for a in all_attrs)
        #--Needs Longs
        self.longTypes = set(self.__class__.long_types or self.rec_attrs)
        # Split srcs based on CSV extension ##: move somewhere else?
        self.csv_srcs = [s for s in p_sources if s.cext == u'.csv']
        self.srcs = [s for s in p_sources if s.cext != u'.csv']

    # CSV helpers - holding out hope for inf-312-parser-abc
    def _parse_csv_sources(self, progress):
        """Parses CSV files. Only called if _csv_parser is set. Override as
        needed and call _process_csv_sources until parser ABC is done."""
        parser_instance = self._csv_parser(aliases=self.patchFile.aliases)
        for src_path in self.csv_srcs:
            try:
                parser_instance.readFromText(getPatchesPath(src_path))
            except OSError:
                deprint(u'%s is no longer in patches set' % src_path,
                    traceback=True)
            except UnicodeError:
                deprint(u'%s is not saved in UTF-8 format' % src_path,
                    traceback=True)
            progress.plus()
        return parser_instance

    def _process_csv_sources(self, parsed_sources):
        """Call from an override of _parse_csv_sources. Applies changes parsed
        from the CSV sources to this patcher's internal data structures."""
        # Filter out any entries that don't actually have data or don't
        # actually exist (for this game at least)
        filtered_dict = {k: v for k, v in parsed_sources.iteritems()
                         if k and k in MreRecord.type_class}
        self.srcClasses.update(MreRecord.type_class[x] for x in filtered_dict)
        for src_data in filtered_dict.itervalues():
            self.id_data.update(src_data)

    def getReadClasses(self):
        return tuple(
            x.rec_sig for x in self.srcClasses) if self.isActive else ()

    def getWriteClasses(self):
        return self.getReadClasses()

    # noinspection PyDefaultArgument
    def _init_data_loop(self, mapper, recClass, srcFile, srcMod, temp_id_data,
                        __attrgetters=_attrgetters):
        recAttrs = self.recAttrs_class[recClass]
        fid_attrs = self._fid_rec_attrs_class[recClass]
        loaded_mods = self.patchFile.loadSet
        if self._multi_tag:
            # For multi-tag importers, we need to look up the applied bash tags
            # and use those to find all applicable attributes
            mod_tags = srcFile.fileInfo.getBashTags()
            recAttrs = set(chain.from_iterable(
                attrs for t, attrs in recAttrs.iteritems() if t in mod_tags))
            fid_attrs = set(chain.from_iterable(
                attrs for t, attrs in fid_attrs.iteritems() if t in mod_tags))
        for record in srcFile.tops[recClass.rec_sig].iter_filtered_records(
                self.getReadClasses()):
            fid = mapper(record.fid)
            # If we have FormID attributes, check those before importing
            if fid_attrs:
                fid_attr_values = [__attrgetters[a](record) for a in fid_attrs]
                if any(f and (f[0] is None or f[0] not in loaded_mods) for f
                       in fid_attr_values):
                    # Ignore the record. Another option would be to just ignore
                    # the attr_fidvalue result
                    self.patchFile.patcher_mod_skipcount[
                        self._patcher_name][srcMod] += 1
                    continue
            temp_id_data[fid] = {attr: __attrgetters[attr](record) for attr in
                                 recAttrs}

    # noinspection PyDefaultArgument
    def initData(self, progress, __attrgetters=_attrgetters):
        """Common initData pattern.
        Used in KFFZPatcher, DeathItemPatcher, SoundPatcher, ImportScripts,
        WeaponModsPatcher, ActorImporter.
        Adding _init_data_loop absorbed GraphicsPatcher also.
        """
        if not self.isActive: return
        id_data = self.id_data
        loadFactory = LoadFactory(False, *self.recAttrs_class.keys())
        longTypes = self.longTypes & {x.rec_sig for x in self.recAttrs_class}
        progress.setFull(len(self.srcs) + len(self.csv_srcs))
        cachedMasters = {}
        minfs = self.patchFile.p_file_minfos
        for index,srcMod in enumerate(self.srcs):
            temp_id_data = {}
            if srcMod not in minfs: continue
            srcInfo = minfs[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            masters = srcInfo.get_masters()
            srcFile.load(do_unpack=True)
            srcFile.convertToLongFids(longTypes)
            mapper = srcFile.getLongMapper()
            for recClass in self.recAttrs_class:
                if recClass.rec_sig not in srcFile.tops: continue
                self.srcClasses.add(recClass)
                self.classestemp.add(recClass)
                self._init_data_loop(mapper, recClass, srcFile, srcMod,
                                     temp_id_data)
            if (self._force_full_import_tag and
                    self._force_full_import_tag in srcInfo.getBashTags()):
                # We want to force-import - copy the temp data without
                # filtering by masters, then move on to the next mod
                id_data.update(temp_id_data)
                continue
            for master in masters:
                if master not in minfs: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = minfs[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    masterFile.convertToLongFids(longTypes)
                    cachedMasters[master] = masterFile
                mapper = masterFile.getLongMapper()
                for recClass in self.recAttrs_class:
                    if recClass.rec_sig not in masterFile.tops: continue
                    if recClass not in self.classestemp: continue
                    for record in masterFile.tops[
                        recClass.rec_sig].iter_filtered_records(
                        self.getReadClasses()): # ugh, looks hideous...
                        fid = mapper(record.fid)
                        if fid not in temp_id_data: continue
                        for attr, value in temp_id_data[fid].iteritems():
                            try:
                                if value == __attrgetters[attr](record):
                                    continue
                                else:
                                    id_data[fid][attr] = value
                            except AttributeError:
                                raise ModSigMismatchError(master, record)
            progress.plus()
        if self._csv_parser:
            self._parse_csv_sources(progress)
        self.longTypes &= {x.rec_sig for x in self.srcClasses}
        self.isActive = bool(self.srcClasses)

    # noinspection PyDefaultArgument
    def scanModFile(self, modFile, progress, __attrgetters=_attrgetters):
        """Identical scanModFile() pattern of :

            GraphicsPatcher, KFFZPatcher, DeathItemPatcher, ImportScripts,
            SoundPatcher, DestructiblePatcher, ActorImporter, WeaponModsPatcher
        """
        id_data = self.id_data
        mapper = modFile.getLongMapper()
        if self.longTypes:
            modFile.convertToLongFids(self.longTypes)
        for recClass in self.srcClasses:
            if recClass.rec_sig not in modFile.tops: continue
            patchBlock = getattr(self.patchFile,
                recClass.rec_sig.decode(u'ascii'))
            # Records that have been copied into the BP once will automatically
            # be updated by update_patch_records_from_mod/mergeModFile
            copied_records = patchBlock.id_records
            for record in modFile.tops[recClass.rec_sig].iter_filtered_records(
                self.getReadClasses()):
                fid = record.fid
                if not record.longFids: fid = mapper(fid)
                # Skip if we've already copied this record or if we're not
                # interested in it
                if fid in copied_records or fid not in id_data: continue
                for attr, value in id_data[fid].iteritems():
                    if __attrgetters[attr](record) != value:
                        patchBlock.setRecord(record.getTypeCopy(mapper))
                        break

    # noinspection PyDefaultArgument
    def _inner_loop(self, keep, records, top_mod_rec, type_count,
                    __attrgetters=_attrgetters):
        """Most common pattern for the internal buildPatch() loop.

        In:
            KFFZPatcher, DeathItemPatcher, ImportScripts, SoundPatcher
        """
        loop_setattr = _setattr_deep if self._deep_attrs else setattr
        id_data = self.id_data
        for record in records:
            rec_fid = record.fid
            if rec_fid not in id_data: continue
            for attr, value in id_data[rec_fid].iteritems():
                if __attrgetters[attr](record) != value: break
            else: continue
            for attr, value in id_data[rec_fid].iteritems():
                loop_setattr(record, attr, value)
            keep(rec_fid)
            type_count[top_mod_rec] += 1

    def buildPatch(self, log, progress, types=None):
        """Common buildPatch() pattern of:

            GraphicsPatcher, ActorImporter, KFFZPatcher, DeathItemPatcher,
            ImportScripts, SoundPatcher, DestructiblePatcher
        Consists of a type selection loop which could be rewritten to support
        more patchers (maybe using filter()) and an inner loop that should be
        provided by a patcher specific, _inner_loop() method.
        Adding `types` parameter absorbed ImportRelations and ImportFactions.
        """
        if not self.isActive: return
        modFileTops = self.patchFile.tops
        keep = self.patchFile.getKeeper()
        type_count = Counter()
        types = filter(modFileTops.__contains__,
            types if types else (x.rec_sig for x in self.srcClasses))
        for top_mod_rec in types:
            records = modFileTops[top_mod_rec].iter_filtered_records(
                self.getReadClasses(), include_ignored=True)
            self._inner_loop(keep, records, top_mod_rec, type_count)
        self.id_data.clear() # cleanup to save memory
        # Log
        self._patchLog(log, type_count)

    def _srcMods(self,log):
        log(self.__class__.srcsHeader)
        all_srcs = self.srcs + self.csv_srcs
        if not all_srcs:
            log(u". ~~%s~~" % _(u'None'))
        else:
            for srcFile in all_srcs:
                log(u"* " +srcFile.s)

#------------------------------------------------------------------------------
# Absorbed patchers -----------------------------------------------------------
#------------------------------------------------------------------------------
class ActorImporter(_APreserver):
    rec_attrs = bush.game.actor_importer_attrs
    _multi_tag = True

#------------------------------------------------------------------------------
class DeathItemPatcher(_APreserver):
    rec_attrs = {x: ('deathItem',) for x in bush.game.actor_types}

#------------------------------------------------------------------------------
class DestructiblePatcher(_APreserver):
    """Merges changes to destructible records for Fallout3/FalloutNV."""
    # All destructibles may contain FIDs, so let longTypes be set automatically
    rec_attrs = {x: ('destructible',) for x in bush.game.destructible_types}

#------------------------------------------------------------------------------
class ImportEffectsStats(_APreserver):
    """Preserves changes to MGEF stats."""
    rec_attrs = {b'MGEF': bush.game.mgef_stats_attrs}

#------------------------------------------------------------------------------
class ImportEnchantmentStats(_APreserver):
    """Preserves changes to ENCH stats."""
    rec_attrs = {b'ENCH': bush.game.ench_stats_attrs}

#------------------------------------------------------------------------------
class ImportFactions(_APreserver):
    logMsg = u'\n=== ' + _(u'Refactioned Actors')
    srcsHeader = u'=== ' + _(u'Source Mods/Files')
    rec_attrs = {x: (u'factions',) for x in bush.game.actor_types}
    _csv_parser = parsers.ActorFactions

    def _parse_csv_sources(self, progress):
        fact_parser = super(ImportFactions, self)._parse_csv_sources(progress)
        # Turn the faction lists into lists of MelObjects
        def make_obj(csv_rsig, csv_obj):
            obj_faction, obj_rank = csv_obj
            ret_obj = MreRecord.type_class[csv_rsig].getDefault(u'factions')
            ret_obj.faction = obj_faction
            ret_obj.rank = obj_rank
            return ret_obj
        self._process_csv_sources(
            {r: {f: {u'factions': [make_obj(r, o) for o in a]}
                 for f, a in d.iteritems()}
             for r, d in fact_parser.type_id_factions.iteritems()})

#------------------------------------------------------------------------------
class ImportScripts(_APreserver):
    rec_attrs = {x: ('script',) for x in bush.game.scripts_types}

#------------------------------------------------------------------------------
class KeywordsImporter(_APreserver):
    rec_attrs = {x: ('keywords',) for x in bush.game.keywords_types}
    # Keywords are all fids, so default to long_types == rec_attrs

#------------------------------------------------------------------------------
class KFFZPatcher(_APreserver):
    rec_attrs = {x: ('animations',) for x in bush.game.actor_types}

#------------------------------------------------------------------------------
class NamesPatcher(_ANamesPatcher, _APreserver):
    rec_attrs = {x: (u'full',) for x in bush.game.namesTypes}
    _csv_parser = parsers.FullNames

    def _parse_csv_sources(self, progress):
        full_parser = super(NamesPatcher, self)._parse_csv_sources(progress)
        # Discard the Editor ID and turn the tuples into dictionaries
        self._process_csv_sources(
            {r: {f: {u'full': a[1]} for f, a in d.iteritems()}
             for r, d in full_parser.type_id_name.iteritems()})

#------------------------------------------------------------------------------
class NpcFacePatcher(_ANpcFacePatcher, _APreserver):
    logMsg = u'\n=== '+_(u'Faces Patched')
    rec_attrs = {b'NPC_': {
        u'NPC.Eyes': (),
        u'NPC.FaceGen': (u'fggs_p', u'fgga_p', u'fgts_p'),
        u'NPC.Hair': (u'hairLength', u'hairRed', u'hairBlue', u'hairGreen'),
        u'NpcFacesForceFullImport': (u'fggs_p', u'fgga_p', u'fgts_p',
                                     u'hairLength', u'hairRed', u'hairBlue',
                                     u'hairGreen'),
    }}
    _fid_rec_attrs = {b'NPC_': {
        u'NPC.Eyes': (u'eye',),
        u'NPC.FaceGen': (),
        u'NPC.Hair': (u'hair',),
        u'NpcFacesForceFullImport': (u'eye', u'hair'),
    }}
    _multi_tag = True
    _force_full_import_tag = u'NpcFacesForceFullImport'

#------------------------------------------------------------------------------
class ObjectBoundsImporter(_APreserver):
    rec_attrs = {x: ('bounds',) for x in bush.game.object_bounds_types}
    long_types = () # OBND never has fids

#------------------------------------------------------------------------------
class SoundPatcher(_APreserver):
    """Imports sounds from source mods into patch."""
    rec_attrs = bush.game.soundsTypes
    long_types = bush.game.soundsLongsTypes

#------------------------------------------------------------------------------
class SpellsPatcher(_ASpellsPatcher, _APreserver):
    logMsg = u'\n=== ' + _(u'Modified SPEL Stats')
    srcsHeader = u'=== ' + _(u'Source Mods/Files')
    rec_attrs = {b'SPEL': bush.game.spell_stats_attrs}
    _csv_parser = parsers.SpellRecords

    def _parse_csv_sources(self, progress):
        spel_parser = super(SpellsPatcher, self)._parse_csv_sources(progress)
        # Add attribute names to the values
        self._process_csv_sources(
            {b'SPEL': {f: {a: v for a, v in zip(self.rec_attrs[b'SPEL'], l)}
                       for f, l in spel_parser.fid_stats.iteritems()}})

#------------------------------------------------------------------------------
class StatsPatcher(_AStatsPatcher, _APreserver):
    # Don't patch Editor IDs - those are only in statsTypes for the
    # Export/Import links
    rec_attrs = {r: tuple(x for x in a if x != u'eid')
                 for r, a in bush.game.statsTypes.iteritems()}
    _csv_parser = parsers.ItemStats

    def _parse_csv_sources(self, progress):
        stat_parser = super(StatsPatcher, self)._parse_csv_sources(progress)
        # See rec_attrs above for an explanation of the Editor ID problem
        for src_attrs in stat_parser.class_fid_attr_value.itervalues():
            for attr_values in src_attrs.itervalues():
                del attr_values[u'eid']
        self._process_csv_sources(stat_parser.class_fid_attr_value)

#------------------------------------------------------------------------------
class TextImporter(_APreserver):
    rec_attrs = bush.game.text_types
    long_types = bush.game.text_long_types

#------------------------------------------------------------------------------
# TODO(inf) Currently FNV-only, but don't move to game/falloutnv/patcher yet -
#  this could potentially be refactored and reused for FO4's modifications
class WeaponModsPatcher(_APreserver):
    """Merge changes to weapon modifications for FalloutNV."""
    scanOrder = 27
    editOrder = 27
    rec_attrs = {b'WEAP': (
        u'modelWithMods', u'firstPersonModelWithMods', u'weaponMods',
        u'soundMod1Shoot3Ds', u'soundMod1Shoot2D', u'effectMod1',
        u'effectMod2', u'effectMod3', u'valueAMod1', u'valueAMod2',
        u'valueAMod3', u'valueBMod1', u'valueBMod2', u'valueBMod3',
        u'reloadAnimationMod', u'vatsModReqiured', u'scopeModel',
        u'dnamFlags1.hasScope', u'dnamFlags2.scopeFromMod')}

#------------------------------------------------------------------------------
# Patchers to absorb ----------------------------------------------------------
#------------------------------------------------------------------------------
##: absorbing this one will be hard - hint: getActiveRecords only exists on
# MobObjects, iter_records works for all Mob* classes, so attack that part of
# _SimpleImporter
class CellImporter(ImportPatcher):
    logMsg = u'\n=== ' + _(u'Cells/Worlds Patched')
    _read_write_records = ('CELL', 'WRLD')

    def __init__(self, p_name, p_file, p_sources):
        super(CellImporter, self).__init__(p_name, p_file, p_sources)
        self.cellData = defaultdict(dict)
        # TODO: docs: recAttrs vs tag_attrs - extra in PBash:
        # 'unused1','unused2','unused3'
        self.recAttrs = bush.game.cellRecAttrs # dict[unicode, tuple[str]]
        self.recFlags = bush.game.cellRecFlags # dict[unicode, str]

    def initData(self,progress):
        """Get cells from source files."""
        if not self.isActive: return
        cellData = self.cellData
        def importCellBlockData(cellBlock):
            """
            Add attribute values from source mods to a temporary cache.
            These are used to filter for required records by formID and
            to update the attribute values taken from the master files
            when creating cell_data.
            """
            if not cellBlock.cell.flags1.ignored:
                fid = cellBlock.cell.fid
                for attr in attrs:
                    tempCellData[fid][attr] = cellBlock.cell.__getattribute__(
                        attr)
                for flg_ in flgs_:
                    tempCellData[fid + ('flags',)][
                        flg_] = cellBlock.cell.flags.__getattr__(flg_)
        def checkMasterCellBlockData(cellBlock):
            """
            Add attribute values from record(s) in master file(s).
            Only adds records where a matching formID is found in temp
            cell data.
            The attribute values in temp cell data are then used to
            update these records where the value is different.
            """
            if not cellBlock.cell.flags1.ignored:
                rec_fid = cellBlock.cell.fid
                if rec_fid not in tempCellData: return
                for attr in attrs:
                    master_attr = cellBlock.cell.__getattribute__(attr)
                    if tempCellData[rec_fid][attr] != master_attr:
                        cellData[rec_fid][attr] = tempCellData[rec_fid][attr]
                for flg_ in flgs_:
                    master_flag = cellBlock.cell.flags.__getattr__(flg_)
                    if tempCellData[rec_fid + ('flags',)][flg_] != master_flag:
                        cellData[rec_fid + ('flags',)][flg_] = \
                            tempCellData[rec_fid + ('flags',)][flg_]
        loadFactory = LoadFactory(False,MreRecord.type_class['CELL'],
                                        MreRecord.type_class['WRLD'])
        progress.setFull(len(self.srcs))
        cachedMasters = {}
        minfs = self.patchFile.p_file_minfos
        for srcMod in self.srcs:
            if srcMod not in minfs: continue
            # tempCellData maps long fids for cells in srcMod to dicts of
            # (attributes (among attrs) -> their values for this mod). It is
            # used to update cellData with cells that change those attributes'
            # values from the value in any of srcMod's masters.
            tempCellData = defaultdict(dict)
            srcInfo = minfs[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            srcFile.convertToLongFids(('CELL','WRLD'))
            cachedMasters[srcMod] = srcFile
            masters = srcInfo.get_masters()
            bashTags = srcInfo.getBashTags()
            # print bashTags
            tags = bashTags & set(self.recAttrs)
            if not tags: continue
            attrs = set(chain.from_iterable(
                self.recAttrs[bashKey] for bashKey in tags))
            flgs_ = tuple(self.recFlags[bashKey] for bashKey in tags if
                          self.recFlags[bashKey] != u'')
            if 'CELL' in srcFile.tops:
                for cellBlock in srcFile.CELL.cellBlocks:
                    importCellBlockData(cellBlock)
            if 'WRLD' in srcFile.tops:
                for worldBlock in srcFile.WRLD.worldBlocks:
                    for cellBlock in worldBlock.cellBlocks:
                        importCellBlockData(cellBlock)
                    if worldBlock.worldCellBlock:
                        importCellBlockData(worldBlock.worldCellBlock)
            for master in masters:
                if master not in minfs: continue # or break filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = minfs[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    masterFile.convertToLongFids(('CELL','WRLD'))
                    cachedMasters[master] = masterFile
                if 'CELL' in masterFile.tops:
                    for cellBlock in masterFile.CELL.cellBlocks:
                        checkMasterCellBlockData(cellBlock)
                if 'WRLD' in masterFile.tops:
                    for worldBlock in masterFile.WRLD.worldBlocks:
                        for cellBlock in worldBlock.cellBlocks:
                            checkMasterCellBlockData(cellBlock)
                        if worldBlock.worldCellBlock:
                            checkMasterCellBlockData(worldBlock.worldCellBlock)
            tempCellData = {}
            progress.plus()

    def scanModFile(self, modFile, progress): # scanModFile0
        """Add lists from modFile."""
        if not self.isActive or (
                'CELL' not in modFile.tops and 'WRLD' not in modFile.tops):
            return
        cellData = self.cellData
        patchCells = self.patchFile.CELL
        patchWorlds = self.patchFile.WRLD
        modFile.convertToLongFids(('CELL','WRLD'))
        if 'CELL' in modFile.tops:
            for cellBlock in modFile.CELL.cellBlocks:
                if cellBlock.cell.fid in cellData:
                    patchCells.setCell(cellBlock.cell)
        if 'WRLD' in modFile.tops:
            for worldBlock in modFile.WRLD.worldBlocks:
                patchWorlds.setWorld(worldBlock.world)
                curr_pworld = patchWorlds.id_worldBlocks[worldBlock.world.fid]
                for cellBlock in worldBlock.cellBlocks:
                    if cellBlock.cell.fid in cellData:
                        curr_pworld.setCell(cellBlock.cell)
                pers_cell_block = worldBlock.worldCellBlock
                if pers_cell_block and pers_cell_block.cell.fid in cellData:
                    curr_pworld.worldCellBlock = pers_cell_block

    def buildPatch(self,log,progress): # buildPatch0
        """Adds merged lists to patchfile."""
        c_float_attrs = bush.game.cell_float_attrs
        def handlePatchCellBlock(patchCellBlock):
            """This function checks if an attribute or flag in CellData has
            a value which is different to the corresponding value in the
            bash patch file.
            The Patch file will contain the last corresponding record
            found when it is created regardless of tags.
            If the CellData value is different, then the value is copied
            to the bash patch, and the cell is flagged as modified.
            Modified cell Blocks are kept, the other are discarded."""
            modified = False
            patch_cell_fid = patchCellBlock.cell.fid
            patch_cell_get = patchCellBlock.cell.__getattribute__
            patch_cell_set = patchCellBlock.cell.__setattr__
            for attr,value in cellData[patch_cell_fid].iteritems():
                curr_value = patch_cell_get(attr)
                if attr == u'regions':
                    if set(value).difference(set(curr_value)):
                        patch_cell_set(attr, value)
                        modified = True
                # bolt.Flags-backed attributes need special comparison logic,
                # since flags can have nonsense values outside of the actual
                # flags. ##: if we ever end up having more flags attrs, this
                # should become a set, probably per-game
                elif attr == u'land_flags':
                    if value.getTrueAttrs() != curr_value.getTrueAttrs():
                        patch_cell_set(attr, value)
                        modified = True
                elif attr in c_float_attrs:
                    if not floats_equal(value, curr_value):
                        patch_cell_set(attr, value)
                        modified = True
                else:
                    if value != curr_value:
                        patch_cell_set(attr, value)
                        modified = True
            patch_get_flag = patchCellBlock.cell.flags.__getattr__
            patch_set_flag = patchCellBlock.cell.flags.__setattr__
            for flag, value in cellData[
                patch_cell_fid + (u'flags',)].iteritems():
                if patch_get_flag(flag) != value:
                    patch_set_flag(flag, value)
                    modified = True
            if modified:
                patchCellBlock.cell.setChanged()
                keep(patch_cell_fid)
            return modified
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        cellData, count = self.cellData, Counter()
        for cellBlock in self.patchFile.CELL.cellBlocks:
            cell_fid = cellBlock.cell.fid
            if cell_fid in cellData and handlePatchCellBlock(cellBlock):
                count[cell_fid[0]] += 1
        for worldBlock in self.patchFile.WRLD.worldBlocks:
            keepWorld = False
            for cellBlock in worldBlock.cellBlocks:
                cell_fid = cellBlock.cell.fid
                if cell_fid in cellData and handlePatchCellBlock(cellBlock):
                    count[cell_fid[0]] += 1
                    keepWorld = True
            if worldBlock.worldCellBlock:
                cell_fid = worldBlock.worldCellBlock.cell.fid
                if cell_fid in cellData and handlePatchCellBlock(
                        worldBlock.worldCellBlock):
                    count[cell_fid[0]] += 1
                    keepWorld = True
            if keepWorld:
                keep(worldBlock.world.fid)
        self.cellData.clear()
        self._patchLog(log, count)

    def _plog(self,log,count): # type 1 but for logMsg % sum(count.values())...
        log(self.__class__.logMsg)
        for srcMod in load_order.get_ordered(count.keys()):
            log(u'* %s: %d' % (srcMod.s,count[srcMod]))

#------------------------------------------------------------------------------
class GraphicsPatcher(_APreserver):
    rec_attrs = bush.game.graphicsTypes
    _fid_rec_attrs = bush.game.graphicsFidTypes

    def _inner_loop(self, keep, records, top_mod_rec, type_count,
                    __attrgetters=_attrgetters):
        id_data = self.id_data
        for record in records:
            fid = record.fid
            if fid not in id_data: continue
            for attr, value in id_data[fid].iteritems():
                rec_attr = __attrgetters[attr](record)
                if isinstance(rec_attr,
                              basestring) and isinstance(value, basestring):
                    if rec_attr.lower() != value.lower():
                        break
                    continue
                elif attr in bush.game.graphicsModelAttrs:
                    try:
                        if rec_attr.modPath.lower() != value.modPath.lower():
                            break
                        continue
                    except: break  # assume they are not equal (ie they
                        # aren't __both__ NONE)
                if rec_attr != value: break
            else: continue
            for attr, value in id_data[fid].iteritems():
                setattr(record, attr, value)
            keep(fid)
            type_count[top_mod_rec] += 1
