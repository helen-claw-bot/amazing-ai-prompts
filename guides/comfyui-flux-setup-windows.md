# ComfyUI + FLUX 本地部署教程（Windows / RTX 3060）

> 适用配置：Windows 11, i7-11700K, 32GB RAM, **RTX 3060 12GB**, 三星 980 PRO 1TB SSD  
> 目标：搭建 AI 影视前期制作工作流（文生图 + 真人换脸 + 角色一致性）  
> 更新日期：2026-05-07

---

## 一、环境要求

| 组件 | 最低要求 | 推荐配置 |
|------|----------|----------|
| 显卡 | NVIDIA 8GB VRAM | RTX 3060 12GB ✅ |
| 内存 | 16GB | 32GB ✅ |
| 存储 | 60GB 可用 | 100GB+ ✅ |
| 系统 | Windows 10/11 | Windows 11 ✅ |

---

## 二、安装 ComfyUI（官方标准安装）

官方 Wiki：https://comfyui-wiki.com/en/install

按官方文档安装完成后：
- 桌面应用位置：`D:\AI\ComfyUI`
- Python 虚拟环境 / 库（含 torch ~7GB）：`C:\Users\<用户名>\Documents\ComfyUI`

> ⚠️ **不要用秋叶整合包**，官方安装更干净，版本更新更可控。

启动后浏览器访问：
```
http://127.0.0.1:8188
```

### 关于内容过滤器

官方安装版本（当前最新）**无内置安全过滤器**，FLUX.1 Dev 本身也无内容审查，影视服装造型等需求直接出图不受限制。

---

## 三、配置模型路径（重要！先做）

**将模型目录指向 D 盘**，避免模型文件占满 C 盘（FLUX 底模 24GB，全套 35GB+）。

### Step 1 — 在 D 盘建模型目录

```
D:\AI\ComfyUI_models\
  ├── checkpoints\
  ├── clip\
  ├── vae\
  ├── loras\
  ├── controlnet\
  └── insightface\
```

### Step 2 — 创建 extra_model_paths.yaml

在 `D:\AI\ComfyUI\` 目录下新建文件 `extra_model_paths.yaml`，内容：

```yaml
my_models:
    base_path: D:\AI\ComfyUI_models
    checkpoints: checkpoints
    clip: clip
    vae: vae
    loras: loras
    controlnet: controlnet
    insightface: insightface
```

### Step 3 — 重启 ComfyUI

重启后 ComfyUI 自动识别 D 盘模型目录 ✅

---

## 四、下载 FLUX 模型

### 所需文件清单（约 35GB）

| 文件 | 大小 | 放置路径 |
|------|------|----------|
| `flux1-dev.safetensors` | ~24GB | `checkpoints\` |
| `ae.safetensors`（VAE） | ~335MB | `vae\` |
| `clip_l.safetensors` | ~246MB | `clip\` |
| `t5xxl_fp16.safetensors` | ~9.8GB | `clip\` |

### 下载来源（推荐国内，无需梯子）

**ModelScope（魔搭）：**
```
https://modelscope.cn/models/black-forest-labs/FLUX.1-dev

# helen实操

pip install modelscope

modelscope download --model black-forest-labs/FLUX.1-dev flux1-dev.safetensors --local_dir D:\\AI\\ComfyUI_models\\checkpoints

modelscope download --model black-forest-labs/FLUX.1-dev ae.safetensors --local_dir D:\\AI\\ComfyUI_models\\vae

modelscope download --model black-forest-labs/FLUX.1-dev  text_encoder_2/model-00001-of-00002.safetensors --local_dir D:\\AI\\ComfyUI_models\\clip

modelscope download --model black-forest-labs/FLUX.1-dev  text_encoder_2/model-00002-of-00002.safetensors --local_dir D:\\AI\\ComfyUI_models\\clip

modelscope download --model Comfy-Org/flux1-dev flux1-dev-fp8.safetensors --local_dir D:\\AI\\ComfyUI_models\\checkpoints

# 下载PuLID
modelscope download --model shiertier/ComfyUI-pulid pulid_flux_v0.9.1.safetensors --local_dir D:\\AI\\ComfyUI_models\\loras

# facexlib 相关的库
modelscope download --model libfishopen/facexlib parsing_bisenet.pth --local_dir  "C:\Users\home\Documents\ComfyUI\models\facexlib"

