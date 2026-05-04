# AI影视前期制作调研报告

> 调研日期：2026-05-04  
> 适用场景：两人小工作室，预算有限  
> 目标输出：角色定妆照 + 静态分镜故事板（漫画/绘本风格）  
> 剧目：① 现代都市爱情剧（娱乐圈/名利场）② 中国古代奇幻剧（志怪/妖/仙/法术）

---

## 一、核心问题与解题思路

### 两大难题

| 难题 | 描述 | 严重程度 |
|------|------|---------|
| **角色一致性** | 同一人物在不同场景、姿势、光线下脸要一致 | ⭐⭐⭐⭐⭐ 最难 |
| **环境/空间一致性** | 同一场景在不同镜头中建筑、陈设、光线保持一致 | ⭐⭐⭐⭐ 次难 |

### 解题总思路

```
真实人脸照片（已授权）
        ↓
  [换脸/特征注入]          ← InstantID / PuLID / GPT Image2 图生图
        ↓
  角色基准图（定妆照）
        ↓
  [场景 + 分镜生成]         ← Midjourney sref + 定妆照 cref
        ↓
  分镜故事板图册
```

---

## 二、工具选型

### 2.1 角色一致性工具对比

| 工具 | 方案 | 一致性强度 | 上手难度 | 成本 | 推荐度 |
|------|------|-----------|---------|------|-------|
| **ComfyUI + InstantID-2** | 本地/云端，输入真实人脸，生成任意风格的同脸图 | ⭐⭐⭐⭐⭐ | 高（需装环境） | 免费（本地GPU）/ 云端按量 | ✅ 定妆照首选 |
| **ComfyUI + PuLID-Flux2** | 基于FLUX.1-dev，2025年最新，效果比InstantID更自然 | ⭐⭐⭐⭐⭐ | 高 | 免费（本地GPU） | ✅ 质量最高 |
| **GPT Image2 (ChatGPT)** | 上传参考图 + 提示词，同一对话内一致性较好 | ⭐⭐⭐ | 低 | $20/月(Plus) | ✅ 快速出图 |
| **Midjourney v8.1 + Omni Reference** | 上传人脸图作为 `--oref`，新版已合并cref | ⭐⭐⭐⭐ | 中 | $10-30/月 | ✅ 美感最强 |
| **Grok (Spicy Mode)** | 内容限制宽松，适合写实古装 | ⭐⭐⭐ | 低 | 含在xAI订阅 | ⚠️ 补充用 |

> **关键洞察：** 你已有真实模特的面部授权照片，这是最强的输入条件。用 InstantID / PuLID 可以把真实人脸"注入"任意风格，实现高度一致。

### 2.2 分镜故事板工具

| 工具 | 适合场景 | 一致性 | 成本 |
|------|---------|--------|------|
| **Midjourney + sref（风格参考）** | 统一画风的分镜图册 | ⭐⭐⭐⭐ | $10/月起 |
| **GPT Image2（对话式）** | 快速文字驱动分镜，同对话内保持一致 | ⭐⭐⭐ | 含ChatGPT Plus |
| **量子探险（yfbudong.com）** | 国内平台，文本→分镜全流程，中文友好 | ⭐⭐⭐ | 按需付费 |
| **ComfyUI 批量工作流** | 高度自定义，可锁定角色+场景 | ⭐⭐⭐⭐⭐ | 免费（成本是学习曲线） |

---

## 三、推荐工作流（适合2人小团队）

### 阶段一：角色定妆照生产

**推荐方案：GPT Image2（快速） + ComfyUI InstantID（精品）**

```
Step 1: 整理模特授权照片（正面、侧面、不同光线，4张以上最佳）

Step 2: GPT Image2 快速出版 —— 快速验证角色方向
  提示词结构：
  "[详细外貌描述], [服装风格], [场景背景], [光线], 
   [画风], portrait photography, high quality"
  技巧：同一对话内追问 "same character, [变化内容]"

Step 3: ComfyUI + InstantID-2 精品出图
  - 输入：4张以上同一模特真实面部照片
  - 工作流：InstantID 文生图工作流 → 输出古风/现代各种定妆
  - 风格控制：配合IP-Adapter加载风格参考图

Step 4: 人工筛选，建立角色基准图库（每个角色10-20张）
```

### 阶段二：分镜故事板生产

**推荐方案：Midjourney + sref风格锁定**

```
Step 1: 确定画风（漫画/绘本风格）
  - 用 --sref [风格参考图URL] 锁定全局画风
  - 古装剧：水墨漫画风 / 仙侠插画风
  - 现代剧：城市轻漫画风 / 写实插图风

Step 2: 用定妆照作为 Omni Reference
  - --oref [角色定妆照URL] --ow 50~80（权重控制）

Step 3: 分镜提示词模板（见第五节）

Step 4: 批量生成，用GPT辅助写分镜描述文本
```

### 阶段三：整合成图册

