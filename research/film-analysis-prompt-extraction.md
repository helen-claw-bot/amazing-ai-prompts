# 拉片指南：关键帧提取 + 提示词提炼

> 适用场景：看到优秀短片/影片，想学习其构图、光线、风格，并提炼成可复现的 AI 生图提示词
> 整理日期：2026-05-04

---

## 一、什么是拉片

拉片 = 逐帧分析一部影片，学习导演的镜头语言、构图、光线、色调设计。
对 AI 生图来说，拉片的目标是：**把你看到的好画面，转化成可以复现的提示词**。

---

## 二、提取关键帧（工具方法）

### 方法1：ffmpeg 批量提帧（推荐）

```bash
# 每5秒提取1帧（适合分析整体节奏）
ffmpeg -i film.mp4 -vf fps=0.2 frames/frame_%04d.jpg

# 每秒提取1帧（适合精细分析）
ffmpeg -i film.mp4 -vf fps=1 frames/frame_%04d.jpg

# 只提取某段（如5:00到10:00）
ffmpeg -ss 00:05:00 -i film.mp4 -to 00:10:00 -vf fps=0.2 frames/frame_%04d.jpg
```

### 方法2：VLC 截图
- 暂停到想要的帧 → `Video` → `Take Snapshot`

### 方法3：用本文件夹的 cut_video.py
先把精彩片段切出来，再 ffmpeg 提帧

---

## 三、分析关键帧（让 AI 帮你提炼）

把截图发给 Claude / GPT-4V，用这个提问模板：

```
请分析这张电影截图的以下要素，并输出一段可以用于 Midjourney 或 GPT Image2 的英文提示词：

1. 景别（特写/中景/全景/等）
2. 镜头角度（平视/仰拍/俯拍）
3. 构图方式（三分法/对称/引导线等）
4. 光线方向和质感
5. 色调风格（暖/冷/对比度）
6. 主体与背景关系
7. 情绪氛围

最后输出：可复现此画面的 Midjourney 提示词（英文，包含 --ar 参数）
```

---

## 四、提示词提炼模板

AI 分析后，输出格式参考：

```
[景别+角度], [主体描述],
[背景/环境],
[光线描述],
[色调/氛围],
[构图特点],
[风格参考],
--ar [宽高比] --v 6.1
```

**实际示例（分析一帧古装剧截图）：**
```
Medium shot, low angle, young Chinese woman in white hanfu,
standing on ancient stone bridge, misty mountain valley background,
soft backlit morning light with golden rim,
cool blue-green color grade, ethereal and mysterious atmosphere,
subject centered with leading lines from bridge railings,
xianxia cinematic style, ink painting aesthetic,
--ar 16:9 --v 6.1
```

---

## 五、建立自己的"构图灵感库"

**推荐工作流：**

```
看到好片
  → ffmpeg 提帧（关键时间点）
  → 发给 AI 分析，输出提示词
  → 把提示词存入 prompts-collection.md（按风格分类）
  → 下次创作直接调用
```

**prompts-collection.md 分类建议：**
- 古风仙侠场景
- 现代都市场景
- 人物特写/情绪
- 大场景/环境
- 特效/魔法场景

---

## 六、拉片重点关注要素速查

| 要素 | 看什么 | 转化为提示词 |
|------|-------|------------|
| 景别 | 人物占画面多少 | `close-up / medium shot / wide shot` |
| 光位 | 光从哪个方向来 | `front light / side light / backlit` |
| 色温 | 偏暖还是偏冷 | `warm golden tones / cool blue tones` |
| 对比度 | 明暗反差大不大 | `high contrast / soft contrast / flat lighting` |
| 景深 | 背景清不清晰 | `shallow DOF, bokeh / deep focus` |
| 构图 | 人物在画面哪个位置 | `rule of thirds / centered / off-center` |
| 氛围 | 整体给你什么感觉 | 见"情绪氛围"关键词表 |

---

## 七、推荐拉片的片单（AI 生图参考）

### 古风仙侠风格参考
- 《陈情令》《天官赐福》《古相思曲》（短片）
- 国风概念艺术：@WLOP、@古风CG

### 现代都市风格参考
- 《隐秘的角落》《无证之罪》（光线/氛围）
- 台剧《我可能不会爱你》（日常温柔感）

### 构图学习参考
- 任何王家卫电影截图（色调+构图经典）
- 《卧虎藏龙》（古风空间感）

---

*整理：虾爬子🦐*
