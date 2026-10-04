"""鸣潮 DLSS5 插件包 · 下载与安装助手

一个纯 Python 的 Streamlit 单页应用：帮用户挑对显卡代际的压缩包、核对下载文件的
完整性、查看安装步骤与常见问题。

运行：
    pip install -r requirements.txt
    streamlit run app.py
"""

from __future__ import annotations

import hashlib
import re

import altair as alt
import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #

REPO = "y083245/Wuthering-Waves-DLSS5-addon"
TAG = "v1.0.0"
RELEASE_URL = f"https://github.com/{REPO}/releases/tag/{TAG}"

# 三包共用的两个文件（与显卡代际无关）
SHARED_FILES = [
    {
        "name": "ReShade_Setup_6.8.0_Addon.exe",
        "size": 4_318_424,
        "sha256": "afe4c8f13048306307983b8b3d41d5bf00a86820440b0e57dea10950e1176445",
        "desc": "ReShade 6.8.0 安装器（Addon 版本，支持加载 addon 插件）",
    },
    {
        "name": "renodx-dlss5.addon64",
        "size": 2_350_592,
        "sha256": "11a32eaac9d2ee8edbe8f33b6d8e0f17b8941c080a6c50789d5316165bc5ec6a",
        "desc": "RenoDX 的 DLSS5 addon 插件本体",
    },
]

PACKAGES = [
    {
        "key": "20-30",
        "label": "20-30系显卡",
        "file": "20-30-series.rar",
        "gpus": "RTX 20 系列 / RTX 30 系列",
        "download_size": 139_055_924,
        "sha256": "e020ca70ae5b29c407661ec11b3a8445dc645996727e5f27174868de30a14d9f",
        "dll_size": 309_671_536,
        "dll_sha256": "6dac1b40f0c87af84a8177b18c741e84fb0c914f204c9d87d95916b665ba3af8",
        "dll_note": "295 MiB，明显大于另外两包，这是该包体积更大的原因",
    },
    {
        "key": "40",
        "label": "40系显卡",
        "file": "40-series.rar",
        "gpus": "RTX 40 系列",
        "download_size": 125_199_763,
        "sha256": "9b8d954ad975d262d495c27245647a20e983078277dd503efd84fc95d165c5b3",
        "dll_size": 165_840_496,
        "dll_sha256": "214ffc2ba081b66ce7f3eb50aee9eaae4d01c55b6a9b3cca4bb66bbeaabac6ca",
        "dll_note": "158 MiB。与 50 系包字节数相同，但内容不同，请勿混用",
    },
    {
        "key": "50",
        "label": "50系显卡",
        "file": "50-series.rar",
        "gpus": "RTX 50 系列",
        "download_size": 126_880_345,
        "sha256": "c96614f59df15b4100b85e990489ac29bd9d2dc9091b1b9a533f8b5e7b1abcef",
        "dll_size": 165_840_496,
        "dll_sha256": "24f2d48e83ee636c8efc05056bbed61daf91bc35e490198485929ebd0d824dd2",
        "dll_note": "158 MiB。与 40 系包字节数相同，但内容不同，请勿混用",
    },
]

RELEASE_ASSET_BASE = f"https://github.com/{REPO}/releases/download/{TAG}"

# 图表配色。取 dataviz 参考调色板的前两个 slot，已用 validate_palette.js 校验：
# CVD ΔE 24.7 / 常视 ΔE 33.6 / 对比度均 ≥3:1，五项检查全 PASS。
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
SERIES = {
    "下载体积": "#2a78d6",    # slot 1 blue
    "解压后体积": "#eb6834",  # slot 2 orange
}
MEASURE_ORDER = ["下载体积", "解压后体积"]

# 安装步骤。作者可按实际情况修改这一段，页面会自动跟着变。
BACKUP_NOTE = "动手之前先整个备份游戏目录（或至少备份被覆盖的原文件），出问题能立刻还原。"

