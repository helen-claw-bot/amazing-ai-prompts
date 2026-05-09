# ComfyUI 多角色场景编排 — 开源方案调研

> 需求：上传多个人物照片 + 多套服装 + 场景图 + 姿势图 → 生成多人穿指定服装、摆指定姿势、在指定场景中的合成图。
>
> 硬件约束：RTX 3060 12GB / Windows 11
>
> 最后更新：2026-05-09

---

## 一、需求分层

| 级别 | 描述 | 典型场景 |
|------|------|---------|
| L1 换脸 | 只替换五官，保留目标图发型/妆容 | 证件照换脸 |
| L2 换头 | 替换五官+发型+头型 | 影视替身 |
| L3 单人角色生成 | 保持人脸ID，自由换服装/场景 | 电商模特、虚拟偶像 |
| L4 多人场景编排 | 多角色×多服装×姿势×场景合成 | 漫画分镜、影视预览、广告 |

---

## 二、核心开源工具

### 2.1 人脸一致性

| 工具 | GitHub | 用途 | 显存 |
|------|--------|------|------|
| **InstantID** | `cubiq/ComfyUI_InstantID` | 单图锁定面部ID，效果最好 | ~6GB |
| **IP-Adapter FaceID** | `cubiq/ComfyUI_IPAdapter_plus` | 多图参考，灵活度高 | ~4GB |
| **PuLID** | `cubiq/ComfyUI_PuLID` | 更自然的面部注入，适配Flux | ~6GB |
| **Reactor** | `Gourieff/comfyui-reactor-node` | 传统换脸，快速但只换五官 | ~2GB |

### 2.2 服装/风格参考

| 工具 | 用途 | 说明 |
|------|------|------|
| **IP-Adapter Plus** | 服装参考图 → 提取风格特征 | 可设权重，多路并行 |
| **ACE++** (`ali-vilab/ACE_plus`) | 万物迁移，自然语言控制 | 支持多参考图 + 文字指令 |
| **ACE++ Redux** | ACE++ + Redux 组合 | 复制/粘贴对象、服装到新场景 |

### 2.3 姿势控制

| 工具 | 用途 |
|------|------|
| **ControlNet OpenPose** | 骨骼图控制人体姿态（支持多人骨骼） |
| **ControlNet Depth** | 深度图控制空间关系 |
| **ControlNet Canny** | 边缘图控制轮廓 |
| **DWPose** | 更精确的姿态估计（替代OpenPose） |

### 2.4 多角色区域控制

