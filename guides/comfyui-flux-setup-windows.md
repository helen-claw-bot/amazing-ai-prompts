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

## 二、安装 ComfyUI（秋叶整合包）

### Step 1 — 下载整合包

- 前往 B站 搜索「秋叶 ComfyUI 整合包」
- 官方地址（备用）：https://github.com/aigc-apps/sd-webui-EasyPhoto

推荐使用**秋叶整合包**，已内置 Python 环境、CUDA、常用节点，无需手动配置环境。

### Step 2 — 安装到 D 盘

安装时修改目标路径：
```
D:\AI\ComfyUI
```

> ⚠️ 不要装在 C 盘！模型文件大，会撑爆系统盘。

### Step 3 — 验证安装

安装完成后，运行 `启动ComfyUI.bat`，浏览器自动打开：
```
http://127.0.0.1:8188
```

看到节点编辑界面即安装成功 ✅

---

## 三、下载 FLUX 模型

### FLUX.1 Dev（推荐，质量最高）

**模型文件大小：约 24GB**，需要提前准备好空间。

#### 下载方式一：HuggingFace（需要梯子）
```
https://huggingface.co/black-forest-labs/FLUX.1-dev
```
下载文件：`flux1-dev.safetensors`

#### 下载方式二：ModelScope（国内直连）
```
https://modelscope.cn/models/black-forest-labs/FLUX.1-dev

# helen实操

pip install modelscope

modelscope download --model black-forest-labs/FLUX.1-dev flux1-dev.safetensors --local_dir D:\\AI\\ComfyUI_models\\checkpoints

modelscope download --model black-forest-labs/FLUX.1-dev ae.safetensors --local_dir D:\\AI\\ComfyUI_models\\vae

modelscope download --model black-forest-labs/FLUX.1-dev  text_encoder_2/model-00001-of-00002.safetensors --local_dir D:\\AI\\ComfyUI_models\\clip

modelscope download --model black-forest-labs/FLUX.1-dev  text_encoder_2/model-00002-of-00002.safetensors --local_dir D:\\AI\\ComfyUI_models\\clip


```

#### 下载方式三：liblib.ai（国内，推荐）
```
https://www.liblib.art/
```
搜索「FLUX.1 Dev」，直接下载 safetensors 文件。

### 放置路径

下载完成后，将模型文件放到：
```
D:\AI\ComfyUI\models\checkpoints\flux1-dev.safetensors
```

### 配套 VAE 和 CLIP 模型

FLUX 需要额外的 VAE 和 CLIP 文本编码器：

| 文件 | 放置路径 |
|------|----------|
| `ae.safetensors`（VAE） | `D:\AI\ComfyUI\models\vae\` |
| `clip_l.safetensors` | `D:\AI\ComfyUI\models\clip\` |
| `t5xxl_fp16.safetensors` | `D:\AI\ComfyUI\models\clip\` |

> 💡 以上文件在 HuggingFace / ModelScope 上 FLUX 模型页面均可找到。

---

## 四、安装换脸 / 角色一致性节点

### 4.1 安装 ComfyUI Manager

ComfyUI Manager 是插件管理器，必装。

1. 打开 ComfyUI 界面 → 点击右上角 `Manager`
2. 如果没有，手动安装：

```bash
# 在 ComfyUI\custom_nodes\ 目录下运行
git clone https://github.com/ltdrdata/ComfyUI-Manager
```

重启 ComfyUI 即可看到 Manager 按钮。

### 4.2 安装 InstantID（推荐用于角色一致性）

通过 Manager 搜索安装：`ComfyUI_InstantID`

或手动：
```bash
cd D:\AI\ComfyUI\custom_nodes
git clone https://github.com/cubiq/ComfyUI_InstantID
```

所需额外模型：
- `ip-adapter.bin` → `D:\AI\ComfyUI\models\instantid\`
- InsightFace 人脸检测模型 → `D:\AI\ComfyUI\models\insightface\`

### 4.3 安装 ReActor（换脸节点）

```bash
cd D:\AI\ComfyUI\custom_nodes
git clone https://github.com/Gourieff/comfyui-reactor-node
```

所需模型：
- `inswapper_128.onnx` → `D:\AI\ComfyUI\models\insightface\`

> 📥 inswapper 模型下载：https://github.com/deepinsight/insightface （需梯子，或在 ModelScope 搜索）

### 4.4 安装 IPAdapter Plus（风格/人脸迁移）

```bash
cd D:\AI\ComfyUI\custom_nodes
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus
```

---

## 五、工作流目录结构

```
D:\AI\ComfyUI\
├── models\
│   ├── checkpoints\     ← FLUX.1 Dev、SDXL 等主模型
│   ├── vae\             ← ae.safetensors
│   ├── clip\            ← clip_l、t5xxl
│   ├── loras\           ← LoRA 微调模型
│   ├── instantid\       ← InstantID 模型
│   └── insightface\     ← ReActor 换脸模型
├── custom_nodes\        ← 插件
│   ├── ComfyUI-Manager\
│   ├── ComfyUI_InstantID\
│   ├── comfyui-reactor-node\
│   └── ComfyUI_IPAdapter_plus\
└── output\              ← 生成图片（可改到 E 盘）

E:\AI项目\              ← 素材 + 工程文件
├── 参考图\
├── 模特照片\
├── 分镜\
└── 产出\
```

---

## 六、验证工作流（第一次出图）

1. 启动 ComfyUI，打开 `http://127.0.0.1:8188`
2. 加载默认工作流（`Load Default` 按钮）
3. 在 `CheckpointLoaderSimple` 节点选择 `flux1-dev.safetensors`
4. 输入一段 prompt，点击 `Queue Prompt`
5. 首次出图可能需要 30-60 秒（模型加载），之后每张约 10-30 秒

---

## 七、AI 影视制作工作流（核心需求）

| 需求 | 工具 | 节点 |
|------|------|------|
| 高质量文生图 | FLUX.1 Dev | 默认工作流 |
| 真人换脸 | ReActor | comfyui-reactor-node |
| 角色一致性（同人不同场景） | InstantID + IPAdapter | ComfyUI_InstantID |
| 风格锁定（古风/现代） | IPAdapter | ComfyUI_IPAdapter_plus |
| 定妆照生成 | FLUX + LoRA | 加载对应 LoRA |

---

## 八、常见问题

### Q: 显存不足（OOM）
- FLUX 标准版需要 12GB，RTX 3060 12GB 刚好满足
- 如果报 OOM，在启动参数加 `--lowvram` 或 `--fp8`

### Q: 模型加载失败
- 检查文件路径是否正确
- 检查文件是否完整下载（用 hash 验证）

### Q: 生成速度慢
- RTX 3060 生成 1024x1024 约 20-40 秒，正常
- 可以先用 512x512 调 prompt，满意后再出大图

---

## 九、资源汇总

| 资源 | 链接 |
|------|------|
| ComfyUI 官方 | https://github.com/comfyanonymous/ComfyUI |
| ComfyUI Wiki（中文） | https://comfyui-wiki.com/zh |
| FLUX 模型（ModelScope） | https://modelscope.cn/models/black-forest-labs/FLUX.1-dev |
| liblib.ai（国内模型站） | https://www.liblib.art |
| ComfyUI Manager | https://github.com/ltdrdata/ComfyUI-Manager |

---

*文档由虾爬子 🦐 整理，基于 RTX 3060 12GB 实际配置*
