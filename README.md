# 鸣潮 DLSS5 插件包

鸣潮（Wuthering Waves）可用的 DLSS5 插件，按**显卡代际**打包分发。

## 下载

到 [Releases](https://github.com/y083245/Wuthering-Waves-DLSS5-addon/releases/latest) 页面，下载与你显卡匹配的那**一个**压缩包：

## 这里再附上另外一位大佬所发布的开源项目DLSS5-Swapper

点击 [DLSS5-Swapper](https://github.com/rakanki911/DLSS5-Swapper)，这是一款适用于几乎所有游戏的dlss5一键安装器

| 压缩包 | 适用显卡 | 下载体积 | 解压后 |
| --- | --- | --- | --- |
| `20-30-series.rar` | RTX 20 / 30 系列 | 132.6 MB | 301.7 MB |
| `40-series.rar` | RTX 40 系列 | 119.4 MB | 164.5 MB |
| `50-series.rar` | RTX 50 系列 | 121.0 MB | 164.5 MB |

> 附件名因 GitHub 不支持非 ASCII 字符而使用英文，中文名见各附件的 label。

每个压缩包解压后是一个同名文件夹，内含同一套三个文件，区别只在 `nvngx_dlssnr.dll` 的版本：

- `ReShade_Setup_6.8.0_Addon.exe` — ReShade 6.8.0 安装器（Addon 版本）
- `renodx-dlss5.addon64` — RenoDX 的 DLSS5 addon 插件本体
- `nvngx_dlssnr.dll` — NVIDIA DLSS 光线重建（Ray Reconstruction）运行库

**40 系与 50 系包内的 DLL 文件大小相同但内容不同**（SHA-256 不同），请勿混用。

## 网页助手

仓库内含一个纯 Python 的 Streamlit 应用，提供选包助手、下载校验、安装步骤与常见问题。

本地运行：

```bash
pip install -r requirements.txt
streamlit run app.py
```

装好后浏览器会自动打开 <http://localhost:8501>。

也可以在 [Streamlit Community Cloud](https://share.streamlit.io) 上免费部署：
新建应用时选择本仓库，主文件填 `app.py` 即可。

## 文件校验

所有下载文件的 SHA-256 都列在网页的「文件与校验」页，下载后建议核对一次。
页面也提供粘贴校验功能，把哈希粘进输入框即可判断是否与发布值一致。

## 版权与免责

- `nvngx_dlssnr.dll` 为 NVIDIA 专有二进制文件，版权归 NVIDIA 所有，此处仅作个人使用分发。
- ReShade 版权归 Crosire 及 ReShade 贡献者所有。
- RenoDX 版权归其原作者所有。
- 本仓库与上述任一项目的官方无隶属关系，也不对使用后果作任何担保。

安装前请先备份游戏目录原始文件。
