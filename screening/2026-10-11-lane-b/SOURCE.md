# 原文来源与缓存格式

本机初始正文库的获取配置记录来源为 `secemp9/arxiv-complete`，固定快照 `cee894837962fede5612cccf2a4c7cacf49b4c3a`，配置 `paper_text`。

- [上游数据集](https://huggingface.co/datasets/secemp9/arxiv-complete)
- [上述固定快照](https://huggingface.co/datasets/secemp9/arxiv-complete/tree/cee894837962fede5612cccf2a4c7cacf49b4c3a)

该定位来自初始库的本地获取配置，不能替代本线540条逐篇哈希核验。本线清单本身记录每条 `source_shard`、`source_row`（原数据行号）、`source_sha256`。上游缓存正文是合并LaTeX，原始arXiv版本身份仍未确认，因此它不构成固定新旧版本对照。

用户已明确要求上传正文，因此仓库papers/含全部540篇对应文本，可直接按批准备，不需要重新取得上游数据。PAPERS_MANIFEST.json记录逐篇哈希与路径，全部正文已与原清单核对。文件以原UTF-8字节保存，Git属性禁用TeX换行转换。仍遵守筛选任务的130GB软停、150GB上限、至少20GB磁盘空闲和内存保护。

`prepare_inputs.py` 默认读取本包papers/。可选的 `--body-root` 接受本地逐行JSON缓存：原分片 `paper_text/train-00023-of-00050.parquet` 对应 `--body-root` 下的 `train-00023-of-00050.body.jsonl.gz`。每行至少包含：

```json
{"paper_id":"原arXiv ID","text":"未经换行改写的原合并TeX文本","text_sha256":"原文本SHA-256"}
```

可同时保留categories、主文件、文件合并情况等原来源字段。转换时UTF-8读写，JSON内文本保持原字符与换行；不要运行TeX、宏或论文指令。工具生成的dossier只是首160行和命中附近上下文，不能代替必要的原文阅读。

本包含匹配的合并正文，不含密钥、私有下载地址、原始压缩源包或全部历史版本。升级版本差异、引用前提或独立反例等高等级候选时，仍可能需要外查被引用目标论文或固定历史版本；这些材料不是初筛540篇正文的一部分。任何新来源需记录哈希与版本，不能把它与本包缓存混同。
