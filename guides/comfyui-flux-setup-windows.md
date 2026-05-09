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

启动后浏览器访问：
```
http://127.0.0.1:8000
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
  ├── pulid\
  └── insightface\
```

### Step 2 — 创建 extra_model_paths.yaml(⚠️ 实际没有起作用)

在 `D:\AI\ComfyUI\` 目录下新建文件 `extra_model_paths.yaml`，内容：

```yaml
my_models:
    base_path: D:\AI\ComfyUI_models
    checkpoints: checkpoints
    clip: clip
    vae: vae
    loras: loras
    controlnet: controlnet
    pulid: pulid
    insightface: insightface
```
✅ 软链接到C盘 ComfyUI 工作路径下

### Step 3 — 重启 ComfyUI

重启后 ComfyUI 自动识别 D 盘模型目录 ✅

---

## 四、下载 FLUX 模型

### 所需文件清单（约 35GB）

| 文件 | 大小 | 放置路径 |
|------|------|----------|
| `flux1-dev.safetensors` | ~24GB | `checkpoints\` |
| `flux1-dev-fp8.safetensors ` | ~16GB | `checkpoints\` |
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
modelscope download --model shiertier/ComfyUI-pulid pulid_flux_v0.9.1.safetensors --local_dir D:\\AI\\ComfyUI_models\\pulid

# facexlib 相关的库
modelscope download --model libfishopen/facexlib parsing_bisenet.pth --local_dir  "C:\Users\home\Documents\ComfyUI\models\facexlib"

```

---

## 五、安装换脸 / 角色一致性节点

### 5.0 激活 ComfyUI 虚拟环境

ComfyUI 的 Python 虚拟环境位于 `C:\Users\home\Documents\ComfyUI\.venv`，需要安装额外 Python 包时先激活：

**PowerShell：**
```powershell
C:\Users\home\Documents\ComfyUI\.venv\Scripts\Activate.ps1

C:\Users\home\Documents\ComfyUI\.venv\Scripts\activate

Get-Command python
>> C:\Users\home\Documents\ComfyUI\.venv/Scripts\python.exe 

(ComfyUI) PS C:\Users\home\Documents\ComfyUI\.venv\Scripts> python -m pip install "numpy==1.26.4" 
(ComfyUI) PS C:\Users\home\Documents\ComfyUI\.venv\Scripts> python -m pip install "opencv-python==4.7.0.72" 

(ComfyUI) PS C:\Users\home\Documents\ComfyUI\.venv\Scripts> python -m pip show opencv-python

更新镜像站
python -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
>> Writing to C:\Users\home\AppData\Roaming\pip\pip.ini
```

**CMD：**
```cmd
C:\Users\home\Documents\ComfyUI\.venv\Scripts\activate.bat
```

激活后命令行前缀会变成 `(.venv)`，再执行 `pip install` 即可。

> ⚠️ PowerShell 若报"执行策略"错误，先运行一次：
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

---

### 5.1 安装 ComfyUI Manager（必装）

1. 打开 ComfyUI → 点击右上角 扩展商店 `Extensions`
2. 若无，手动安装：

```bash
cd D:\AI\ComfyUI\custom_nodes
git clone https://github.com/Comfy-Org/ComfyUI-Manager.git
```
重启 ComfyUI 生效。

### 5.2 安装 PuLID（换脸 + 角色一致性，首选）

通过 Manager 搜索：`ComfyUI PuLID Flux`

或手动：
```bash
cd D:\AI\ComfyUI\custom_nodes
git clone https://github.com/lldacing/ComfyUI_PuLID_Flux_ll.git
```

### 5.3 安装 ReActor（换脸节点，备选）

> ✅ 新版 ReActor 已重写核心，**不再依赖 InsightFace Python 库**，也不需要 C++ Build Tools，安装大幅简化。

**安装方式一：ComfyUI Manager**
搜索 `ReActor` 直接安装。

