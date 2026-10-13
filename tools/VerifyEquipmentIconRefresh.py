#!/usr/bin/env python3
"""Combined final-map gate for spirit, equipment and open-slot icons only."""
import argparse
import hashlib
import json
from pathlib import Path
from BuildSpiritSkillIcons import ROOT,build
from BuildEquipmentIconRefresh import MANIFEST
from ReadEquipmentCatalog import catalog,icon_paths
from GenerateTowerTerrainMask import Mpq
from VerifySemanticIconArtifact import load_objects,decode_blp
import VerifySpiritSkillIcons as spirit

EXPECTED_NEW={(1,4):'WindrunnerBanner',(5,4):'ForestSeed',(6,3):'SunderingSeal',(7,4):'CommandHorn',**{(9,q):'WindDrum' for q in range(1,5)}}


def source_check():
    manifest=json.loads(MANIFEST.read_text()); paths=icon_paths()
    for key,stem in EXPECTED_NEW.items():
        spirit.require(paths[key]=='war3mapImported\\BTNTDItem'+stem+'.blp','Wrong equipment mapping '+str(key))
    spirit.require(paths[1,3]==paths[1,2],'Telescope still points to unrelated bow')
    spirit.require(paths[2,3]==paths[2,1],'War axe still points to unrelated badge')
    spirit.require(not spirit.equipment_report()['cross_line_review_needed'],'Different equipment lines still share icons')
    source=(ROOT/'wurst/pets/TDPetUIData.wurst').read_text()
    spirit.require('if action == 14\n\t\treturn importedIcon("TDPetEmptySlot")' in source,'Open slot shares cultivation icon')
    return build(MANIFEST,check=True,expected_pairs=5)


def validate_packed(archive,objects):
    manifest=json.loads(MANIFEST.read_text()); paths=icon_paths(); total=0
    for e in catalog():
        spirit.require(spirit.field(objects['items'][e.rawcode],'iico')==paths[e.line,e.quality],'Wrong final item icon '+e.rawcode)
    for key in ('aart','arar'):
        spirit.require(spirit.field(objects['abilities']['Pm06'],key)=='war3mapImported\\BTNTDPetEmptySlot.blp','Open slot icon mismatch')
    for entry in manifest['assets']:
        for key in ('normal','disabled'):
            path=entry[key];data=archive.extract(path)
            spirit.require(hashlib.sha256(data).hexdigest()==entry[key+'_sha256'],'Wrong packed equipment icon '+path)
            spirit.require(data==(ROOT/'imports'/path.replace('\\','/')).read_bytes(),'Import bytes differ '+path)
            decode_blp(data,path);total+=archive.blocks[archive.block_index(path)][1]
    spirit.require(total<=manifest['max_added_mpq_bytes'],'Equipment MPQ budget exceeded')
    return total


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--map',type=Path);p.add_argument('--baseline-map',type=Path);p.add_argument('--output',type=Path)
    args=p.parse_args();result,n=spirit.source_check();result['equipment_asset_build']=source_check()
    sm=json.loads(spirit.MANIFEST.read_text()); em=json.loads(MANIFEST.read_text())
    if args.baseline_map:result['baseline_audit']=spirit.global_packed_audit(Mpq(args.baseline_map.read_bytes()),n)
    if args.map:
        archive=Mpq(args.map.read_bytes());objects=load_objects(archive)
        result['packed']=spirit.validate_packed(archive,objects,n,sm)
        result['packed']['equipment_added_mpq_bytes']=validate_packed(archive,objects)
        total=result['packed']['actual_added_icon_mpq_bytes']+result['packed']['equipment_added_mpq_bytes']
        spirit.require(total<=em['max_combined_added_mpq_bytes'],'Combined MPQ icon budget exceeded')
        result['packed']['combined_added_mpq_bytes']=total
        result['packed']['combined_budget']=em['max_combined_added_mpq_bytes']
        result['final_audit']=spirit.global_packed_audit(archive,n)
        spirit.require(not result['final_audit']['tower_command_or_upgrade_duplicate_groups'],'Tower command conflict')
        spirit.require(not result['final_audit']['equipment']['cross_line_review_needed'],'Packed equipment conflict')
        if args.baseline_map:
            baseline=Mpq(args.baseline_map.read_bytes())
            result['delta']=spirit.verify_delta(baseline,archive,n,sm,em)
            result['map_byte_delta']=args.map.stat().st_size-args.baseline_map.stat().st_size
            spirit.require(result['map_byte_delta']<=em['max_combined_added_mpq_bytes'],'Full map growth exceeded 320KiB')
    else:result['packed_verification']='NOT RUN: no new map supplied'
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:args.output.write_text(text+'\n')
    print(text)

if __name__=='__main__':main()
