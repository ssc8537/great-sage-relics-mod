import sys, os
sys.path.insert(0, 'tools')
import pak

BASE = r'C:\Program Files (x86)\Steam\steamapps\common\BlackMythWukong\b1\Content\Paks'
OUT = r'work\vanilla'

TABLES = [
    'FUStTalentLvUpCfgDesc.data',
    'FUStTalentDisplayDesc.data',
    'TalentRankDesc.data',
    'TalentSDesc.data',
    'NewGamePlusDesc.data',
    'FUStBuffDesc-lz.data',
    'FUStBuffDesc-Item.data',
    'FUStBuffDesc-Talent.data',
    'FUStBuffDispDesc.data',
    'FUStPassiveSkillDesc.data',
    'FUStSkillEffectDesc-Talent.data',
    'FUStSkillEffectDesc-lz.data',
    'EquipAttrDesc.data',
    'ItemDesc.data',
    'PlayerLevelDesc.data',
    'FUStGlobalConfigDesc-DA.data',
]

want26 = [t for t in TABLES]
for chunk in ['pakchunk26-Windows_P.pak', 'pakchunk16-Windows.pak']:
    pk = pak.Pak(os.path.join(BASE, chunk))
    tag = 'patch' if '26' in chunk else 'base'
    for rel in pk.files:
        base = os.path.basename(rel)
        if base in TABLES and rel.endswith('.data'):
            dst = os.path.join(OUT, tag, base)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            data = pk.read(rel)
            open(dst, 'wb').write(data)
            print('%-6s %-40s %8d bytes' % (tag, base, len(data)))