**安装方式二：手动**
```bash
cd D:\AI\ComfyUI\custom_nodes
git clone https://github.com/Gourieff/ComfyUI-ReActor
cd ComfyUI-ReActor
install.bat
```

**所需模型（install.bat 会自动下载，国内网络可能超时需手动补）：**

| 模型 | 路径 | 说明 |
|------|------|------|
| `inswapper_128.onnx` | `models\insightface\` | 主换脸模型（默认） |
| `buffalo_l`（5x .onnx） | `models\insightface\models\buffalo_l\` | 人脸识别，首次启动自动下 |
| `GFPGANv1.4.pth` | `models\facerestore_models\` | **必须手动下载**，否则启动时联网超时导致节点加载失败 |

手动下载地址（国内用 hf-mirror）：
```
https://hf-mirror.com/datasets/Gourieff/ReActor/resolve/main/models/facerestore_models/GFPGANv1.4.pth
```

> ⚠️ **重要：** ReActor 启动时会检查 `models\facerestore_models\` 目录，若为空则自动联网下载。国内网络会超时，导致所有 ReActor 节点加载失败（报 `URLError`）。必须提前手动放入至少一个 face restore 模型。

**可选增强模型：**
- `codeformer-v0.1.0.pth` → `models\facerestore_models\`（细节更锐利，与 GFPGAN 二选一对比）
- ReSwapper（inswapper 替代）: `models\reswapper\`
- HyperSwap（高分辨率换脸，推荐）: `models\hyperswap\`

**换脸模型对比：**

| 模型 | 分辨率 | 效果 | 路径 |
|------|--------|------|------|
| `inswapper_128.onnx` | 128px | 通用，速度快 | `models\insightface\` |
| `hyperswap_1b_256.onnx` | 256px | 细节更好，推荐 | `models\hyperswap\` |
| `reswapper_256.onnx` | 256px | inswapper 改进版 | `models\reswapper\` |

> 💡 HyperSwap 文件实际存放在 `D:\AI\ComfyUI_models\insightface\`，用 Junction 软链接映射：
> ```powershell
> New-Item -ItemType Junction -Path "C:\Users\home\Documents\ComfyUI\models\hyperswap" -Target "D:\AI\ComfyUI_models\insightface"
> ```

**ReActor 节点说明：**

| 参数 | 建议值 | 说明 |
|------|--------|------|
| `swap_model` | `hyperswap_1b_256.onnx` | 换脸主模型，优先用 hyperswap |
| `face_restore_model` | `GFPGANv1.4.pth` | 换脸后修复画质 |
| `face_restore_visibility` | `0.7` | 修复强度，过高会有塑料感 |
| `detect_gender_input/source` | 按实际设置 | 换男性演员记得改为 male |
| `input/source_faces_index` | `0` | 多人图时指定第几张脸（0=第一张） |

**Face Booster 节点（可选，进一步提升清晰度）：**

| 参数 | 建议值 | 说明 |
|------|--------|------|
| `visibility` | `0.8` | Boost 强度，过高会过度锐化 |
| `interpolation` | `Lanczos` | 缩放算法，保持默认 |

**注意：ReActor 只替换皮肤纹理和五官，不改变脸型轮廓。** 需要换脸型请用 PuLID（生成阶段注入身份）。

**NSFW 检测器（默认开启）：**
检测到裸露内容会跳过该帧。如需关闭，编辑 `nodes.py`，找到：
```python
if not sfw.nsfw_image(img_byte_arr, NSFWDET_MODEL_PATH):
    pil_images_sfw.append(img)
```
将 `if` 那行注释掉，`append` 行保留（去掉缩进或保持原缩进均可）。

### 5.4 安装 IPAdapter Plus（风格/人脸迁移）

```bash
cd D:\AI\ComfyUI\custom_nodes
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus
```

### 各种库的关系

InsightFace作用是认人
```
InsightFace
├── antelopev2（模型包）
│   ├── scrfd（找脸）
│   ├── landmark（对齐五官）
│   └── buffalo_l（认人/提取人脸向量）