```

上述四个文件在同一页面均可找到。

**备用：liblib.art**
```
https://www.liblib.art/
```
搜索「FLUX.1 Dev」。

---

## 五、安装换脸 / 角色一致性节点

### 5.1 安装 ComfyUI Manager（必装）

1. 打开 ComfyUI → 点击右上角 `Manager`
2. 若无，手动安装：

```bash
cd D:\AI\ComfyUI\custom_nodes
git clone https://github.com/Comfy-Org/ComfyUI-Manager.git
git clone https://github.com/ltdrdata/ComfyUI-Manager
```

重启 ComfyUI 生效。

### 5.2 安装 PuLID（换脸 + 角色一致性，首选）

通过 Manager 搜索：`ComfyUI PuLID Flux`

或手动：
```bash
cd D:\AI\ComfyUI\custom_nodes
git clone https://github.com/cubiq/PuLID_ComfyUI
```

所需模型：
- `ip-adapter_pulid_flux_v0.9.1.safetensors`（~1.6GB）→ `D:\AI\ComfyUI_models\loras\`
- InsightFace `buffalo_l` → `D:\AI\ComfyUI_models\insightface\models\buffalo_l\`

> PuLID 相比 InstantID 在 FLUX 上兼容性更好，推荐优先使用。

### 5.3 安装 ReActor（换脸节点，备选）

```bash
cd D:\AI\ComfyUI\custom_nodes
git clone https://github.com/Gourieff/comfyui-reactor-node
```

所需模型：
- `inswapper_128.onnx` → `D:\AI\ComfyUI_models\insightface\`

### 5.4 安装 IPAdapter Plus（风格/人脸迁移）

```bash
cd D:\AI\ComfyUI\custom_nodes
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus
```

---

## 六、目录结构总览

```
D:\AI\ComfyUI\                        ← ComfyUI 桌面应用
├── extra_model_paths.yaml            ← 模型路径配置（手动创建）
└── custom_nodes\
    ├── ComfyUI-Manager\
    ├── PuLID_ComfyUI\
    ├── comfyui-reactor-node\
    └── ComfyUI_IPAdapter_plus\

D:\AI\ComfyUI_models\                 ← 所有模型（D盘）
├── checkpoints\  ← flux1-dev.safetensors
├── vae\          ← ae.safetensors
├── clip\         ← clip_l + t5xxl_fp16
├── loras\        ← PuLID、风格 LoRA
├── controlnet\
└── insightface\  ← buffalo_l、inswapper

C:\Users\<用户名>\Documents\ComfyUI\  ← Python 环境（含 torch ~7GB，不动）
```

---

## 七、验证工作流（第一次出图）

1. 启动 ComfyUI → 打开 `http://127.0.0.1:8188`
2. 加载默认工作流（`Load Default`）
3. `CheckpointLoaderSimple` 节点选择 `flux1-dev.safetensors`
4. 输入 prompt，点击 `Queue Prompt`
5. 首次出图约 30-60 秒（模型加载），后续每张约 15-30 秒

---

## 八、AI 影视制作工作流（核心需求）

| 需求 | 方案 | 节点 |
|------|------|------|
| 高质量文生图 | FLUX.1 Dev | 默认工作流 |
| 真人换脸 | ReActor | comfyui-reactor-node |
| 角色一致性（同人不同场景） | PuLID | PuLID_ComfyUI |
| 风格锁定（古风/现代） | IPAdapter | ComfyUI_IPAdapter_plus |
| 定妆照生成 | FLUX + LoRA | 加载对应 LoRA |

---

## 九、常见问题

### Q: 显存不足（OOM）
- FLUX 标准版需要 12GB，RTX 3060 12GB 刚好满足
- 报 OOM 时，在启动参数加 `--fp8` 或 `--lowvram`

### Q: 模型加载失败
- 检查 `extra_model_paths.yaml` 路径是否正确（注意反斜杠）
- 检查文件是否完整下载

### Q: 生成速度慢
- RTX 3060 生成 1024x1024 约 20-40 秒，正常
- 调 prompt 阶段先用 512x512，满意后出大图

---

## 十、资源汇总

| 资源 | 链接 |
|------|------|
| ComfyUI 官方 Wiki | https://comfyui-wiki.com/en/install |
| ComfyUI GitHub | https://github.com/comfyanonymous/ComfyUI |
| FLUX 模型（ModelScope） | https://modelscope.cn/models/black-forest-labs/FLUX.1-dev |
| liblib.art（国内模型站） | https://www.liblib.art |
| ComfyUI Manager | https://github.com/ltdrdata/ComfyUI-Manager |

---

*文档由虾爬子 🦐 整理，基于 RTX 3060 12GB 实际配置*
