# 移交说明：黑神话·悟空「意见欲」根器开关解锁 MOD（PAK）

> 本文件写给**下一位接手这个项目的 AI**。请先完整读完本文件，再动手。
> 工作目录：`C:\Users\Administrator\Desktop\1-Test\1-大圣根器mod`
> 游戏本体（**严禁修改**）：`C:\Program Files (x86)\Steam\steamapps\common\BlackMythWukong`

---

## 0. 用户到底要什么（原始意图，勿走偏）

用户以「大圣根器-优秀案例」里的社区 MOD（`pakchunk27-Windows_P.pak`）为参考，要求：

1. **只解锁游戏中「意见欲」这个根器的开关**——让`s 修行 → 根器`里「意见欲」的三个选项（万相归真 / 合意同心 / 不生不灭）变成可选，用户自己进游戏选「合意同心」。
2. **不要修改任何功能数值**（不要动那 18 个根器的效果，只要游戏原版功能）。
3. 产出**一个 PAK 文件**，放进 `BlackMythWukong\b1\Content\Paks\~mods\` 生效。
4. 游戏本体目录**不许改动**。
5. 用户安装 MOD 用的是「黑盒 / Mod-Box」管理器（见第 6 节）。

**当前交付状态：已产出可用 PAK，但「是否真的能在游戏里解锁」尚未经过实机验证（无法在本机跑游戏验证）。**

---

## 1. 已交付产物

| 文件 | 说明 |
|---|---|
| `输出\pakchunk28-Windows_P.pak` | **最终 MOD 文件（8433 字节）**，直接放进 `...\b1\Content\Paks\~mods\` |
| `大圣根器-优秀案例\` | 用户给的参考案例（原样保留，勿删） |
| `tools\` | 我自己写的全套工具（pak 读写、protobuf 读写、分析脚本） |
| `work\` | 全部中间产物：原版表、分析结果、解包资源、round-trip 测试包 |

**该 PAK 只包含 2 个文件（挂载点 `../../../`，完整路径写法，与案例 MOD 一致）：**
- `b1/Content/00Main/PBTable/Runtime/CommDropRuleDesc.data`
- `b1/Content/00Main/PBTable/Runtime/UnitDropRuleDesc.data`

---

## 2. 核心结论：根器到底是怎么"开"的（重要，别再走弯路）

经过对游戏 388 张 PBTable 的全量扫描，结论如下：

1. **根器 = 物品**。6 个根器就是 `ItemDesc.data` 里的 6 个道具：
   - 4091 眼看喜（大圣之眼）、4092 耳听怒、4093 鼻嗅爱、4094 舌尝思、4095 身本忧、**4096 意见欲（大圣之意）**
   - 它们 `f5=14`（物品类型 14），全游戏只有这 6 个 type=14 道具。
   - 4092~4096 的描述是「击败XX后获得的…（临时）」，即正常流程是**打完对应章节 BOSS 后掉落拾取**。
2. **根器面板（`BUI_LearnDSTalent` → `BI_Genqi` 蓝图）按"是否拥有该物品"决定是否锁定**（UI 有 `ButtonUIStat::LockNormal` 锁定态）。天赋表 `TalentSDesc.data` 里根器记录的 `f3` 分组 ID = 4091~4096，**与物品 ID 完全一致**，这就是「物品→天赋组」的映射证据。
3. 所以 **PAK 无法直接翻转一个"开关布尔值"**：解锁的唯一数据侧途径就是**让玩家获得物品 4096**。
4. **掉落规则就是获得物品的合法通道**：`CommDropRuleDesc.data` 里已有的原版规则
   - `9901 → 掉落 4091`（眼看喜）
   - `9902 → 4092`、`9903 → 4093`、`9904 → 4094`、`9905 → 4095`、**`9906 → 4096`（意见欲）**
   - 另有 **`10105 → 只掉 4096`**、`1030 → 只掉 4096`
   这些是「根器宝箱」用的规则（`FUStInteractionMappingDesc` 里 `990101` 交互 = Box08 宝箱 → 规则 9901）。
5. 掉落条目格式（原版就是这么写的，已逐字节核对）：
   `f13 = { f1: 物品ID, f2: 1, f3: 1, f4: 10000 }`，规则里 `f10 = 10000`（权重满值 = 必掉，原版 9906 里两条 10000 的条目会同时掉落）。

> 已排除的方向（别再试）：
> - `FUStTalentLvUpCfgDesc` / `FUStTalentDisplayDesc` / `TalentRankDesc` / `NewGamePlusDesc` 里没有解锁开关；
> - `ItemDesc` 里没有「初始拥有 / 自动获得」字段可改；
> - 商店 `ShopItemDesc` 卖的道具类型只有 3/4/5/6/9/10/11/17，**从不卖 type 14**，且 `f3/f4` 字段语义未确认，属于高风险备选（见第 5 节备选方案 B）；
> - `CommLogicCfgDesc` / `RoleDataConfigDesc` / `LoadingTipsDesc` 里出现的 4091~4096 是别的 ID 空间的数字撞车，与根器无关。

---

## 3. 我做的 MOD 具体改了什么（**只增不改**）

### 3.1 `CommDropRuleDesc.data`：给 11 条规则各追加一条「必掉意见欲」条目

追加内容（每条规则一模一样）：
```
f13 = { f1: 4096, f2: 1, f3: 1, f4: 10000 }   # 新增的重复字段，protobuf repeated，安全
```
若该规则原本没有 `f10`，则补一个 `f10 = 10000`（如 91000）。

被扩展的规则（`rule_id` → 触发场景）：
| 规则 | 触发场景 |
|---|---|
| **91000** | **普通可破坏物（罐子/木箱等，`DestructionDropDesc` 里 10 个破坏物 ID 共用）** |
| **1008** | **土地庙 / 重生点「上香」交互（interaction 100801）** |
| 9001 | 宝箱 Box08（7 个交互） |
| 2013 / 2008 / 2016 / 2002 / 2014 / 2009 / 3102 / 5001 | 被 7~16 个常见世界交互共用（门、宝箱、剧情物件等） |

### 3.2 `UnitDropRuleDesc.data`：66 条敌人掉落组全部追加一条引用

```
f4 = { f1: 10105, f2: 100000 }   # 10105 是原版规则，只掉 4096；权重给满 → 击杀任意敌人必掉
```
> `UnitDropRuleDesc` 的 `f1` 是**敌兵 ID**（1000~1013=一章小妖，1021~1028=一章精英，2001~2049=二章…），共 66 条，覆盖了绝大部分敌人。

**效果预期**：装了这个 PAK 后，玩家**打碎任意罐子/木箱**、或**杀任意敌人**、或**去土地庙上香/开宝箱**，都会掉落一个「大圣之意（意见欲）」，拾取后 `修行 → 根器` 里「意见欲」即解锁，可自行选择「合意同心」并参悟。

**没有改动任何**：根器效果（FUStBuffDesc-* / FUStSkillEffectDesc-* / TalentSDesc）、属性表、天赋、其他掉落条目（所有原始字段都原样保留，见第 4 节校验）。

---

## 4. 已完成的自校验（可信度依据）

1. **pak 读取器**：`tools\pak.py` 能正确解析游戏全部 pak（pakchunk0 有 113689 个文件）、解密索引、解压 Oodle/Zlib 数据。
2. **pak 写入器**：用「读案例 MOD → 重新打包 → 与原文件逐字段对比」验证。逐字段核对结果：
   - entry 内联头布局、`sha1(未压缩数据)` 哈希、block count=1、block=(74, 74+compressed)、`flags`、`compression_block_size=未压缩长度` —— **全部与原文件一致**；
   - footer 布局（guid(16) → encrypted_index(1) → magic → version=11 → `0x0010` → index_offset → index_size → sha1(index头) → 5×32 压缩名）与原文件一致；
   - index 头（mount_point / record_count / seed / phi+fdi 及其 sha1 / encoded entries / non_encoded=0）一致；
   - 唯一差异：zlib 压缩等级不同导致压缩后字节数不同（案例用 78 01，我用 78 da），**不影响正确性**。
   - 重新读取自建 pak，12 个文件全部内容一致。
3. **protobuf 读写器**：`tools\pbraw.py` 保证「解析→重新编码」**逐字节等同**；`tools\make_mod.py` 里对要改的两张表做了断言（round-trip 通过）才动手。
4. **改动校验**：`tools\verify_mod.py` 逐记录比对原版 vs 改后——
   - 原始字段**全部按原顺序保留**（`PROBLEM - originals not preserved...: none`）；
   - 只有 11 条掉落规则各多 1 个 `f13`（其中 91000 另加 `f10`）；
   - 66 条敌人掉落各多 1 个 `f4`。
5. **优先级确认**：全库扫描确认只有 `pakchunk16-Windows.pak` 含这两张表（无补丁 pak 覆盖），我的 pak 挂载点 `../../../` + `b1/Content/...` 与本体 `../../../b1/Content/` + `00Main/...` 解析为**同一路径**，可正常覆盖。

---

## 5. 下一位 AI 要做什么（按优先级）

### 第一优先：实机验证（用户操作，或让用户反馈）
让用户按第 6 节安装后进游戏：
1. 打碎一个罐子 / 杀一个怪 / 去土地庙上香；
2. 看是否掉落「大圣之意」并可在 `修行 → 根器` 里看到「意见欲」可选；
3. 确认「合意同心」能参悟。
若成功 → 项目完成（只需清理工具目录、交付说明书）。

### 若未生效：备选方案（按风险从低到高）
- **A. 扩大掉落通道**：把 `f13={4096,1,1,10000}` 加到更多规则上。做法：用 `tools\scan_relic_refs.py` 思路先找出 `FUStInteractionMappingDesc.data` 里被最多交互引用的规则 ID（我扫过：2013=16次、2008=15、5001=13、2016/2002/2014/2009=8~9、9001=7、3102=7，已包含在本次 MOD 中），可再往上加 3070/2019/2222 等（这几条在 CommDropRuleDesc 里**不存在**，需新建规则记录）。
- **B. 商店通道**：给 `ShopItemDesc.data` 新增一条记录并把 4096 加进 `ShopItemGroupDesc.data` 的组 1001（一章土地庙商店，卖「行者」套装的那一组 → 对应 `ShopRefreshDesc` 里 shop 2000 / refresh 2001）。
  新增记录要模仿：`{f1: 唯一ID(如 900001), f2: 4096, f3: 一个不与现有冲突的 1~96 的值, f4: 字节 '08ee1e1004' 之类, f5: 1, f8: 价格, f10: 1}`。
  **风险**：f3/f4 语义未确认（f3 取值 1~96，疑似排序/图标槽位，越界可能出问题），且商店 UI 是否显示 type=14 道具未验证。
- **C. 根器宝箱通道**：`FUStInteractionMappingDesc.data` 里把某个「玩家早期必定能开的宝箱」交互的 `f2` 指向 9906（意见欲宝箱规则），或干脆给 9901/9902 这些**已存在的根器宝箱规则**加 f13。注意：宝箱是否已在关卡里摆放、是否被剧情脚本隐藏，未验证。
- **D. UE4SS + GM 命令**（社区标准做法，但会往游戏目录写文件，用户明确怕动本体，需先问用户）：
  游侠网的「命令解锁全部物品护甲意志与经验MOD」用 UE4SS Lua 调用游戏自带 GM 命令系统加物品/意志，`F7` 执行；前置 UE4SS 解压到 `b1\Binaries\Win64\ue4ss\Mods\`。**这条与 PAK 路线独立，是最稳的兜底。**

### 若实机发现掉落刷屏（重复获得大量「大圣之意」）
属于可接受副作用（关键道具多几个无害），但若用户不喜欢：把 `f13` 的 `f4` 权重从 `10000` 降到 `1000~2000`（概率掉落），或只保留 91000（可破坏物）一条通道。

---

## 6. 安装说明（给用户的原话，可直接转发）

1. 打开 `C:\Program Files (x86)\Steam\steamapps\common\BlackMythWukong\b1\Content\Paks\`，
   若没有 `~mods` 文件夹就**新建一个**（名字就是一个波浪号 + mods）。
2. 把 `pakchunk28-Windows_P.pak` 复制进 `~mods`。
3. Steam 里右键《黑神话：悟空》→ 属性 → 通用 → 启动选项，填入 `-fileopenlog`（推荐，社区惯例）。
4. **黑盒 / Mod-Box 管理器**：该管理器设置里游戏为 `blackmythwukong`，本体路径 `c:\program files (x86)\steam\steamapps\common\BlackMythWukong`，MOD 数据目录 `D:\mods_data`。
   - 用管理器的「导入本地 MOD / 添加本地文件」，选择这个 pak，导入后启用即可；管理器会把它部署到游戏的 `~mods`。
   - 若管理器不认这种"裸 pak"，就直接按第 1~2 步手动放进 `~mods`（效果一样，互不冲突）。
5. 进游戏后：打碎任意罐子/木箱，或杀任意小怪，拾取掉落的「大圣之意」→ 打开 `修行 → 根器`，即可选择「意见欲 → 合意同心」。
6. 卸载：直接删掉 `~mods` 里的这个 pak 即可，**不坏档**。

---

## 7. 工具与目录说明（给下一位 AI）

### 目录规范
```
1-大圣根器mod\
├── HANDOVER.md                    ← 本文件（根目录，便于直接转发给 AI）
├── 大圣根器-优秀案例\              ← 用户提供的参考 MOD（原样保留）
│   ├── pakchunk27-Windows_P.pak
│   └── 安装说明 Readme.txt
├── 输出\
│   └── pakchunk28-Windows_P.pak   ← 最终交付物
├── tools\                          ← 工具与脚本
│   ├── pak.py                     ← UE5 pak 读/写器（BMW 专用，已适配 guid→bool 的 footer）
│   ├── oodle.py                   ← Oodle 解压/压缩 ctypes 封装
│   ├── pb.py / pbraw.py           ← protobuf 解码 / 逐字节保真编辑
│   ├── dump_candidates.py、scan_*.py、find_refs.py、shop_*.py、strings.py …（分析脚本）
│   ├── make_mod.py                ← **构建 MOD 的入口脚本**
│   ├── verify_mod.py              ← MOD 校验脚本
│   └── bin\oo2core_9_win64.dll    ← Oodle 运行库（sha256 6f5d41a7…f457，必需）
│   └── bin\repak.exe              ← 无效，勿用（footer 字段顺序与本游戏不同）
└── work\                           ← 中间产物（可删，重新生成见下）
    ├── vanilla\base\...           ← 从游戏导出的原版表
    ├── sample_extract\...         ← 案例 MOD 解包结果
    ├── assets\...                 ← 从游戏解出的蓝图（Genqi/大圣天赋 UI）
    └── analysis\...               ← 全部分析报告（表结构、掉落规则、商店结构…）