INSTALL_STEPS = [
    (
        "备份游戏目录",
        "把鸣潮的游戏安装目录整体复制一份留底。mod 类操作最常见的翻车都是覆盖了原文件又没留备份。",
    ),
    (
        "确认自己的显卡代际",
        "选包助手页可以帮你确认。选错代际的包大概率表现为游戏起不来、画面异常或 DLSS 选项消失。",
    ),
    (
        "解压对应代际的压缩包",
        "解压后是一个与压缩包同名的文件夹，里面有 nvngx_dlssnr.dll、renodx-dlss5.addon64、"
        "ReShade_Setup_6.8.0_Addon.exe 三个文件。",
    ),
    (
        "运行 ReShade 安装器",
        "运行 ReShade_Setup_6.8.0_Addon.exe，按提示选择鸣潮的游戏主程序（Wuthering Waves.exe），"
        "并选择游戏实际使用的图形 API（DirectX 10/11/12 视版本而定）。",
    ),
    (
        "放置 addon 与 DLSS 库文件",
        "把 renodx-dlss5.addon64 和 nvngx_dlssnr.dll 按你所用教程指定的位置放进游戏目录。"
        "不同游戏版本目录结构可能不同，以你参考的教程为准。",
    ),
    (
        "游戏内启用",
        "进入游戏后按 Home 键呼出 ReShade 界面，在 addon 列表里启用 DLSS5 相关项，"
        "再在游戏画面设置里打开 DLSS。",
    ),
]

FAQ = [
    (
        "40 系和 50 系的包大小一样，是同一个文件吗？",
        "不是。两个包里的 nvngx_dlssnr.dll 都是 165,840,496 字节，但 SHA-256 不同"
        "（40 系 214ffc2b 开头，50 系 24f2d48e 开头），是两个不同的构建。请按自己的显卡代际下载，不要混用。",
    ),
    (
        "20-30 系的包为什么大这么多？",
        "因为该包内的 nvngx_dlssnr.dll 是 295 MiB，而 40 系和 50 系包内的是 158 MiB。"
        "压缩包本身体积的差距（132.6 MB vs 119.4 / 121.0 MB）也来自这里。",
    ),
    (
        "怎么确认我的显卡是哪一代？",
        "Windows 下按 Win+R 输入 dxdiag，在「显示」标签页看显卡型号；"
        "或按 Ctrl+Shift+Esc 打开任务管理器，「性能」→「GPU」页也能看到。型号里的前两位数字即代际，"
        "例如 RTX 4070 属于 40 系。",
    ),
    (
        "下载后怎么校验文件没坏？",
        "在「文件与校验」页把下载到的压缩包 SHA-256 粘进去，页面会告诉你是否与发布值一致。"
        "校验不一致说明下载不完整或被中间环节改动过，重新下载即可。",
    ),
    (
        "可以用迅雷 / 第三方下载器吗？",
        "可以，但下载完请务必做一次 SHA-256 校验。第三方下载器与 GitHub 直连的完整性偶有差异。",
    ),
    (
        "装完游戏起不来怎么办？",
        "用备份覆盖回去，把 ReShade 和两个插件文件都移除，确认游戏能正常启动后再逐步重装。"
        "游戏更新后 ReShade 版本不匹配也会导致启动失败，需要重装。",
    ),
]


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #

def human_size(num_bytes: int) -> str:
    """把字节数格式化成便于阅读的形式。"""
    mb = num_bytes / 1024 / 1024
    if mb >= 1024:
        return f"{mb / 1024:.2f} GB"
    if mb >= 1:
        return f"{mb:.1f} MB"
    return f"{num_bytes / 1024:.0f} KB"


def sha256_of_file(path: str, chunk: int = 1 << 20) -> str:
    """流式计算文件 SHA-256，避免把大文件整个读进内存。"""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def unpacked_size(pkg: dict) -> int:
    """某包解压后的总体积 = 三个文件之和。"""
    return pkg["dll_size"] + sum(f["size"] for f in SHARED_FILES)


