# 原文来源与缓存格式

本机初始正文库的获取配置记录来源为 `secemp9/arxiv-complete`，固定快照 `cee894837962fede5612cccf2a4c7cacf49b4c3a`，配置 `paper_text`。

- [上游数据集](https://huggingface.co/datasets/secemp9/arxiv-complete)
- [上述固定快照](https://huggingface.co/datasets/secemp9/arxiv-complete/tree/cee894837962fede5612cccf2a4c7cacf49b4c3a)

该定位来自初始库的本地获取配置，不能替代本线540条逐篇哈希核验。本线清单本身记录每条 `source_shard`、`source_row`（原数据行号）、`source_sha256`。上游缓存正文是合并LaTeX，原始arXiv版本身份仍未确认，因此它不构成固定新旧版本对照。

接手机器可在合法访问与原许可允许的范围内，从已有同源缓存提取被领取的30条，或从上述上游的对应分片/行号有界取得所需记录。无需重建全库或重复本机已完成的归档；仍遵守130GB软停、150GB上限、至少20GB磁盘空闲和内存保护。先确认上游字段与行号对应，最终以 `SHA256(text.encode('utf-8'))` 匹配清单为准；不能以匹配arXiv ID替代匹配正文。

`prepare_inputs.py` 接受本地逐行JSON缓存：原分片 `paper_text/train-00023-of-00050.parquet` 对应 `--body-root` 下的 `train-00023-of-00050.body.jsonl.gz`。每行至少包含：

```json
{"paper_id":"原arXiv ID","text":"未经换行改写的原合并TeX文本","text_sha256":"原文本SHA-256"}
```

可同时保留categories、主文件、文件合并情况等原来源字段。转换时UTF-8读写，JSON内文本保持原字符与换行；不要运行TeX、宏或论文指令。工具生成的dossier只是首160行和命中附近上下文，不能代替必要的原文阅读。

本公开包没有全文缓存、密钥或私有下载地址。无法取得匹配正文时登记INPUT_VERSION_MISMATCH/SOURCE_CACHE_MISSING及欠账。可另行阅读明确版本的官方原文，但必须记录新来源、哈希与版本，重新定位命中，并把它与旧缓存的结果区分；不能静默改清单后宣称通过原输入核验。