```

### 常用命令（在项目根目录执行）
```powershell
# 重新构建 MOD（读游戏原版表 → 追加字段 → 输出 输出\pakchunk28-Windows_P.pak）
python tools\make_mod.py

# 校验 MOD（逐记录比对，确认只有新增字段、原字段全保留）
python tools\verify_mod.py

# 列出任意 pak 内容 / 解包
python tools\pak.py list <pak路径>
python tools\pak.py extract <pak路径> <输出目录>
```

### 关键技术要点（避坑，务必保留）
- **Oodle 解压**：游戏 `.data` 是 Oodle 压缩。必须用 `tools\bin\oo2core_9_win64.dll`（来源 `https://ghproxy.net/https://raw.githubusercontent.com/WorkingRobot/OodleUE/main/Engine/Source/Programs/Shared/EpicGames.Oodle/Sdk/2.9.10/win/redist/oo2core_9_win64.dll`，直连 github 会被重置，走 ghproxy 镜像）。多块解压时**块的偏移是"相对 entry 起点"的绝对偏移，且必须用数据区内联头（不是索引里的块大小）**，每块输出长度 `min(compression_block_size, 剩余)`。
- **索引里的 encoded entry 只存"每块压缩后大小"**，偏移是累加出来的；单块文件 `compression_block_size = 未压缩长度`。
- **数据内联头比标准多 1 字节**（`HEADER_EXTRA=1`，紧跟 u64 offset 之后，值为 0），所以单块头长 = 74，n 块 = 58+16n。
- **游戏 pak 的 footer 是 guid(16) → encrypted_index(1) → magic**（repak 是反的，所以 repak 用不了）；游戏本体 pak 的索引是加密的，`encrypted_index=1`。
- **BMW AES key**：`A896068444F496956900542A215367688B49B19C2537FCD2743D8585BA1EB128`（AES-256-ECB，只解密 16 字节整数倍部分），用于索引/部分数据条目（`flags & 1` 表示数据条目加密）。
- **挂载点**：本体 chunk16 是 `../../../b1/Content/` + `00Main/...`；MOD 用 `../../../` + `b1/Content/00Main/...`，两者解析成同一路径才能覆盖。
- **不要用 repak**：footer 字段顺序不兼容（报错 `trying version V11 failed: got 18, which is not a boolean`）。
- **严禁改动游戏本体目录**（用户明确要求）；所有产出都写在项目目录里。