```
- 用 Canva / Adobe Express 排版分镜图册
- 每页：分镜图 + 场景描述 + 台词/旁白
- 输出格式：PDF 图册（便于展示/投资人看）
```

---

## 四、成本估算

### 月度工具成本（2人工作室）

| 工具 | 月成本 | 用途 |
|------|--------|------|
| ChatGPT Plus（GPT Image2） | $20/月 × 1账号 | 快速出图、剧本辅助 |
| Midjourney Standard | $30/月 | 分镜、定妆照美化 |
| Grok（xAI Premium） | $30/月 | 补充出图（内容宽松） |
| ComfyUI 本地 | 电费+GPU时间 | 精品定妆照（InstantID/PuLID） |
| ComfyUI 云端（RunComfy/Vast.ai） | 按量，约$5-20/月 | 没有本地GPU时的替代 |
| **合计** | **~$80-100/月** | |

> **省钱建议：**
> - 先只订 ChatGPT Plus + Midjourney Basic（$10/月）= $30/月起步
> - ComfyUI 用免费云端 Colab 或 Kaggle 跑（有免费GPU额度）
> - Grok spicy mode 属于赠品，不需要额外开销（如已订阅xAI）

### 单项成本参考

| 产出物 | 估算成本 | 工具 |
|--------|---------|------|
| 一个角色定妆照（10张） | $2-5 | ComfyUI云端 |
| 一集分镜（30-50张） | $5-15 | Midjourney |
| 全剧定妆照（4-6个角色） | $20-40 | 混合工具 |
| 全集分镜图册（12集） | $60-180 | Midjourney |

---

## 五、提示词模板

### 5.1 古装奇幻剧 — 定妆照

```
[角色名], [年龄描述], traditional Chinese fantasy costume, 
xianxia aesthetic, [发型：如 black hair with jade hairpin], 
[服装：如 white flowing hanfu with silver embroidery], 
[气质：如 ethereal, mysterious], 
soft studio lighting, clean background, 
portrait photography, ultra detailed, 8K,
painterly style with ink wash texture
```

**细化关键词库（古装奇幻）：**
- 服装：hanfu, dao clothing, immortal robes, demon lord armor, fox spirit dress
- 配饰：jade pendant, silver crown, lotus hairpin, bone bracelet
- 气质：celestial, demonic, ethereal, righteous, playful fox spirit
- 场景：misty mountains, ancient temple, peach blossom forest, night sky with stars

### 5.2 现代都市剧 — 定妆照

```
[角色名], [年龄描述], modern Chinese entertainment industry,
[身份：如 rising actress / entertainment CEO / paparazzi],
[服装：如 high fashion, designer suit, casual chic],
[场景：如 press conference, luxury penthouse, TV studio backstage],
natural photography lighting, editorial style,
sharp focus, cinematic composition
```

**细化关键词库（现代都市）：**
- 身份：entertainment CEO, rising star actress, gossip journalist, luxury brand manager
- 场景：Sanlitun luxury mall, TV award ceremony, rooftop bar, film set
- 情绪：ambitious, melancholic, confident, vulnerable behind the glamour

### 5.3 分镜提示词结构

```
[镜头类型] shot, [主体描述], [动作/情绪], 
[场景描述], [光线], [构图],
[画风], storyboard panel, black and white sketch / comic book style,
cinematic framing
```

**镜头类型词库：**
- extreme close-up / close-up / medium / wide / extreme wide
- over-the-shoulder / POV / bird's eye / low angle / dutch angle
- establishing shot（建立镜）/ reaction shot（反应镜）

**示例 - 古装分镜：**
```
wide establishing shot, ancient Chinese mountain gate in mist,
two figures in white robes standing at the entrance,
dawn light, dramatic atmosphere,
ink wash painting storyboard style, black and white,
cinematic composition, high contrast
```

**示例 - 现代分镜：**
```
medium shot, young woman in black dress, 
standing at floor-to-ceiling window overlooking night city skyline,
she turns to look at camera with a complex expression,
backlit by city lights, moody cinematic lighting,
comic storyboard style, clean lines
```

---

## 六、角色一致性实战技巧

### GPT Image2 技巧
1. **同一对话不退出** —— GPT会记住前面生成的角色，直接说 "same character, now in [新场景]"
2. **建立角色卡** —— 先用文字描述写一张详细的角色卡，每次生成前粘贴进去
3. **锁定特征词** —— 挑3-5个最独特的外貌词（如 "sharp jawline, distinctive beauty mark, copper-colored eyes"）每次必带

### Midjourney 技巧
1. **Omni Reference (--oref)** —— V7/V8.1用法，上传定妆照URL作为身份参考
2. **Style Reference (--sref)** —— 锁定画风，保证整本分镜风格统一
3. **权重调节** —— `--ow 50` 适度参考，`--ow 100` 强制贴近（但可能损失创意）
4. **角色一致性测试** —— 先用同一张参考图生成20张不同场景，挑出一致性最好的5张作为新基准

