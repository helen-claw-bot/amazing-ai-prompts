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
modelscope download --model shiertier/ComfyUI-pulid pulid_flux_v0.9.1.safetensors --local_dir D:\\AI\\ComfyUI_models\\pulid

# facexlib 相关的库
modelscope download --model libfishopen/facexlib parsing_bisenet.pth --local_dir  "C:\Users\home\Documents\ComfyUI\models\facexlib"

```

上述四个文件在同一页面均可找到。


#### 配置model软连接

```bash
cmd /c mklink /J "C:\Users\home\Documents\ComfyUI\models\facexlib" "D:\AI\ComfyUI_models\facexlib"
```


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



## PuLID

PuLID 是一个角色/人脸保持的方案/模型


#### facexlib 人脸工具库(脸部检测)

path: `C:\Users\home\Documents\ComfyUI\.venv\Lib\site-packages\facexlib\`


#### insightface identity recognization（认人）

`ComfyUI/models/insightface/models/antelopev2/`

问题: antelopev2 是insightface v0.7 (2022发布) 过时很久了

#### EVA_CLIP


```
https://huggingface.co/QuanSun/EVA-CLIP/blob/main/EVA02_CLIP_L_336_psz14_s6B.pt

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
| pulid_flux_v0.9.1.safetensors | ~1.6GB | models\loras\ | HuggingFace |
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

