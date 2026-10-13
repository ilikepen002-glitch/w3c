#!/usr/bin/env python3
"""Read-only source/resource and actual-map gate for the 43 spirit icon identities.

With --map, verifies the final packed paths, imported bytes and measured MPQ
budget. With --baseline-map, proves that only approved ability icon fields and
50 icon resources changed, preserving every other object field and asset.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path
import struct
from BuildSpiritSkillIcons import MANIFEST, ROOT, build
from GenerateTowerTerrainMask import Mpq
from ReadEquipmentCatalog import catalog, icon_paths
from VerifyPetUIArtifact import phase_one_catalog
from VerifySemanticIconArtifact import load_objects
from VerifyTowerUpgradeArtifact import BRANCH_ICONS, EXPECTED_TOWERS, EVOLUTION_REPLACEMENTS, HIDDEN


def require(ok, message):
    if not ok: raise ValueError(message)


def field(obj, name):
    value = obj.fields.get((name, 0, 0))
    return value.value if value else ''


def normalized(path):
    return path.replace('/', '\\').casefold()


def skill_paths(n):
    return {i: n['tdPetSkillIconPath'](i, False) for i in range(n['TD_PET_SKILL_COUNT']) if n['tdPetSkillDefined'](i)}


def expected_bindings(n):
    out={}
    count=n['TD_PET_SKILL_COUNT']
    for skill in skill_paths(n):
        for position in range(2):
            out[f'Ps{position * count + skill:02X}']=n['tdPetSkillIconPath'](skill, False)
        for slot in range(4):
            if n['tdPetSkillAllowed'](skill, slot, False, False):
                out[f's{slot}{skill:02X}']=n['tdPetSkillIconPath'](skill, False)
                if slot >= 2:out[f's{slot}{skill + count:02X}']=n['tdPetSkillIconPath'](skill, True)
    return out


def collisions(records):
    grouped=collections.defaultdict(list)
    for record in records:grouped[normalized(record['path'])].append(record)
    return [{'path': path, 'uses': uses} for path,uses in sorted(grouped.items()) if len(uses)>1]


def equipment_report(objects=None):
    icons=icon_paths()
    records=[{'rawcode':e.rawcode,'name':e.name,'line':e.line,'quality':e.quality,'path':field(objects['items'][e.rawcode],'iico') if objects else icons[e.line,e.quality]} for e in catalog()]
    groups=collisions(records)
    return {'records':records, 'same_line_quality_reuse':[g for g in groups if len({v['line'] for v in g['uses']})==1],
            'cross_line_review_needed':[g for g in groups if len({v['line'] for v in g['uses']})>1]}


def source_check():
    n=phase_one_catalog(); paths=skill_paths(n)
    require(len(paths)==43,'Expected 43 implemented identities')
    require(len(set(map(normalized,paths.values())))==43,'Different spirit identities share an icon')
    manifest=json.loads(MANIFEST.read_text()); imported={e['skill_id']:e for e in manifest['assets']}
    require(len(imported)==25,'Expected 25 selected originals')
    for skill,path in paths.items():
        name=n['tdPetSkillIconName'](skill)
        disabled=n['tdPetSkillIconPath'](skill,True)
        require(disabled=='ReplaceableTextures\\CommandButtonsDisabled\\DIS'+name+'.blp','Bad DISBTN path')
        if skill in imported:
            require(path==imported[skill]['normal'] and disabled==imported[skill]['disabled'],'Manifest/mapping mismatch')
        else:
            require(path=='ReplaceableTextures\\CommandButtons\\'+name+'.blp','Unverified new native dispatch')
    equipment=equipment_report()
    other_paths={normalized(e['path']) for e in equipment['records']}
    other_paths.update(normalized('ReplaceableTextures\\CommandButtons\\'+x+'.blp') for pair in BRANCH_ICONS.values() for x in pair)
    require(not (set(map(normalized,paths.values()))&other_paths),'Spirit icon collides with equipment or branch')
    source=(ROOT/'wurst/pets/TDPetObjectGen.wurst').read_text()
    require('..setIconNormal(tdPetSkillIconPath(skill, false))' in source,'Preview bypasses shared full-path dispatcher')
    require('..setIconNormal(tdPetSlotIconPath(variant))' in source,'Slots bypass shared dispatcher')
    return {'active_identities':43,'distinct_spirit_paths':43,'custom_pairs':25,'retained_native_paths':18,
            'spirit_equipment_branch_collisions':[], 'asset_build':build(check=True), 'equipment':equipment},n


def validate_packed(archive, objects, n, manifest):
    bindings=expected_bindings(n)
    for raw,path in bindings.items():
        require(raw in objects['abilities'], 'Missing skill object '+raw)
        require(field(objects['abilities'][raw],'aart')==path,'Wrong skill icon '+raw)
    total=0
    for entry in manifest['assets']:
        for key in ('normal','disabled'):
            path=entry[key];data=archive.extract(path)
            require(hashlib.sha256(data).hexdigest()==entry[key+'_sha256'],'Packed icon hash mismatch '+path)
            require(data[:4]==b'BLP1' and struct.unpack_from('<2I',data,12)==(64,64),'Wrong 64px BLP1 icon '+path)
            require(len(data)==12102,'Unexpected palette/alpha/mipmap byte size')
            require(data==(ROOT/'imports'/path.replace('\\','/')).read_bytes(),'Packed/import bytes differ')
            total+=archive.blocks[archive.block_index(path)][1]
    require(total<=manifest['max_added_mpq_bytes'],'Actual MPQ icon budget exceeded')
    return {'ability_icon_bindings':len(bindings),'actual_added_icon_mpq_bytes':total,'max_added_mpq_bytes':manifest['max_added_mpq_bytes']}


def normalized_display_stamp(data):
    # W3I v25: the supported entrypoint stamps map name AND loading title.
    require(struct.unpack_from('<I',data)[0]==25,'Unexpected W3I version')
    spans=[];offset=12
    for _ in range(4):
        end=data.index(b'\0',offset);spans.append((offset,end));offset=end+1
    name=data[slice(*spans[0])].decode('utf-8')
    require(re.fullmatch(r'契灵守卫战 \d{8}-\d{4}-UTC\+8',name) is not None,'Unexpected map name metadata')
    # Camera bounds, complements, size, flags, tileset, loading screen index.
    offset+=32+16+8+4+1+4
    loading=[]
    for _ in range(3):
        end=data.index(b'\0',offset);loading.append((offset,end));offset=end+1
    title=loading[2]
    require(data[slice(*title)]==name.encode('utf-8'),'Map/loading display stamps disagree')
    out=data[:title[0]]+b'<BUILD DISPLAY STAMP>'+data[title[1]:]
    first=spans[0]
    return out[:first[0]]+b'<BUILD DISPLAY STAMP>'+out[first[1]:]


def verify_delta(before,after,n,manifest, equipment_manifest=None):
    require(before.extract('war3map.j')==after.extract('war3map.j'),'Runtime JASS changed in icon-only update')
    old=load_objects(before);new=load_objects(after); bindings=expected_bindings(n)
    modified=[]
    item_bindings={}
    command_bindings={}
    if equipment_manifest:
        icons=icon_paths()
        item_bindings={e.rawcode:icons[e.line,e.quality] for e in catalog()}
        command_bindings={'Pm06':'war3mapImported\\BTNTDPetEmptySlot.blp'}
    for kind in old:
        require(old[kind].keys()==new[kind].keys(),'Object identities changed: '+kind)
        for raw,obj in old[kind].items():
            other=new[kind][raw]
            require(obj.identity==other.identity and obj.fields.keys()==other.fields.keys(),'Object structure changed '+raw)
            for key,value in obj.fields.items():
                if value.raw==other.fields[key].raw:continue
                expected=None
                if kind=='abilities' and raw in bindings and key==('aart',0,0):expected=bindings[raw]
                if kind=='items' and raw in item_bindings and key==('iico',0,0):expected=item_bindings[raw]
                if kind=='abilities' and raw in command_bindings and key in (('aart',0,0),('arar',0,0)):expected=command_bindings[raw]
                require(expected is not None,'Non-icon field changed '+raw+str(key))
                require(other.fields[key].value==expected,'Unexpected replacement icon '+raw)
                modified.append((kind,raw,key))
    expected_changes={raw for raw,path in bindings.items() if field(old['abilities'][raw],'aart')!=path}
    require({raw for kind,raw,key in modified if kind=='abilities' and raw in bindings}==expected_changes,'Missing or extra spirit icon changes')
    for skill,path in skill_paths(n).items():
        if skill not in {e['skill_id'] for e in manifest['assets']}:
            require(field(old['abilities'][f'Ps{skill:02X}'],'aart')==path,'Retained native path was silently changed')
    added={e[k] for e in manifest['assets'] for k in ('normal','disabled')}
    if equipment_manifest:added.update(e[k] for e in equipment_manifest['assets'] for k in ('normal','disabled'))
    old_names=set(before.extract('(listfile)').decode().splitlines());new_names=set(after.extract('(listfile)').decode().splitlines())
    require(new_names-old_names==added and not old_names-new_names,'Unexpected packaged member addition/removal')
    require(normalized_display_stamp(before.extract('war3map.w3i'))==normalized_display_stamp(after.extract('war3map.w3i')),'Non-display W3I metadata changed')
    permitted={'war3map.w3a','war3map.j','war3map.imp','war3map.w3i','(listfile)','(attributes)'}
    if equipment_manifest:permitted.add('war3map.w3t')
    for name in old_names-permitted:
        require(before.extract(name)==after.extract(name),'Unrelated packaged member changed '+name)
    return {'changed_icon_fields':len(modified), 'changed_fields':[list((kind,raw,*key)) for kind,raw,key in modified],'added_icon_resources':len(added),'runtime_jass_byte_identical':True,'object_ids_levels_gameplay_fields_unchanged':True,'models_and_other_assets_byte_identical':True,'w3i_only_expected_build_display_stamp_changed':True}


def global_packed_audit(archive,n):
    objects=load_objects(archive)
    pet_records=[{'skill':i,'name':n['tdPetSkillNameById'](i),'path':field(objects['abilities'][f'Ps{i:02X}'],'aart')} for i in skill_paths(n)]
    command_conflicts=[]
    for uid,attached in EXPECTED_TOWERS.items():
        # Upgrade ability REPLACES its predecessor; they are not co-visible.
        replacements=EVOLUTION_REPLACEMENTS.get(uid,{})
        actual={replacements.get(a,a) for a in attached}|{'AeEV'}
        records=[]
        for raw in actual-HIDDEN:
            obj=objects['abilities'][raw];path=field(obj,'aart')
            if path:records.append({'id':raw,'name':field(obj,'anam'),'path':path})
        unit=objects['units'][uid]
        for raw in field(unit,'uupt').split(','):
            if raw in objects['units']:
                obj=objects['units'][raw];records.append({'id':raw,'name':field(obj,'unam'),'path':field(obj,'uico')})
        for group in collisions(records):command_conflicts.append({'tower':uid,**group})
    return {'spirit_duplicate_groups':collisions(pet_records),'tower_command_or_upgrade_duplicate_groups':command_conflicts,
            'bottom_buff_status_scope':'Native bottom-row aura/status carriers are distinct from command buttons; they are not relabeled by this icon-only change.',
            'equipment':equipment_report(objects)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--map',type=Path);p.add_argument('--baseline-map',type=Path);p.add_argument('--output',type=Path)
    args=p.parse_args();result,n=source_check();manifest=json.loads(MANIFEST.read_text())
    if args.baseline_map: result['baseline_audit']=global_packed_audit(Mpq(args.baseline_map.read_bytes()),n)
    if args.map:
        archive=Mpq(args.map.read_bytes());result['packed']=validate_packed(archive,load_objects(archive),n,manifest)
        result['final_audit']=global_packed_audit(archive,n)
        if args.baseline_map:result['delta']=verify_delta(Mpq(args.baseline_map.read_bytes()),archive,n,manifest)
    else:result['packed_verification']='NOT RUN: no new map supplied'
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:args.output.write_text(text+'\n')
    print(text)

if __name__=='__main__':main()
