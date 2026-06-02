# ComfyUI 换脸工作流踩坑记录 (2026-06-02)

---

## 坑1：comfyui_layerstyle IMPORT FAILED

- **现象**：ComfyUI Manager 显示"已安装"但标记为不兼容，节点报错 "Node ID #196 has no class_type"
- **原因**：依赖冲突导致插件加载失败，Manager 的 Apply Changes 无法自动修复
- **解决**：
```cmd
cd C:\Users\home\Documents\ComfyUI\custom_nodes\comfyui_layerstyle
C:\Users\home\Documents\ComfyUI\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 坑2：opencv-python 和 opencv-python-headless 共存冲突

- **现象**：pip check 报冲突
- **原因**：两个 opencv 包不能同时装，会互相覆盖
- **解决**：只保留一个。ComfyUI 用 headless 就够了：
```cmd
pip uninstall opencv-python -y
pip install opencv-python-headless
```

---

## 坑3：升级 facenet-pytorch 意外降级 CUDA torch

- **现象**：跑 `pip install facenet-pytorch --upgrade` 后 torch 从 2.11.0+cu128 变成 2.2.2（CPU版）
- **原因**：facenet-pytorch 声明依赖 torch<2.3，pip 自动降级了
- **解决**：
```cmd
pip install torch==2.11.0+cu128 torchvision==0.26.0+cu128 --index-url https://download.pytorch.org/whl/cu128
pip install facenet-pytorch --no-deps
```
- **教训**：装有严格 torch 版本要求的包时，永远加 `--no-deps`

---

## 坑4：PermissionError install-scripts.txt 被占用

- **现象**：`PermissionError: [WinError 32] 另一个程序正在使用此文件`
- **原因**：ComfyUI Manager 进程占用文件
- **解决**：关闭 ComfyUI → 手动删除文件 → 重启
```cmd
del "C:\Users\home\Documents\ComfyUI\user\__manager\startup-scripts\install-scripts.txt"
```

---

## 坑5：VITMatte 模型下载超时（HuggingFace 国内不可达）

- **现象**：PersonMaskUltra V2 节点报错 `LocalEntryNotFoundError`，连接 huggingface.co 超时
- **解决**：用镜像站下载：
```cmd
set HF_ENDPOINT=https://hf-mirror.com
huggingface-cli download hustvl/vitmatte-small-composition-1k --local-dir "C:\Users\home\Documents\ComfyUI\custom_nodes\ComfyUI_LayerStyle_Advance\models\vitmatte-small-composition-1k" --exclude "*.md" "*.txt"
```
- **注意**：模型名是 `vitmatte-small-composition-1k`，不是 base

---

## 坑6：HDR 视频抽帧灰蒙蒙

- **现象**：视频有 HDR 标志，抽出来的图片色彩暗淡、对比度低
- **原因**：HDR 视频用 BT.2020/PQ 色彩空间，抽帧时没做 tone mapping
- **解决**：ffmpeg 加 tonemap 滤镜：
```cmd
ffmpeg -i 视频.mp4 -vf "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p" -q:v 2 output_%04d.jpg
```

---

## 环境信息

- ComfyUI 路径：`C:\Users\home\Documents\ComfyUI`（使用 .venv）
- GPU：NVIDIA GeForce RTX 3060 12GB
- PyTorch：2.8.0+cu129（ComfyUI .venv）/ 2.11.0+cu128（faceextract conda）
- Python：3.12.11