```

总的来说，
- InsightFace(antelopev2（模型包）) = 认出这是谁，看骨相
- EVA_CLIP = 看参考图细节/感觉,看气质和细节 (EVA02_CLIP_L_336_psz14_s6B.pt )
- facexlib = 帮忙分清脸部区域，哪里是脸（人脸识别模型retinaface_resnet50，和解析模型bisenet）
- PuLID = 把身份信息塞进 FLUX （pulid_flux_vXXX.safetensors）
- FLUX = 真正生图模型 
- KSampler = 控制画图过程 (ComfyUI内建节点)
- VAE = 把 latent 变成图片 （模型语言翻译成可视化图片）



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

## 常见坑与解决方案（PuLID FLUX 安装）

### 坑1：T5-XXL 文本编码器加载失败
**错误：** `RuntimeError: mat1 and mat2 shapes cannot be multiplied (256x4096 and 10240x4096)`  
**原因：** ModelScope 的 FLUX.1-dev 仓库里 t5xxl 是分片文件（model-00001-of-00002），ComfyUI 无法直接加载。  
**解决：** 从 HuggingFace `comfyanonymous/flux_text_encoders` 下载单文件版：
- `t5xxl_fp16.safetensors`（~9.8GB）
- `clip_l.safetensors`（~246MB）

放到 `D:\AI\ComfyUI_models\clip\`

DualCLIPLoader 配置：`clip_name1 = t5xxl_fp16.safetensors`，`clip_name2 = clip_l.safetensors`

---

### 坑2：InsightFace 联网验证失败
**错误：** `requests.exceptions.ConnectTimeout: HTTPSConnectionPool(host='github.com')`  
**原因：** InsightFace 每次加载都会先联网验证模型完整性，国内连不上 GitHub 就直接失败，即使本地文件完整也不用。  
**解决：** 修改 insightface 库的 storage.py，在 `download()` 函数开头加本地目录检测：

文件路径：`C:\Users\home\Documents\ComfyUI\.venv\Lib\site-packages\insightface\utils\storage.py`

```python
def download(sub_dir, name, force=False, root='~/.insightface'):
    _root = os.path.expanduser(root)
    dir_path = os.path.join(_root, sub_dir, name)
    if os.path.exists(dir_path) and not force:
        return dir_path
    # ... 原来的代码继续
```

模型文件手动放到：`C:\Users\home\.insightface\models\buffalo_l\` 和 `C:\Users\home\.insightface\models\antelopev2\`

---

### 坑3：antelopev2 下载地址
**原因：** InsightFace 官方 GitHub release 在国内访问不稳定。  
**正确的 ModelScope 源：** `https://modelscope.cn/models/AI-ModelScope/antelopev2/files`  
下载所有 `.onnx` 文件放到 `C:\Users\home\.insightface\models\antelopev2\`

---

### 坑4：EVA-CLIP 模型路径
**原因：** PuLID 的 EVA-CLIP 加载器用 `folder_paths.get_full_path("text_encoders", ...)` 查找，找不到就去 `models/clip` 目录，不会从 insightface 目录读。  
**解决：** 把 `EVA02_CLIP_L_336_psz14_s6B.pt`（~3.5GB）放到：
```
C:\Users\home\Documents\ComfyUI\models\clip\EVA02_CLIP_L_336_psz14_s6B.pt
```
ModelScope 下载源：`https://modelscope.cn/models/QuanSun/EVA-CLIP/files`

---

