from __future__ import annotations

from pandoc_gui.models import OptionKind, OptionSpec


CORE_OPTION_NAMES = {
    "from",
    "read",
    "to",
    "write",
    "output",
}

TOOL_OPTION_NAMES = {
    "bash-completion",
    "list-input-formats",
    "list-output-formats",
    "list-extensions",
    "list-highlight-languages",
    "list-highlight-styles",
    "print-default-template",
    "print-default-data-file",
    "print-highlight-style",
    "version",
    "help",
}


def _spec(
    key: str,
    label: str,
    category: str,
    kind: OptionKind = OptionKind.TEXT,
    *,
    choices: tuple[str, ...] = (),
    repeatable: bool = False,
    aliases: tuple[str, ...] = (),
    description: str = "",
) -> OptionSpec:
    return OptionSpec(
        key=key.replace("-", "_"),
        flag=f"--{key}",
        label=label,
        category=category,
        kind=kind,
        choices=choices,
        repeatable=repeatable,
        aliases=aliases,
        description=description,
    )


OPTION_SPECS: tuple[OptionSpec, ...] = (
    _spec("data-dir", "Pandoc 数据目录", "模板与元数据", OptionKind.PATH),
    _spec("metadata", "元数据 KEY[=VALUE]", "模板与元数据", repeatable=True),
    _spec("metadata-file", "元数据文件", "模板与元数据", OptionKind.PATH, repeatable=True),
    _spec("defaults", "Defaults 文件", "模板与元数据", OptionKind.PATH, repeatable=True),
    _spec("file-scope", "文件独立作用域", "模板与元数据", OptionKind.BOOL),
    _spec("sandbox", "沙盒模式", "模板与元数据", OptionKind.BOOL),
    _spec("standalone", "独立文档", "模板与元数据", OptionKind.BOOL),
    _spec("template", "模板文件", "模板与元数据", OptionKind.PATH),
    _spec("variable", "模板变量 KEY[=VALUE]", "模板与元数据", repeatable=True),
    _spec("variable-json", "JSON 模板变量 KEY:JSON", "模板与元数据", repeatable=True),
    _spec("wrap", "换行模式", "布局与文本", OptionKind.CHOICE, choices=("auto", "none", "preserve")),
    _spec("ascii", "仅 ASCII 输出", "布局与文本", OptionKind.BOOL),
    _spec("toc", "生成目录", "目录与章节", OptionKind.BOOL, aliases=("table-of-contents",)),
    _spec("toc-depth", "目录深度", "目录与章节", OptionKind.INTEGER),
    _spec("lof", "插图目录", "目录与章节", OptionKind.BOOL, aliases=("list-of-figures",)),
    _spec("lot", "表格目录", "目录与章节", OptionKind.BOOL, aliases=("list-of-tables",)),
    _spec("number-sections", "章节编号", "目录与章节", OptionKind.BOOL),
    _spec("number-offset", "章节编号偏移", "目录与章节"),
    _spec("top-level-division", "顶级章节类型", "目录与章节", OptionKind.CHOICE, choices=("section", "chapter", "part")),
    _spec("extract-media", "提取媒体目录", "资源与媒体", OptionKind.PATH),
    _spec("resource-path", "资源搜索路径", "资源与媒体"),
    _spec("include-in-header", "页头包含文件", "资源与媒体", OptionKind.PATH, repeatable=True),
    _spec("include-before-body", "正文前包含文件", "资源与媒体", OptionKind.PATH, repeatable=True),
    _spec("include-after-body", "正文后包含文件", "资源与媒体", OptionKind.PATH, repeatable=True),
    _spec("no-highlight", "禁用代码高亮", "代码高亮", OptionKind.SWITCH),
    _spec("highlight-style", "高亮样式或文件", "代码高亮"),
    _spec("syntax-definition", "语法定义文件", "代码高亮", OptionKind.PATH, repeatable=True),
    _spec("syntax-highlighting", "语法高亮主题", "代码高亮"),
    _spec("dpi", "图片 DPI", "资源与媒体", OptionKind.INTEGER),
    _spec("eol", "换行符", "布局与文本", OptionKind.CHOICE, choices=("crlf", "lf", "native")),
    _spec("columns", "字符列宽", "布局与文本", OptionKind.INTEGER),
    _spec("preserve-tabs", "保留制表符", "布局与文本", OptionKind.BOOL),
    _spec("tab-stop", "制表符宽度", "布局与文本", OptionKind.INTEGER),
    _spec("pdf-engine", "PDF 引擎", "PDF 与 Office"),
    _spec("pdf-engine-opt", "PDF 引擎参数", "PDF 与 Office", repeatable=True),
    _spec("reference-doc", "参考文档", "PDF 与 Office", OptionKind.PATH),
    _spec("self-contained", "自包含文档", "资源与媒体", OptionKind.BOOL),
    _spec("embed-resources", "嵌入资源", "资源与媒体", OptionKind.BOOL),
    _spec("link-images", "链接图片", "资源与媒体", OptionKind.BOOL),
    _spec("request-header", "请求头 NAME=VALUE", "资源与媒体", repeatable=True),
    _spec("no-check-certificate", "忽略 TLS 证书检查", "资源与媒体", OptionKind.BOOL),
    _spec("abbreviations", "缩写文件", "资源与媒体", OptionKind.PATH),
    _spec("typst-input", "Typst 输入 KEY=VALUE", "PDF 与 Office", repeatable=True),
    _spec("indented-code-classes", "缩进代码类", "代码高亮"),
    _spec("default-image-extension", "默认图片扩展名", "资源与媒体"),
    _spec("filter", "可执行过滤器", "过滤器", repeatable=True),
    _spec("lua-filter", "Lua 过滤器", "过滤器", OptionKind.PATH, repeatable=True),
    _spec("shift-heading-level-by", "标题级别偏移", "目录与章节", OptionKind.INTEGER),
    _spec("base-header-level", "基础标题级别", "目录与章节", OptionKind.INTEGER),
    _spec("track-changes", "修订处理", "PDF 与 Office", OptionKind.CHOICE, choices=("accept", "reject", "all")),
    _spec("strip-comments", "移除注释", "布局与文本", OptionKind.BOOL),
    _spec("reference-links", "使用引用链接", "布局与文本", OptionKind.BOOL),
    _spec("reference-location", "引用链接位置", "布局与文本", OptionKind.CHOICE, choices=("block", "section", "document")),
    _spec("figure-caption-position", "图片标题位置", "布局与文本", OptionKind.CHOICE, choices=("above", "below")),
    _spec("table-caption-position", "表格标题位置", "布局与文本", OptionKind.CHOICE, choices=("above", "below")),
    _spec("markdown-headings", "Markdown 标题样式", "布局与文本", OptionKind.CHOICE, choices=("setext", "atx")),
    _spec("list-tables", "使用列表表格", "布局与文本", OptionKind.BOOL),
    _spec("listings", "使用 LaTeX listings", "代码高亮", OptionKind.BOOL),
    _spec("incremental", "增量显示列表", "HTML 与幻灯片", OptionKind.BOOL),
    _spec("slide-level", "幻灯片级别", "HTML 与幻灯片", OptionKind.INTEGER),
    _spec("section-divs", "章节使用 div", "HTML 与幻灯片", OptionKind.BOOL),
    _spec("html-q-tags", "使用 HTML q 标签", "HTML 与幻灯片", OptionKind.BOOL),
    _spec("email-obfuscation", "邮箱混淆", "HTML 与幻灯片", OptionKind.CHOICE, choices=("none", "javascript", "references")),
    _spec("id-prefix", "元素 ID 前缀", "HTML 与幻灯片"),
    _spec("title-prefix", "页面标题前缀", "HTML 与幻灯片"),
    _spec("css", "CSS 文件或 URL", "HTML 与幻灯片", repeatable=True),
    _spec("epub-subdirectory", "EPUB 子目录", "EPUB"),
    _spec("epub-cover-image", "EPUB 封面", "EPUB", OptionKind.PATH),
    _spec("epub-title-page", "EPUB 标题页", "EPUB", OptionKind.BOOL),
    _spec("epub-metadata", "EPUB 元数据", "EPUB", OptionKind.PATH),
    _spec("epub-embed-font", "EPUB 嵌入字体", "EPUB", OptionKind.PATH, repeatable=True),
    _spec("split-level", "分割级别", "EPUB", OptionKind.INTEGER),
    _spec("chunk-template", "分块文件名模板", "EPUB"),
    _spec("epub-chapter-level", "EPUB 章节级别", "EPUB", OptionKind.INTEGER),
    _spec("ipynb-output", "Notebook 输出", "PDF 与 Office", OptionKind.CHOICE, choices=("all", "none", "best")),
    _spec("citeproc", "处理引用", "引用", OptionKind.SWITCH),
    _spec("bibliography", "参考文献文件", "引用", OptionKind.PATH, repeatable=True),
    _spec("csl", "CSL 样式文件", "引用", OptionKind.PATH),
    _spec("citation-abbreviations", "引用缩写文件", "引用", OptionKind.PATH),
    _spec("natbib", "使用 natbib", "引用", OptionKind.SWITCH),
    _spec("biblatex", "使用 biblatex", "引用", OptionKind.SWITCH),
    _spec("mathml", "使用 MathML", "数学公式", OptionKind.SWITCH),
    _spec("webtex", "使用 WebTeX", "数学公式"),
    _spec("mathjax", "使用 MathJax", "数学公式"),
    _spec("katex", "使用 KaTeX", "数学公式"),
    _spec("gladtex", "使用 gladTeX", "数学公式", OptionKind.SWITCH),
    _spec("trace", "跟踪模式", "诊断", OptionKind.BOOL),
    _spec("dump-args", "输出参数", "诊断", OptionKind.BOOL),
    _spec("ignore-args", "忽略参数", "诊断", OptionKind.BOOL),
    _spec("verbose", "详细日志", "诊断", OptionKind.SWITCH),
    _spec("quiet", "安静模式", "诊断", OptionKind.SWITCH),
    _spec("fail-if-warnings", "警告视为失败", "诊断", OptionKind.BOOL),
    _spec("log", "JSON 日志文件", "诊断", OptionKind.PATH),
)

OPTION_BY_KEY = {spec.key: spec for spec in OPTION_SPECS}
CATEGORIES = tuple(dict.fromkeys(spec.category for spec in OPTION_SPECS))


def mapped_option_names() -> set[str]:
    names = set(CORE_OPTION_NAMES) | set(TOOL_OPTION_NAMES)
    for spec in OPTION_SPECS:
        names.update(spec.long_names)
    return names