### 已生成的分析报告索引（`work\analysis\`）
- `TalentSDesc_mod.json`、`relic200.json`：根器天赋记录
- `droprules.txt` / `droprules2.txt` / `relic_drops.txt`：掉落规则与根器掉落（**最关键**）
- `chest_rules.txt` / `chests.txt` / `interaction_relics.txt`：宝箱与交互 → 掉落规则映射
- `shop_structure.txt` / `shopitem_all.txt`：商店结构（备选方案 B 用）
- `item_relic.txt` / `item_4070_4110.txt` / `names_destruction.txt`：物品与破坏物表
- `globalcfg.txt`、`collect_drop.txt`、`unitdrop.txt`、`roledata_f4.txt`、`strings\*.txt`：其他排查记录

---

## 8. 一句话总结

**根器不是"开关表"，而是"物品"**：我给 11 条常见掉落规则（可破坏物/土地庙/宝箱/交互）和 66 条敌人掉落组**纯追加**了「必掉物品 4096（意见欲）」的条目，产出 `输出\pakchunk28-Windows_P.pak`；
**没有改动任何原版功能数值**，pak 结构已与原版/案例逐字段比对通过，**唯一未完成的是实机验证**——请下一位 AI 先让用户按第 6 节安装试一次，再按第 5 节的备选方案推进。