### 坑5：facexlib 人脸检测模型联网下载
**错误：** `Downloading: "https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth"`  
**原因：** PuLID 的 Apply 节点依赖 facexlib，首次运行会从 GitHub 自动下载检测模型。  
**解决：** 手动下载后放到正确位置：
- 文件：`detection_Resnet50_Final.pth`（~109MB）
- ModelScope 源：`https://modelscope.cn/models/jackychoulab/facexlib/files`
- 目标路径：`C:\Users\home\Documents\ComfyUI\models\facexlib\`

---

### PuLID FLUX 完整模型清单

| 文件 | 大小 | 路径 | 来源 |
|------|------|------|------|
| flux1-dev.safetensors | ~24GB | models\checkpoints\ | ModelScope |
| ae.safetensors | ~335MB | models\vae\ | ModelScope |
| t5xxl_fp16.safetensors | ~9.8GB | models\clip\ | HuggingFace |
| clip_l.safetensors | ~246MB | models\clip\ | HuggingFace |
| pulid_flux_v0.9.1.safetensors | ~1.6GB | models\pulid\ | ModelScope |
| EVA02_CLIP_L_336_psz14_s6B.pt | ~3.5GB | models\clip\ | ModelScope |
| antelopev2 (5x .onnx) | ~440MB | .insightface\models\antelopev2\ | ModelScope |
| buffalo_l (5x .onnx) | ~340MB | .insightface\models\buffalo_l\ | ModelScope |
| detection_Resnet50_Final.pth | ~109MB | models\facexlib\ | ModelScope |


---

### 坑6：PuLID 插件与新版 ComfyUI 不兼容（latent_shapes 参数）
**错误：** `TypeError: pulid_outer_sample_wrappers_with_override() got an unexpected keyword argument 'latent_shapes'`  
**原因：** ComfyUI 新版本在采样器调用时加入了 `latent_shapes` 参数，但 PuLID 插件（comfyui_pulid_flux_ll v1.1.4，最后更新 2025-02-19）的函数签名没有接收这个参数。  
**解决：** 手动修改插件源码，在函数定义里加 `**kwargs`：

文件路径：`C:\Users\home\Documents\ComfyUI\custom_nodes\comfyui_pulid_flux_ll\pulidflux.py`

搜索 `pulid_outer_sample_wrappers_with_override`，找到函数定义，在 `seed=None` 后面加 `, **kwargs`：

```python
# 改前
def pulid_outer_sample_wrappers_with_override(wrapper_executor, noise, latent_image, sampler, sigmas, denoise_mask=None, callback=None, disable_pbar=False, seed=None):

# 改后
def pulid_outer_sample_wrappers_with_override(wrapper_executor, noise, latent_image, sampler, sigmas, denoise_mask=None, callback=None, disable_pbar=False, seed=None, **kwargs):
```

保存后重启 ComfyUI 即可。



## huggingface setup

> 使用 python api 下载，速度可达 15.7MB/s

```python
pip install --upgrade huggingface_hub

from huggingface_hub import hf_hub_download

hf_hub_download(
    repo_id="black-forest-labs/FLUX.2-klein-4b-fp8",
    filename="flux-2-klein-4b-fp8.safetensors",
    local_dir="D:/AI/ComfyUI_models/checkpoints/"
)


hf_hub_download(
    repo_id="skbhadra/ClearRealityV1",
    filename="4x-ClearRealityV1.pth",
    local_dir="D:/AI/ComfyUI_models/upscale_models/"
)





```


# 超分辨率模型

```python
from huggingface_hub import hf_hub_download

hf_hub_download(
    repo_id="skbhadra/ClearRealityV1",
    filename="4x-ClearRealityV1.pth",
    local_dir="D:/AI/ComfyUI_models/upscale_models/"
)

```

```bash
New-Item -ItemType Junction -Path "C:\Users\home\Documents\ComfyUI\models\upscale_models" -Target "D:\AI\ComfyUI_models\upscale_models"

New-Item -ItemType SymbolicLink -Path "C:\Users\home\Documents\ComfyUI\models\upscale_models" -Target "D:\AI\ComfyUI_models\upscale_models"

