# AI 生图经验库

> 记录生图过程中积累的提示词、技巧、成功/失败案例。
> 持续更新中 🚀

---

## 📁 目录结构

```
amazing-ai-prompts/
  image-gen-notes.md          # 本文件：生图经验库 & 技巧
  prompts-collection.md       # 提示词收藏库（含效果图占位）
  issues-log.md               # 踩坑问题记录
  assets/                     # 效果图存放目录
  research/
    ai-image-video-apps.md    # AI 生图/生视频应用调研
```

---

## 🗂️ 经验卡片模板

复制下面的模板，填写后追加到对应分类下。

```markdown
### 标题（风格 + 关键特征）
**平台：** Grok / Midjourney / FLUX / SD / ComfyUI
**模型：** Hero / FLUX.1 dev / GPT Image-2 / ...
**日期：** YYYY-MM-DD
**评分：** ⭐⭐⭐⭐☆

**提示词（中文）：**
（在此填写）

**提示词（英文）：**
（在此填写）

**关键参数：**
- 尺寸：
- Steps / CFG：
- 其他：

**效果描述：**
（哪里好，哪里有瑕疵）

**改进方向：**
（下次怎么优化）
```

---

## 🎨 案例记录

### 古风仙侠

#### ✅ 冰蓝礼服仙侠女性
**平台：** Grok Imagine
**日期：** 2026-05-03
**评分：** 待测试

**提示词（中文）：**
超写实古风仙侠美女，身着冰蓝色曳地礼服，裙摆轻盈拖曳，腰间佩戴精致白玉腰带，头戴华贵发冠，发丝细腻，神情冷艳高贵，站在飘渺云雾间的仙境石台上，仙气十足，背景为淡蓝色云海与远山，超高清，电影级光影，8K画质，完美面部细节

**提示词（英文）：**
Ultra-photorealistic ancient Chinese xianxia beauty, wearing an ice-blue floor-length ceremonial gown with a gently trailing skirt, adorned with an exquisite white jade waist belt, wearing an ornate imperial headdress, hair rendered with fine detail, expression cold and noble, standing on a mystical stone platform amid drifting celestial mist, ethereal immortal atmosphere, backdrop of pale blue cloud sea and distant mountains, ultra-high definition, cinematic lighting, 8K resolution, perfect facial detail

**备注：** 提示词于 2026-05-03 由原始中文稿校对（修正了拖曳/神情/搭配/设定等错别字后翻译）

---

## 💡 通用技巧

### 提示词写法

- **质量提升 tag：** `ultra-photorealistic, 8K, cinematic lighting, masterpiece, best quality`
- **人物细节：** `perfect hands, anatomically correct, detailed facial features`
- **风格锁定（Midjourney）：** `--v 7 --ar 9:16 --style raw`
- **FLUX 特有：** 描述要更详细，比 SD 更能理解复杂场景

### 常见问题 & 解决

| 问题 | 解决方案 |
|------|----------|
| 手指变形/多指 | 加 `perfect hands, five fingers, anatomically correct` |
| 面部失真 | 加 `detailed face, symmetrical features, natural skin` |
| 衣服纹理糊 | 加 `intricate fabric detail, textured cloth, fine embroidery` |
| 背景太乱 | 加 `clean background, bokeh, depth of field` |
| 出图内容偏离提示词 | 精简提示词，核心描述放前面 |

### 各平台特点

| 平台/模型 | 优势 | 适合场景 |
|-----------|------|----------|
| FLUX.1 dev | 文字渲染强、人体准确 | 写实、商业风 |
| Midjourney | 艺术感强，画面完整度高 | 插画、概念艺术 |
| GPT Image-2 | 理解复杂指令、一致性好 | 场景描述复杂时 |
| Hero | 内容限制少 | 特定创作需求 |
| Hunyuan（混元） | 服装、物体渲染好 | 时尚、产品图 |
| Qwen 2（通义） | 中文提示词理解强 | 中文创作者友好 |
| Flux Kontext | 保持角色/主体一致性 | 多图一致性创作 |

---

## 🔗 相关资源

- [PromptHero](https://prompthero.com/) — 提示词社区，图+提示词展示
- [grokprompts.app](https://grokprompts.app/) — Grok 生图提示词库
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) — 节点式本地生图工具
- [FLUX GitHub](https://github.com/black-forest-labs/flux) — Black Forest Labs 官方

---

*最后更新：2026-05-03*
