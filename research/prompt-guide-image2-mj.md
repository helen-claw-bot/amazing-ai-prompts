# GPT Image2 提示词速查手册

> 适用场景：影视前期制作，从灵感草图到可生成画面的提示词
> 整理日期：2026-05-04

---

## 一、提示词万能模板

```
[主体描述] + [动作/状态] + [环境/背景] + [光线] + [镜头/构图] + [风格]
```

**示例：**
```
A young Chinese woman in white hanfu, standing still with eyes closed,
ancient Chinese town at night, paper lanterns, foggy street,
soft warm lantern light from the left,
medium shot, slightly low angle, centered composition,
xianxia style, cinematic, ink painting aesthetic
```

---

## 二、用草图辅助出图

GPT Image2 支持**上传图片 + 文字描述**，即使是火柴人草图也能用：

**用法：**
1. 画出你想要的构图（人物位置、大致场景布局）
2. 上传图片，附上文字：
   > "参考这个构图和人物位置关系，生成一个古风场景：女主角白色汉服站在画面左侧，右侧是一个神秘摊位，夜晚，灯笼光..."

**效果：** AI 会按你草图的空间布局来生成，构图可控

---

## 三、核心关键词速查表

### 景别（镜头距离）

| 中文 | 英文提示词 |
|------|-----------|
| 特写（脸部） | `close-up portrait` |
| 近景（胸部以上） | `medium close-up` |
| 中景（腰部以上） | `medium shot` |
| 全景（全身） | `full body shot` |
| 远景（人在环境中） | `wide shot, establishing shot` |
| 航拍/俯瞰 | `aerial view, bird's eye view` |
| 仰拍 | `low angle shot` |
| 俯拍 | `high angle shot` |

### 光线风格

| 效果 | 英文提示词 |
|------|-----------|
| 自然柔光 | `soft natural lighting, diffused light` |
| 戏剧侧光 | `dramatic side lighting, chiaroscuro` |
| 逆光/轮廓光 | `backlit, rim light, silhouette` |
| 黄金时刻 | `golden hour, warm sunset light` |
| 夜景/灯笼 | `night scene, warm lantern light, candlelight` |
| 月光 | `moonlight, cool blue light, night` |
| 霓虹都市 | `neon lights, cyberpunk lighting, night city` |

### 情绪氛围

| 情绪 | 英文提示词 |
|------|-----------|
| 神秘感 | `mysterious, ethereal, misty atmosphere` |
| 史诗感 | `epic, grand, majestic` |
| 悬疑紧张 | `suspenseful, dramatic tension, dark atmosphere` |
| 浪漫温柔 | `romantic, soft, dreamy, warm` |
| 孤独忧郁 | `melancholic, lonely, somber` |
| 喜悦活力 | `joyful, vibrant, energetic` |

### 画面风格

| 风格 | 英文提示词 |
|------|-----------|
| 电影感 | `cinematic, film still, anamorphic lens flare` |
| 古风仙侠 | `xianxia, ancient Chinese fantasy, ink painting style` |
| 水墨画 | `Chinese ink wash painting, traditional art` |
| 漫画/绘本 | `comic book style, illustrated, graphic novel` |
| 写实照片 | `photorealistic, hyperrealistic, photography` |
| 概念艺术 | `concept art, digital painting, detailed` |

### 构图法则

| 构图 | 英文提示词 |
|------|-----------|
| 三分法 | `rule of thirds` |
| 对称构图 | `symmetrical composition, centered` |
| 引导线 | `leading lines` |
| 框中框 | `frame within frame` |
| 深景深虚化 | `shallow depth of field, bokeh background` |

---

## 四、两部剧专用提示词模板

### 现代都市爱情剧（娱乐圈）

**定妆照模板：**
```
[角色名], modern Chinese actress, [服装描述],
professional studio portrait, soft beauty lighting,
clean background, high fashion editorial style,
photorealistic, ultra detailed, 8K
--ar 2:3
```

**分镜场景模板：**
```
[景别], [人物状态],
modern urban setting, [具体场景如: luxury apartment / TV studio / rooftop],
[光线], [情绪氛围],
cinematic film still, modern drama aesthetic
--ar 16:9
```

### 中国古代奇幻剧（志怪/仙侠）

**定妆照模板：**
```
[角色名], ancient Chinese [角色定位如: celestial fairy / demon lord],
wearing [服装描述: white hanfu with golden embroidery],
traditional Chinese palace / mountain setting,
soft ethereal lighting, [头发/配饰描述],
xianxia style, ink painting aesthetic, ultra detailed
--ar 2:3
```

**分镜场景模板：**
```
[景别], [人物状态],
[环境: ancient Chinese mountain / jade palace / misty forest],
[特效: floating petals / magical aura / sword light],
[光线: moonlight / ethereal glow],
xianxia cinematic, epic fantasy, dramatic atmosphere
--ar 16:9
```

---

## 五、常见问题与修正词

| 问题 | 修正词 |
|------|-------|
| 脸变形/多手多脚 | 负面提示：`bad anatomy, deformed, extra limbs` |
| 画面太暗 | `well-lit, bright, clear visibility` |
| 风格不够古风 | `traditional Chinese, Tang dynasty, Song dynasty aesthetic` |
| 人物太多/太乱 | `single subject, clean composition, minimal background` |
| 分辨率低 | `ultra detailed, 8K, sharp focus, high resolution` |
| 表情太夸张 | `natural expression, subtle emotion, realistic face` |

---

*整理：虾爬子🦐*
