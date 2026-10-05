"""Dump vanilla PBTable candidates (base = pakchunk16, patch = pakchunk26) to work/vanilla/."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pak  # noqa: E402

GAME_PAKS = r"C:\Program Files (x86)\Steam\steamapps\common\BlackMythWukong\b1\Content\Paks"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "work", "vanilla")

TARGETS = [
    "00Main/PBTable/Runtime/TalentSDesc.data",
    "00Main/PBTable/Runtime/TalentRankDesc.data",
    "00Main/PBTable/Runtime/NewGamePlusDesc.data",
    "00Main/PBTable/NoneRuntime/FUStTalentLvUpCfgDesc.data",
    "00Main/PBTable/NoneRuntime/FUStTalentDisplayDesc.data",
    "00Main/PBTable/NoneRuntime/FUStBuffDesc-Talent.data",
    "00Main/PBTable/NoneRuntime/FUStSkillEffectDesc-Talent.data",
]

SOURCES = [("base", "pakchunk16-Windows.pak"), ("patch", "pakchunk26-Windows_P.pak")]

for tag, name in SOURCES:
    p = pak.Pak(os.path.join(GAME_PAKS, name))
    for rel in TARGETS:
        if rel not in p.files:
            print(f"  [{tag}] MISSING {rel}")
            continue
        data = p.read(rel)
        dst = os.path.join(OUT, tag, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(data)
        print(f"  [{tag}] {rel} -> {len(data)} bytes")