| 工具 | GitHub | 说明 |
|------|--------|------|
| **Attention Couple** | `Danand/ComfyUI-ComfyCouple` | 将画面分区，每个区域独立提示词 + 独立ID |
| **Regional Prompter** | 内置/社区节点 | 按mask分区，每区不同提示词 |
| **Civitai 多人工作流** | [链接](https://civitai.com/models/1403746/comfyui) | 现成双/多角色工作流，避免提示词污染 |

### 2.5 一体化编辑

| 工具 | 模型大小 | 说明 | 12GB可跑？ |
|------|---------|------|-----------|
| **Qwen-Image-Edit** | 20B (有量化版) | 自然语言图像编辑，万物迁移 | ✅ 量化版可 |
| **ACE++** | 基于Flux | 多参考图 + 自然语言 | ✅ fp8可 |
| **FLUX Kontext** | 12B | in-context编辑 | ⚠️ 勉强 |

---

## 三、推荐工作流方案

### 方案A：分步合成（最稳定，推荐新手）

```
第1步：单人生成×N
  人物A照片 + 服装1 + 姿势骨骼图
  → InstantID(锁脸) + IP-Adapter(锁服装) + ControlNet OpenPose(锁姿势)
  → 生成透明背景单人图

第2步：场景合成
  环境图 + 所有单人图
  → Inpainting / 图层合成
  → 统一光影色调（img2img精修）
```

优点：每步可控，容错高
缺点：步骤多，光影一致性需手动调

### 方案B：区域提示词一步生成（进阶）

```
双人OpenPose骨骼图（控制位置和姿势）
     ↓
环境图 → IP-Adapter（低权重0.3，控制背景）
     ↓
区域A mask → InstantID(人物A) + IP-Adapter(服装1) + 提示词A
区域B mask → InstantID(人物B) + IP-Adapter(服装2) + 提示词B
     ↓
Attention Couple / Regional Prompter 分区控制
     ↓
RedZ 1.5 / SDXL 生成
```

优点：一步出图，人物交互自然
缺点：调参复杂，对mask精度要求高

### 方案C：ACE++ 万物迁移（最灵活）

```
参考图：人物A照片 + 人物B照片 + 服装1 + 服装2 + 场景图
     ↓
自然语言指令："让人物A穿上服装1站在左边，人物B穿上服装2站在右边，
              两人在这个场景中面对面站立"
     ↓
ACE++ 生成
```

优点：自然语言控制，最灵活
缺点：多人场景效果不稳定，可能需要多次生成

---

## 四、现成工作流资源

### 4.1 多人角色一致性

| 来源 | 链接 | 说明 |
|------|------|------|
| **Civitai 多人工作流** | https://civitai.com/models/1403746/comfyui | 双角色独立生成，避免提示词污染，支持LoRA角色 |
| **VisionPaletteAI 双角色工作流** | https://visionpaletteai.com/products/comfyui-dual-character-workflow-guide | 区域控制 + Wildcards随机切换动作/服装/表情 |
| **camenduru 一致性工作流** | [GitHub JSON](https://github.com/camenduru/comfyui-colab/blob/main/workflow/InstantID_IPAdapter_ControlNet_FaceDetailer.json) | InstantID + IP-Adapter + ControlNet + FaceDetailer 组合 |

### 4.2 换脸/换头

| 来源 | 链接 | 说明 |
|------|------|------|
| **Flux.2 Klein 换头工作流** | https://www.runninghub.cn/post/2026220875019718658 | 零违和感换头换脸 |
| **ACE++ 换脸工作流** | https://www.runcomfy.com/comfyui-workflows/ace-plus-plus-face-swap | 自然语言控制换脸 |
| **ACE++ Redux 万物迁移** | https://myaiforce.com/ace-plus-inpainting/ | 复制/粘贴对象、服装到新场景 |
| **Reddit BFS 换脸** | https://reddit.com/r/comfyui/comments/1o1ui2u/ | Qwen-Image-Edit 2509 + 换头LoRA，被评为"Best Face Swap" |

### 4.3 角色一致性（单人多场景）

| 来源 | 链接 | 说明 |
|------|------|------|
| **RunComfy 一致性角色** | https://www.runcomfy.com/comfyui-workflows/create-consistent-characters-within-comfyui | IPAdapter + InstantID + ControlNet 完整教程 |
| **IP-Adapter FaceID Plus** | https://www.runcomfy.com/comfyui-workflows/create-consistent-characters-in-comfyui-with-ipadapter-faceid-plus | 角色设计一致性 |
| **Multi-Image + FLUX PuLID** | https://comfyui.org/en/mastering-multi-image-face-swapping-portraits | 多图合成 + 换脸 + 4x放大 |

### 4.4 资料合集

| 来源 | 链接 |
|------|------|
| **夸克网盘全量资料** | https://pan.quark.cn/s/3288b8fbb8c0 |
| **RunningHub 邀请码** | rh-v1256（领1000 RH币） |

---

## 五、所需 ComfyUI 插件清单

```
# 核心插件
cubiq/ComfyUI_InstantID          # 人脸ID保持
cubiq/ComfyUI_IPAdapter_plus     # 风格/服装参考（已转官方维护 comfyorg/comfyui-ipadapter）
Gourieff/comfyui-reactor-node    # 快速换脸
ali-vilab/ACE_plus               # ACE++ 万物迁移
Fannovel16/comfyui_controlnet_aux # ControlNet 预处理（OpenPose/DWPose/Depth等）

# 区域控制
Danand/ComfyUI-ComfyCouple       # Attention Couple 多角色分区

# 增强
cubiq/ComfyUI_PuLID              # PuLID 面部注入（Flux架构）
ltdrdata/ComfyUI-Impact-Pack     # FaceDetailer 面部精修
```

---

## 六、所需模型文件

```
models/instantid/
  ip-adapter.bin                              # InstantID adapter

models/ipadapter/
  ip-adapter-faceid-plusv2_sdxl.bin           # FaceID Plus v2
  ip-adapter-plus_sdxl_vit-h.safetensors     # IP-Adapter Plus（服装/风格参考）

models/insightface/models/antelopev2/
  1k3d68.onnx, 2d106det.onnx, genderage.onnx,
  glintr100.onnx, scrfd_10g_bnkps.onnx       # InsightFace 人脸检测模型

models/controlnet/
  control-lora-openposeXL2-rank256.safetensors  # OpenPose（或 DWPose）
  control-lora-depth-rank256.safetensors         # Depth

models/checkpoints/
  RedZ 1.5 fp8 (已有)                          # 基础生图模型
  flux-2-klein-4b-fp8.safetensors (已有)        # 轻量换头
```

---

## 七、RTX 3060 12GB 显存规划

| 任务 | 预估显存 | 说明 |
|------|---------|------|
| RedZ 1.5 fp8 文生图 | ~6GB | 基础生图 |
| + InstantID | ~8GB | 加锁人脸 |
| + IP-Adapter (1路) | ~9GB | 加服装参考 |
| + ControlNet OpenPose | ~10GB | 加姿势控制 |
| + Attention Couple (2区) | ~11GB | 双角色分区 |
| **总计（双角色满配）** | **~11GB** | **勉强可跑，建议关其他程序** |

> ⚠️ 三人以上场景建议用方案A分步合成，避免一次性加载太多模型爆显存。

---

## 八、下一步行动

1. [ ] 安装 InstantID + IP-Adapter 插件
2. [ ] 下载 antelopev2 + ip-adapter 模型
3. [ ] 跑通单人角色生成（L3）
4. [ ] 尝试 Civitai 双角色工作流
5. [ ] 测试 ACE++ 万物迁移