def guess_key_from_gpu(text: str) -> str | None:
    """从显卡型号文本里猜代际，例如 'RTX 4070 Ti' -> '40'。"""
    match = re.search(r"\b([2-5])\d{3}\b", text)
    if not match:
        return None
    return {"2": "20-30", "3": "20-30", "4": "40", "5": "50"}[match.group(1)]


def pkg_by_key(key: str) -> dict:
    return next(p for p in PACKAGES if p["key"] == key)


def chart_frame() -> pd.DataFrame:
    """分组条形图数据：每个包的下载体积与解压后体积两个口径。"""
    rows = []
    for pkg in PACKAGES:
        rows.append({"包": pkg["label"], "口径": "下载体积", "大小": pkg["download_size"]})
        rows.append({"包": pkg["label"], "口径": "解压后体积", "大小": unpacked_size(pkg)})
    df = pd.DataFrame(rows)
    df["MB"] = (df["大小"] / 1024 / 1024).round(1)
    return df


def composition_frame() -> pd.DataFrame:
    """解压后的文件构成，供表格视图使用。"""
    rows = []
    for pkg in PACKAGES:
        for name, size in [
            ("nvngx_dlssnr.dll", pkg["dll_size"]),
            ("renodx-dlss5.addon64", SHARED_FILES[1]["size"]),
            ("ReShade_Setup_6.8.0_Addon.exe", SHARED_FILES[0]["size"]),
        ]:
            rows.append(
                {"包": pkg["label"], "文件": name, "MB": round(size / 1024 / 1024, 1)}
            )
    return pd.DataFrame(rows)


def size_chart() -> alt.LayerChart:
    """各包下载体积 vs 解压后体积的分组条形图。

    用分组而非堆叠：包内两个小文件只有 2~4 MB，堆叠时会被压成几像素的细线，
    读不出信息；而「下载体积」和「解压后体积」这两个口径本身都有量级，
    摆在一起还能顺带看出压缩比。
    """
    df = chart_frame()
    label_order = [p["label"] for p in PACKAGES]
    headroom = float(df["MB"].max()) * 1.14  # 给条尾的直接标注留位置

    # 两个图层共用同一套轴定义，layered chart 会合并成一套轴
    axes = {
        "y": alt.Y(
            "包:N",
            sort=label_order,
            axis=alt.Axis(title=None, labelColor=INK, labelFontSize=12,
                          domainColor=GRID, tickColor=GRID),
        ),
        "yOffset": alt.YOffset("口径:N", sort=MEASURE_ORDER),
        "x": alt.X(
            "MB:Q",
            title="体积 (MB)",
            scale=alt.Scale(domain=[0, headroom]),
            axis=alt.Axis(labelColor=INK_MUTED, titleColor=INK_MUTED,
                          gridColor=GRID, domainColor=GRID, tickColor=GRID),
        ),
    }

    bars = (
        alt.Chart(df)
        .mark_bar(size=18, cornerRadiusTopRight=4, cornerRadiusBottomRight=4,
                  stroke=SURFACE, strokeWidth=1.5)
        .encode(
            **axes,
            color=alt.Color(
                "口径:N",
                scale=alt.Scale(domain=MEASURE_ORDER,
                                range=[SERIES[n] for n in MEASURE_ORDER]),
                legend=alt.Legend(title=None, orient="top", labelColor=INK_MUTED,
                                  symbolType="square", symbolSize=120),
            ),
            tooltip=[
                alt.Tooltip("包:N", title="压缩包"),
                alt.Tooltip("口径:N", title="口径"),
                alt.Tooltip("MB:Q", title="体积 (MB)", format=",.1f"),
            ],
        )
    )

    # 条尾直接标注数值。文字穿文本色，不跟随系列色。
    labels = (
        alt.Chart(df)
        .mark_text(align="left", dx=6, fontSize=11, color=INK)
        .encode(**axes, text=alt.Text("MB:Q", format=",.0f"))
    )

    return (bars + labels).properties(height=240).configure_view(stroke=None)