```

---

## 十一、RedZ 1.5 / ERNIE RedMIX Text2Image 测试

> 测试日期：2026-05-09 | RTX 3060 12GB 环境

### 红潮（RedCraft）系列模型谱系

**红潮（RedCraft）** 是由社区作者 AiMetatron（光元）开发的图像生成模型系列，在高质量基底模型上进行 SFT（有监督微调），解锁更多风格和生成自由度。

Civitai 页面：https://civitai.com/models/958009/redcraft-or-or-ernie-redmix

#### 基底模型演进

| 代系 | 基底模型 | 架构 | 参数量 | 开发方 |
|------|---------|------|--------|--------|
| **RedZ v1.0~v1.5**（旧版） | **Z-Image / Z-Image-Turbo** | 单流 DiT（Diffusion Transformer） | 6B | 通义万相（阿里 Tongyi-MAI） |
| **ERNIE RedMIX**（最新） | **ERNIE-Image** | 单流 DiT | 8B | 百度 ERNIE-Image 团队 |

**Z-Image 系列**（阿里通义万相）：
- **Z-Image**（ZI）：基础模型，50步，支持 CFG，高多样性
- **Z-Image-Turbo**（ZIT）：蒸馏加速版，仅需 8 步，无 CFG，画质极高但多样性较低
- **Z-Image-Base**（ZIB）：社区底座模型，适合微调
- **Z-Image-Omni-Base**：同时支持生成和编辑
- **Z-Image-Edit**：专注图像编辑

HuggingFace：https://huggingface.co/Tongyi-MAI/Z-Image-Turbo

**ERNIE-Image**（百度）：
- 8B DiT 参数，Apache 2.0 开源
- 使用 **Qwen3** 作为文本编码器（不是 T5XXL）
- 原生支持中英文双语
- 文本渲染能力在开源模型中领先

#### RedCraft 在基底上的微调版本

| 缩写 | 全称 | 含义 |
|------|------|------|
| **RedZ** | Red Z-Image | 基于 Z-Image 的红潮微调 |
| **RedZiT** | Red Z-Image-Turbo | 基于 ZIT（Turbo 加速版）的微调 |
| **RedZDX** | Red Z-Image Distilled X | 蒸馏版，更快更小 |
| **ERNIE RedMIX** | ERNIE Red Mixed | 基于 ERNIE-Image 的混合精度微调（最新） |

---

### 模型文件命名解读

以 `RedZDX-ZIB-Distilled-nocfg-10steps-fp8-e4m3fn-Diffusion-models.safetensors` 为例：

| 字段 | 含义 |
|------|------|
| **RedZDX** | RedCraft Z-Image Distilled X（蒸馏版微调） |
| **ZIB** | Z-Image Base（基于 Z-Image 基底） |
| **Distilled** | 蒸馏加速（更少步数即可出图） |
| **nocfg** | 不需要 CFG（Classifier-Free Guidance），设 CFG=1 即可 |
| **10steps** | 推荐 10 步即可出图 |
| **fp8** | FP8 量化精度（约为 BF16 的一半体积） |
| **e4m3fn** | FP8 具体格式（4 位指数 + 3 位尾数） |
| **Diffusion-models** | 仅含 DiT/UNet 权重，**不含 CLIP 和 VAE**，需分离加载 |
| **AIO** | All-In-One，包含 DiT + CLIP + VAE 的完整包 |
| **Checkpoints** | 完整检查点格式（可用 CheckpointLoaderSimple 加载） |
| **BF16** | BFloat16 全精度（最高质量，最大体积） |
| **FP8mixed** | 混合精度（部分层 FP8，部分层 FP16） |

---

### 不同版本的设备要求

| 版本类型 | 文件大小 | 最低显存 | 推荐显存 | 适用场景 |
|---------|---------|---------|---------|---------|
| **BF16 AIO**（全精度完整包） | ~17-20 GB | 24 GB | 32+ GB | 4090 / A100 等高端卡 |
| **FP8mixed AIO**（混合精度完整包） | ~17 GB | 16 GB | 24 GB | 3090 / 4080 |
| **FP8 Diffusion-only**（量化仅模型） | ~5.7 GB | **8 GB** | **12 GB** | **RTX 3060 12GB ✅** |
| **NVFP4**（4 位量化） | ~3-4 GB | 6 GB | 8 GB | Blackwell 架构 GPU（50系） |

> ⚠️ Diffusion-only 版本还需额外加载 Text Encoder（~2-5 GB）和 VAE（~300 MB）

---

### 坑7：ERNIE RedMIX 模型加载方式（重要！）

ERNIE RedMIX 基于 ERNIE-Image 架构，**不是标准 Flux**，加载方式完全不同。

#### ❌ 错误方式

| 尝试 | 结果 |
|------|------|
| `CheckpointLoaderSimple` 加载 AIO | CLIP 输出为 **None** |
| `DualCLIPLoader` + clip_l + t5xxl | `RuntimeError: normalized_shape=[2560], got [2, 256, 4096]` |
| `DualCLIPLoader` + clip_l + qwen3 | `RuntimeError: normalized_shape=[2560], got [1, 512, 7680]` |

**原因：** ERNIE-Image 使用**单文本编码器** Qwen3（不是 Flux 的双编码器 clip_l + t5xxl），维度完全不同。

#### ✅ 正确方式：三件套分离加载

1. **UNETLoader**（Load Diffusion Model）
   - 模型：`redcraftERNIERedmix_redzit15AIO.safetensors`（或 fp8 Diffusion-only 版）
   - weight_dtype：`default`

2. **CLIPLoader**（单个 Load CLIP，**不是 DualCLIPLoader！**）
   - clip_name：`qwen3_4b_fp8_scaled.safetensors`
   - type：根据实际版本选择
   ```python
   hf_hub_download(
    repo_id="jiangchengchengNLP/qwen3-4b-fp8-scaled",
    filename="qwen3_4b_fp8_scaled.safetensors",
    local_dir="D:/AI/ComfyUI_models/clip/"
    )
   ```

3. **VAELoader**
   - vae_name：`ae.safetensors`（标准 Flux.1 16C VAE，~319 MB，与 FLUX.1 共用）

---

### 所需文件清单

| 文件 | 用途 | 放置路径 | 大小 | 来源 |
|-----|------|---------|------|------|
| `redcraftERNIERedmix_redzit15AIO.safetensors`（或 fp8 Diffusion） | 主模型 | `models/checkpoints/` 或 `models/diffusion_models/` | 5.7~17 GB | Civitai |
| `qwen3_4b_fp8_scaled.safetensors` | 文本编码器 | `models/clip/` | ~2-5 GB | Civitai |
| `ae.safetensors` | VAE 解码器 | `models/vae/` | ~319 MB | 已有（同 FLUX.1） |

---

### 推荐采样参数

| 参数 | 推荐值 |
|------|--------|
| 采样器 | **EULER** 或 **DEIS** |
| 调度器 | **Simple** |
| CFG | **1** |
| 步数 | **10** |

---

### 测试结果

✅ **RedZ 1.5 ERNIE RedMIX 在 RTX 3060 12GB 上成功运行**

- 画面质量和细节明显优于 FLUX.1 Dev
- 支持中文提示词直接输入（Qwen3 编码器原生支持中英双语）
- 出图速度理想 50-80s
- FP8 Diffusion-only 版显存占用友好
- ⭐当前出图质量最佳 (2026-05-09)
- ⭐当前NSFW适配最佳 (2026-05-09)


❌️ Klein 4B 生成的人物失真过于严重，眼睛/五官细节丢失过多。因此不考虑使用该模型。