### ComfyUI InstantID 技巧
1. **多角度输入** —— 提供同一模特的正面、45度侧面、不同光线4张以上，效果大幅提升
2. **风格权重** —— IP-Adapter的风格权重和InstantID的ID权重分开调，通常ID=0.8, style=0.6
3. **批量工作流** —— 一次跑完所有场景变体，省时省钱

### 环境一致性技巧
1. **建立场景基准图** —— 每个主要场景（古镇、宫殿、现代公寓）先生成1张高质量基准图
2. **用基准图作为 Image Prompt** —— 后续该场景的所有分镜都把基准图作为参考
3. **场景关键词标准化** —— 在提示词管理文档里固定每个场景的描述词，不要每次重新写

---

## 七、国内可用平台补充

| 平台 | 特点 | 适用 |
|------|------|------|
| **通义万相（阿里云）** | 支持多镜头连贯叙事，中文提示词 | 分镜生成 |
| **量子探险（yfbudong.com）** | 文本→分镜全流程，适合网文改编 | 快速分镜 |
| **LiblibAI** | 国内ComfyUI云端平台，有现成工作流 | ComfyUI替代 |
| **吐司（tusi.art）** | 大量古风/仙侠模型，中文社区 | 古装定妆照 |

---

## 八、推荐行动计划

### 第一周：工具验证
- [ ] 用GPT Image2测试古装/现代两个角色的基础定妆照
- [ ] 注册Midjourney（Basic $10/月），测试Omni Reference
- [ ] 整理模特授权照片（每人至少4张，不同角度/光线）

### 第二周：建立角色基准
- [ ] 用InstantID（LiblibAI云端）生成精品定妆照
- [ ] 每个角色选定10张基准定妆照
- [ ] 写定妆照角色卡（固定外貌关键词）

### 第三周：分镜试产
- [ ] 确定分镜画风（用Midjourney出5种风格对比）
- [ ] 用第一集剧情生成30张分镜
- [ ] 整合成PDF图册，评估效果

### 第四周：工作流固化
- [ ] 整理提示词模板，存入 prompts-collection.md
- [ ] 建立两部剧的场景关键词库
- [ ] 评估是否需要引入ComfyUI本地环境

---

## 九、参考资源

- [Midjourney Omni Reference 官方文档](https://docs.midjourney.com/hc/en-us/articles/36285124473997-Omni-Reference)
- [ComfyUI InstantID-2 知乎教程](https://zhuanlan.zhihu.com/p/1920260523053790631)
- [GPT Image2 角色一致性指南](https://blog.laozhang.ai/ai-tools/mastering-character-consistency-chatgpt-image-generator/)
- [AI影视成本分析2026](https://www.mindstudio.ai/blog/ai-filmmaking-cost-breakdown-2026)
- [PuLID-Flux2 ComfyUI实现](https://github.com/iFayens/ComfyUI-PuLID-Flux2)
- [通义万相分镜提示词指南](https://help.aliyun.com/zh/model-studio/text-to-video-prompt)

---

---

## 十、GPT Image2 vs Midjourney 深度对比

### GPT Image 2 的短板（影视前期场景下）

- **没有原生的风格锁定机制** —— MJ有 `--sref` 可以把一张参考图的画风完全克隆到所有输出，Image2做不到这种精准锁定，每次生成风格会漂移
- **分镜批量生产效率低** —— Image2是对话式，一张一张来；MJ可以同时跑4张变体，还有 Repeat 批量模式
- **构图控制弱** —— MJ对镜头语言（`--ar`宽高比、`low angle`、`dutch angle`）的响应比Image2稳定得多，分镜场景的构图更可控
- **成本其实差不多** —— Image2 API 按张计费（约$0.04-0.17/张），MJ Standard $30/月无限Relax模式出图，大量出图时MJ更划算

### MJ真正的护城河

- **Omni Reference（`--oref`）锁人脸 + Style Reference（`--sref`）锁画风**，两个同时用 = 角色脸 × 统一画风，这是目前最稳定的分镜一致性方案
- **美感天花板高** —— 同样的提示词，MJ出图的"电影感"构图比Image2强，定妆照更有质感
- **社区资源** —— 大量现成的古风/仙侠 `--sref` 风格码可以直接拿来用

### 什么时候用 Image2 API？

- 剧本辅助、快速验证想法（不需要高质量）
- 需要文字渲染（海报上加字）—— Image2文字生成远强于MJ
- 有精确的文字描述，不需要风格参考图时

### 结论

> Image2 = 快速原型 + 文字渲染
> MJ = 分镜量产 + 风格一致性 + 美感出品

两个配合用，不是非此即彼。分镜故事板用MJ，定妆照快速验证用Image2。

---

*报告由虾爬子🦐整理，基于2025-2026年公开资料，部分定价可能随时更新，使用前以官网为准。*