# --------------------------------------------------------------------------- #
# 页面
# --------------------------------------------------------------------------- #

def page_overview() -> None:
    st.title("鸣潮 DLSS5 插件包")
    st.caption(f"下载与安装助手 · 对应 Release [{TAG}]({RELEASE_URL})")

    st.markdown(
        "本仓库按**显卡代际**把插件打成三个压缩包，你只需要下载与自己显卡匹配的那一个。"
        "每个包里是同一套三个文件，区别只在 `nvngx_dlssnr.dll` 的版本。"
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("压缩包数量", f"{len(PACKAGES)} 个", help="按 RTX 20/30、40、50 系划分")
    col2.metric("单包下载体积", "119 ~ 133 MB", help="取决于显卡代际")
    col3.metric("解压后总体积", "165 ~ 302 MB", help="20-30 系包的 DLL 明显更大")

    st.divider()

    st.subheader("快速开始")
    step1, step2, step3 = st.columns(3)
    with step1:
        st.markdown("**1 · 确认显卡代际**")
        st.caption("Win+R 输入 `dxdiag`，看「显示」页的显卡型号。")
    with step2:
        st.markdown("**2 · 下载对应的包**")
        st.caption("到「选包助手」页点下载按钮，直达对应压缩包。")
    with step3:
        st.markdown("**3 · 校验并解压**")
        st.caption("核对 SHA-256，确认下载完整后再动手安装。")

    st.divider()

    st.subheader("各包体积：下载 vs 解压后")
    st.altair_chart(size_chart(), width="stretch")
    st.caption(
        "三个包的下载体积都在 119~133 MB，彼此差得不多；解压之后差距才拉开——"
        "20-30 系包 301.7 MB，接近另外两包（164.5 MB）的两倍。"
        "差距几乎全部来自包内的 `nvngx_dlssnr.dll`：该包内是 295 MiB，另外两包是 158 MiB。"
    )

    st.divider()
    with st.expander("解压后文件构成（表格视图）", expanded=False):
        composition = composition_frame().pivot(index="包", columns="文件", values="MB")
        st.dataframe(composition.round(1), width="stretch")

    st.info(BACKUP_NOTE, icon="⚠️")


def page_picker() -> None:
    st.title("选包助手")
    st.markdown("选一个方式告诉页面你的显卡，它会给出该下载哪个包。")

    tab_pick, tab_type = st.tabs(["按代际选择", "输入显卡型号"])

    selected_key: str | None = None

    with tab_pick:
        choice = st.radio(
            "你的显卡属于哪一代？",
            options=[p["label"] for p in PACKAGES],
            horizontal=True,
            label_visibility="collapsed",
        )
        selected_key = next(p["key"] for p in PACKAGES if p["label"] == choice)

    with tab_type:
        typed = st.text_input(
            "输入显卡型号",
            placeholder="例如：RTX 3060 / RTX 4070 Ti / RTX 5080",
        )
        if typed:
            guessed = guess_key_from_gpu(typed)
            if guessed:
                selected_key = guessed
                st.success(f"识别为 **{pkg_by_key(guessed)['label']}**", icon="✅")
            else:
                st.warning("没识别出代际，请用左边的「按代际选择」，或确认型号写法。", icon="⚠️")
        else:
            selected_key = None

    if selected_key is None:
        st.info("请先选择或输入你的显卡型号。", icon="👈")
        return

    pkg = pkg_by_key(selected_key)
    download_url = f"{RELEASE_ASSET_BASE}/{pkg['file']}"

    st.divider()
    st.subheader(f"推荐下载：{pkg['label']}")

    left, right = st.columns([3, 2])
    with left:
        st.markdown(f"**适用显卡**：{pkg['gpus']}")
        st.markdown(f"**下载体积**：{human_size(pkg['download_size'])}")
        st.markdown(f"**解压后体积**：{human_size(unpacked_size(pkg))}")
        st.markdown(f"**压缩包文件名**：`{pkg['file']}`")
        st.link_button(f"⬇ 下载 {pkg['file']}", download_url, width="stretch")
    with right:
        st.markdown("**包内 `nvngx_dlssnr.dll`**")
        st.markdown(f"- 体积：{human_size(pkg['dll_size'])}")
        st.caption(pkg["dll_note"])

    with st.expander("下载后核对 SHA-256"):
        st.code(pkg["sha256"], language=None)
        st.caption("完整校验工具在「文件与校验」页。")

    st.divider()
    st.subheader("三个包的对比")

    compare = pd.DataFrame(
        [
            {
                "压缩包": p["file"],
                "适用显卡": p["gpus"],
                "下载体积": human_size(p["download_size"]),
                "解压后": human_size(unpacked_size(p)),
                "包内 DLL": human_size(p["dll_size"]),
            }
            for p in PACKAGES
        ]
    )
    st.dataframe(compare, width="stretch", hide_index=True)


def page_files() -> None:
    st.title("文件与校验")

    st.subheader("下载压缩包")
    links = pd.DataFrame(
        [
            {
                "文件名": p["file"],
                "适用显卡": p["label"],
                "体积": human_size(p["download_size"]),
                "下载": f"{RELEASE_ASSET_BASE}/{p['file']}",
            }
            for p in PACKAGES
        ]
    )
    st.dataframe(
        links,
        width="stretch",
        hide_index=True,
        column_config={
            "下载": st.column_config.LinkColumn("下载", display_text="点击下载"),
        },
    )

    st.subheader("压缩包 SHA-256")
    for pkg in PACKAGES:
        with st.expander(f"{pkg['file']}　·　{human_size(pkg['download_size'])}"):
            st.code(pkg["sha256"], language=None)

    st.divider()

    st.subheader("校验下载结果")
    st.markdown("把下载到的压缩包 SHA-256 粘进下面的框，页面会告诉你是否与发布值一致。")

    pasted = st.text_input(
        "SHA-256",
        placeholder="粘贴 64 位十六进制字符串",
        label_visibility="collapsed",
    ).strip().lower().replace(" ", "")

    if pasted:
        if not re.fullmatch(r"[0-9a-f]{64}", pasted):
            st.warning("这不像一个 SHA-256（应为 64 位十六进制字符），请检查是否复制完整。", icon="⚠️")
        else:
            hit = next((p for p in PACKAGES if p["sha256"] == pasted), None)
            if hit:
                st.success(f"校验通过 —— 这就是 **{hit['label']}** 的压缩包（`{hit['file']}`）。", icon="✅")
                st.info("可以解压安装了，安装步骤见「安装步骤」页。", icon="👉")
            else:
                st.error("与三个发布版本都不匹配。下载可能不完整或被改动过，建议重新下载。", icon="❌")
                st.caption("若确认是从本仓库 Release 页下载的，请检查是否下到了其他版本或其他仓库的文件。")

    st.divider()

    st.subheader("解压后各文件的 SHA-256")
    st.caption("解压完成后可以逐个核对。三包共用的两个文件，40 系与 50 系包内完全相同。")

    for pkg in PACKAGES:
        with st.expander(f"{pkg['label']} 包内文件"):
            rows = [
                {
                    "文件": "nvngx_dlssnr.dll",
                    "体积": human_size(pkg["dll_size"]),
                    "SHA-256": pkg["dll_sha256"],
                }
            ]
            rows += [
                {"文件": f["name"], "体积": human_size(f["size"]), "SHA-256": f["sha256"]}
                for f in SHARED_FILES
            ]
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    with st.expander("本地文件校验（可选，需要在本机运行）"):
        st.markdown("如果你把本应用跑在本地，可以直接选文件算哈希：")
        st.code(
            "import hashlib, pathlib\n"
            "\n"
            "path = pathlib.Path(r'D:\\下载\\40-series.rar')\n"
            "h = hashlib.sha256()\n"
            "with path.open('rb') as fh:\n"
            "    while block := fh.read(1 << 20):\n"
            "        h.update(block)\n"
            "print(h.hexdigest())",
            language="python",
        )


def page_install() -> None:
    st.title("安装步骤")
    st.warning(BACKUP_NOTE, icon="⚠️")

    for idx, (title, body) in enumerate(INSTALL_STEPS, start=1):
        st.markdown(f"#### {idx}. {title}")
        st.markdown(body)

    st.divider()
    st.info(
        "上面的流程是通用参考。不同游戏版本、不同 ReShade 版本的目录结构与操作细节会有差异，"
        "请以你实际参考的教程为准。",
        icon="ℹ️",
    )

    st.subheader("装完没效果？按顺序排查")
    st.markdown(
        "1. **确认包选对了** —— 装错代际是最常见的原因，回「选包助手」核对一次。\n"
        "2. **确认文件放置位置正确** —— 尤其 `nvngx_dlssnr.dll`，放错目录等于没装。\n"
        "3. **确认 ReShade 起来了** —— 游戏内按 Home 能呼出界面，说明注入成功。\n"
        "4. **确认游戏设置里开了 DLSS** —— 插件装好了但游戏里没开，同样看不到效果。\n"
        "5. **确认游戏版本兼容** —— 游戏更新后 ReShade 可能失效，需要重装。"
    )


def page_faq() -> None:
    st.title("常见问题")
    for question, answer in FAQ:
        with st.expander(question):
            st.markdown(answer)

    st.divider()
    st.markdown(f"还有别的问题？到 [Issues](https://github.com/{REPO}/issues) 提。")


def page_about() -> None:
    st.title("关于")

    st.subheader("这个仓库是什么")
    st.markdown(
        f"一个 mod 资源分发仓库，把鸣潮可用的 DLSS5 插件按显卡代际打包成三个压缩包，"
        f"通过 [GitHub Release]({RELEASE_URL}) 发布。仓库本身只包含本页面与说明文档，不含游戏或源码。"
    )

    st.subheader("页面怎么跑起来")
    st.markdown("本页是纯 Python 的 Streamlit 应用，本地运行：")
    st.code(
        "pip install -r requirements.txt\n"
        "streamlit run app.py",
        language="bash",
    )
    st.caption("装好后浏览器会自动打开 http://localhost:8501。")

    st.subheader("版权与免责")
    st.markdown(
        "- `nvngx_dlssnr.dll` 为 NVIDIA 专有二进制文件，版权归 NVIDIA 所有，此处仅作个人使用分发。\n"
        "- ReShade 版权归 Crosire 及 ReShade 贡献者所有。\n"
        "- RenoDX 版权归其原作者所有。\n"
        "- 本仓库与上述任一项目的官方无隶属关系，也不对使用后果作任何担保。"
    )

    st.divider()
    st.markdown(
        f"[Release {TAG}]({RELEASE_URL})　·　"
        f"[仓库首页](https://github.com/{REPO})　·　"
        f"[问题反馈](https://github.com/{REPO}/issues)"
    )


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #

PAGES = {
    "概览": page_overview,
    "选包助手": page_picker,
    "文件与校验": page_files,
    "安装步骤": page_install,
    "常见问题": page_faq,
    "关于": page_about,
}


def main() -> None:
    st.set_page_config(
        page_title="鸣潮 DLSS5 插件包",
        page_icon="🎮",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.sidebar.title("鸣潮 DLSS5")
    st.sidebar.caption("下载与安装助手")
    choice = st.sidebar.radio("导航", list(PAGES), label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.markdown(f"[Release {TAG}]({RELEASE_URL})")
    st.sidebar.caption("本页面不隶属于游戏或以上任一项目的官方。")

    PAGES[choice]()


if __name__ == "__main__":
    main()
